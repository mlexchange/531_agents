"""
Scan Plan Capability for BL531 Beamline.

Executes a scan plan, retrieves the data, and returns it formatted.
This is a complete workflow: scan → retrieve → format.
"""

import re
import textwrap
from typing import Any, Dict, Optional

from langgraph.types import interrupt

# isort: off
from osprey.approval import (
    clear_approval_state,
    create_approval_type,
    get_approval_resume_data,
)
from osprey.base.capability import BaseCapability
from osprey.base.decorators import capability_node
from osprey.base.errors import ErrorClassification, ErrorSeverity
from osprey.base.examples import (
    ClassifierActions,
    ClassifierExample,
    OrchestratorExample,
    OrchestratorGuide,
    PlannedStep,
    TaskClassifierGuide,
)
from osprey.registry import get_registry
from osprey.state import AgentState, StateManager
from osprey.utils.logger import get_logger
from osprey.utils.streaming import get_streamer

# isort: on
from bl531.bl531_api import bl531  # noqa: I100 bug in linter
from bl531.bl531_data_api import bl531_data
from bl531.context_classes import RunDataContext

REF_RE = re.compile(
    r"^ref:(?P<context_key>[^.]+)\.(?P<field>[A-Za-z_]\w*)(?P<offset>[+-]\d+(?:\.\d+)?)?$"
)


def _get_context_from_state(state, context_type: str, context_key: str):
    """
    Best-effort fetch of a stored capability context object directly from `state`.

    Tries common storage layouts, including Osprey-style `capability_context_data`.

    Args:
        state: AgentState (often dict-like)
        context_type: e.g. registry.context_types.XRAY_EDGE_CONTEXT (typically "XRAY_EDGE_CONTEXT")
        context_key: the PlannedStep.context_key used when storing the context

    Returns:
        The stored context object, or None if not found.
    """
    # ----------------------------
    # dict-like state (most common)
    # ----------------------------
    if isinstance(state, dict):
        # ✅ Osprey common location: state["capability_context_data"]
        ccd = state.get("capability_context_data")
        if isinstance(ccd, dict):
            # Shape A: ccd[context_type][context_key] = obj
            typed = ccd.get(context_type)
            if isinstance(typed, dict) and context_key in typed:
                return typed[context_key]

            # Shape B: ccd[context_key] = obj (untyped)
            if context_key in ccd:
                return ccd[context_key]

        # Other common patterns (typed)
        for path in (
            ("contexts", context_type, context_key),
            ("context", context_type, context_key),
            ("context_store", context_type, context_key),
            ("memory", "contexts", context_type, context_key),
            ("data", "contexts", context_type, context_key),
            ("session_state", "contexts", context_type, context_key),
            ("execution_step_results", context_type, context_key),
        ):
            cur = state
            ok = True
            for p in path:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    ok = False
                    break
            if ok:
                return cur

        # Other common patterns (untyped)
        for path in (
            ("contexts", context_key),
            ("context", context_key),
            ("context_store", context_key),
            ("memory", "contexts", context_key),
            ("data", "contexts", context_key),
            ("session_state", "contexts", context_key),
        ):
            cur = state
            ok = True
            for p in path:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    ok = False
                    break
            if ok:
                return cur

        return None

    # ----------------------------
    # object-like state (fallback)
    # ----------------------------
    for attr in (
        "capability_context_data",
        "contexts",
        "context",
        "context_store",
        "memory",
        "data",
        "session_state",
    ):
        if hasattr(state, attr):
            root = getattr(state, attr)
            if isinstance(root, dict):
                # typed
                typed = root.get(context_type)
                if isinstance(typed, dict) and context_key in typed:
                    return typed[context_key]
                # untyped
                if context_key in root:
                    return root[context_key]

    return None


def _resolve_numeric(value, state, registry, StateManager=None):
    """
    Resolve:
      - numeric (int/float) -> float
      - numeric string -> float
      - ref:<context_key>.<field>(+/-offset) -> resolved float
    """
    # Already numeric
    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        raise ValueError(f"Expected numeric string or ref: got {type(value)}")

    v = value.strip()

    # Block placeholders hard (common LLM mistakes)
    lower = v.lower()
    if (
        ("{{" in v)
        or ("}}" in v)
        or ("<" in v)
        or (">" in v)
        or ("placeholder" in lower)
        or ("tbd" in lower)
    ):
        raise ValueError(f"Unresolved placeholder detected: {value}")

    # Try literal float first
    try:
        return float(v)
    except ValueError:
        pass

    # Try reference pattern
    m = REF_RE.match(v)
    if not m:
        raise ValueError(
            f"Value must be a number or ref: <context_key>.<field>(+/-offset). Got: {value}"
        )

    context_key = m.group("context_key")
    field = m.group("field")
    offset = float(m.group("offset") or 0.0)

    ctx_type = registry.context_types.XRAY_EDGE_CONTEXT

    # Prefer an official accessor if your framework provides one (optional)
    ctx_obj = None
    if StateManager is not None and hasattr(StateManager, "load_context"):
        ctx_obj = StateManager.load_context(state, ctx_type, context_key)  # if it exists
    if ctx_obj is None:
        ctx_obj = _get_context_from_state(state, ctx_type, context_key)

    if ctx_obj is None:
        # safe debug info (won’t reference undefined vars)
        if isinstance(state, dict):
            top = list(state.keys())
        else:
            top = [a for a in dir(state) if not a.startswith("_")]
        raise ValueError(
            f"Missing XRAY_EDGE_CONTEXT '{context_key}' (type={ctx_type}). "
            f"Top-level state keys/attrs: {top[:30]}"
        )

    base_value = _get_field(ctx_obj, field)
    if base_value is None:
        if isinstance(ctx_obj, dict):
            avail = list(ctx_obj.keys())
        else:
            avail = [a for a in dir(ctx_obj) if not a.startswith("_")]
        raise ValueError(
            f"Field '{field}' not found on XRAY_EDGE_CONTEXT '{context_key}'. "
            f"Available keys/attrs: {avail[:50]}"
        )

    return float(base_value) + offset


def _get_field(ctx_obj, field: str):
    # 1) attribute-style
    if not isinstance(ctx_obj, dict):
        if hasattr(ctx_obj, field):
            return getattr(ctx_obj, field)

    # 2) dict-style exact key
    if isinstance(ctx_obj, dict) and field in ctx_obj:
        return ctx_obj[field]

    # 3) aliases for common energy field names
    # If the user asked for edge_energy_eV, try other likely keys.
    aliases = {
        "edge_energy_eV": [
            "edge_energy_eV",
            "edge_energy_ev",
            "edge_energy",
            "edge_energy_eV".lower(),
            "energy_eV",
            "energy_ev",
            "energy",
            "edgeEnergy_eV",
            "edgeEnergyEv",
        ],
        "edge_energy_keV": [
            "edge_energy_keV",
            "edge_energy_kev",
            "edge_energy_keV".lower(),
            "energy_keV",
            "energy_kev",
        ],
    }

    # Also allow requesting "edge_energy_eV" but stored as different case
    candidates = aliases.get(field, [field, field.lower(), field.upper()])

    if isinstance(ctx_obj, dict):
        for k in candidates:
            if k in ctx_obj:
                return ctx_obj[k]

        # last resort: fuzzy match ignoring underscores/case
        def norm(s):
            return "".join(c for c in s.lower() if c.isalnum())

        target = norm(field)
        for k in ctx_obj.keys():
            if norm(k) == target:
                return ctx_obj[k]

    return None


logger = get_logger("scan_capability")
registry = get_registry()


class ScanCapabilityError(Exception):
    """Base exception for scan capability."""


# Motor definitions for BL531 beamline
AVAILABLE_MOTORS = {
    "gi_angle": "Grazing incidence angle",
    "hexapod_motor_Ty": "Hexapod Y-axis translation (horizontal/lateral)",
    "hexapod_motor_Tz": "Hexapod Z-axis translation (vertical/height)",
    "hexapod_motor_Ry": "Hexapod rotation around Y-axis",
    "hexapod_motor_Rz": "Hexapod rotation around Z-axis",
    "mono_energy": "Energy of the beam unit in eV",
}


@capability_node
class ScanCapability(BaseCapability):
    """Execute scan plan, retrieve data, and return formatted results.

    This capability does the complete workflow:
    1. Execute scan plan (motor + detectors)
    2. Retrieve the data using run_uid
    3. Return formatted data ready for user

    Available motors:
    - gi_angle: Grazing incidence angle
    - hexapod_motor_Ty: Lateral position (Y translation)
    - hexapod_motor_Tz: Vertical position (Z translation)
    - hexapod_motor_Ry: Rotation around Y axis
    - hexapod_motor_Rz: Rotation around Z axis
    - mono_energy: Energy of the beam unit in eV
    """

    name = "bl531_scan"
    description = "Execute scan plan and return formatted scan data"
    provides = ["RUN_DATA_CONTEXT"]
    requires = ["MOTOR_NAME", "START_POSITION", "STOP_POSITION", "NUM_POINTS", "DETECTORS"]

    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute scan plan and retrieve data."""

        step = StateManager.get_current_step(state)
        streamer = get_streamer("scan_capability", state)
        logger = get_logger("scan_capability")

        # Extract inputs from orchestrator
        inputs_list = step.get("inputs", [])
        combined_inputs = {}
        if isinstance(inputs_list, list):
            for item in inputs_list:
                if isinstance(item, dict):
                    combined_inputs.update(item)
        else:
            combined_inputs = inputs_list if isinstance(inputs_list, dict) else {}

        # Extract required parameters
        motor = combined_inputs.get("MOTOR_NAME")
        start_raw = combined_inputs.get("START_POSITION")
        stop_raw = combined_inputs.get("STOP_POSITION")
        num = combined_inputs.get("NUM_POINTS")
        detectors = combined_inputs.get("DETECTORS", '["det"]')

        # Validate presence BEFORE resolving
        missing = []
        if motor is None:
            missing.append("MOTOR_NAME")
        if start_raw is None:
            missing.append("START_POSITION")
        if stop_raw is None:
            missing.append("STOP_POSITION")
        if num is None:
            missing.append("NUM_POINTS")
        if missing:
            raise ValueError(
                f"Missing required scan inputs: {missing}. Got keys={list(combined_inputs.keys())}"
            )

        # Now resolve
        start = _resolve_numeric(start_raw, state, registry)
        stop = _resolve_numeric(stop_raw, state, registry)
        num = int(num or 1)  # default to 1 point if not provided

        # Validate inputs
        if not motor or start is None or stop is None or num is None:
            raise ValueError(
                f"Missing required scan inputs. Got: motor={motor}, start={start}, "
                f"stop={stop}, num={num}"
            )

        # Validate motor is available
        if motor not in AVAILABLE_MOTORS:
            available_list = ", ".join(AVAILABLE_MOTORS.keys())
            raise ValueError(f"Invalid motor: {motor}. Available motors: {available_list}")

        # Convert to proper types
        start = float(start)
        stop = float(stop)
        num = int(num)

        # Parse detectors - handle string representation of list
        if isinstance(detectors, str):
            import ast

            try:
                detectors = ast.literal_eval(detectors)
            except (ValueError, SyntaxError):
                detectors = [detectors]

        if not isinstance(detectors, list):
            detectors = [detectors]

        context_key = step.get("context_key", "scan_result")

        # =======================================================
        # HUMAN APPROVAL WORKFLOW - Framework Pattern
        # =======================================================

        # Check if resuming from approval
        has_approval_resume, approved_payload = get_approval_resume_data(
            state, create_approval_type("bl531_scan")
        )

        logger.info(f"Approval resume check: {has_approval_resume}, payload: {approved_payload}")

        if has_approval_resume:
            if not approved_payload:
                # User denied
                raise ScanCapabilityError("Scan operation was cancelled by the user.")

            # User approved - extract approved parameters
            logger.info("Resuming approved scan operation.")
            execution_plan = approved_payload.get("execution_plan", {})
            approved_inputs = execution_plan.get("inputs", inputs_list)

            # Re-extract from approved plan
            combined_inputs = {}
            if isinstance(approved_inputs, list):
                for item in approved_inputs:
                    if isinstance(item, dict):
                        combined_inputs.update(item)

            motor = combined_inputs.get("MOTOR_NAME", motor)
            start = _resolve_numeric(
                combined_inputs.get("START_POSITION", start),
                state,
                registry,
                StateManager=StateManager,
            )
            stop = _resolve_numeric(
                combined_inputs.get("STOP_POSITION", stop),
                state,
                registry,
                StateManager=StateManager,
            )
            num = int(combined_inputs.get("NUM_POINTS", num))
            detectors_approved = combined_inputs.get("DETECTORS")
            if detectors_approved:
                if isinstance(detectors_approved, str):
                    import ast

                    detectors = ast.literal_eval(detectors_approved)
                else:
                    detectors = detectors_approved

            # Clear approval state to prevent pollution
            approval_cleanup = clear_approval_state()

        else:
            # Request approval - THIS IS WHERE THE CHANGE IS
            logger.info("Scan requires human approval before execution.")
            streamer.status("⏸️ Waiting for operator approval...")

            # Create scan summary
            motor_desc = AVAILABLE_MOTORS.get(motor, motor)
            scan_plan_summary = (
                f"**Scan Plan: **\n"
                f"- **Motor: ** {motor_desc}\n"
                f"- **Range: ** {start} → {stop}\n"
                f"- **Points: ** {num}\n"
                f"- **Detectors: ** {detectors}\n"
            )

            # Create execution plan for resume
            execution_plan = {
                "context_key": context_key,
                "capability": ScanCapability.name,
                "task_objective": step.get(
                    "task_objective", f"Scan {motor_desc} from {start} to {stop} with {num} points"
                ),
                "success_criteria": step.get(
                    "success_criteria", f"Scan completed successfully with {num} data points"
                ),
                "expected_output": "RUN_DATA_CONTEXT",
                "parameters": {
                    "motor": motor,
                    "motor_description": motor_desc,
                    "start": str(start),
                    "stop": str(stop),
                    "num_points": str(num),
                    "detectors": detectors,
                },
                "inputs": inputs_list,
            }
            logger.info(f"Created execution plan for approval resume: {execution_plan}")

            # Create interrupt data
            interrupt_data = {
                "user_message": (
                    f"⚠️ **SCAN APPROVAL REQUIRED** ⚠️\n\n"
                    f"{scan_plan_summary}\n"
                    f"**To proceed: **\n"
                    f"- Type **`yes`** to approve and execute\n"
                    f"- Type **`no`** to cancel"
                ),
                "resume_payload": {
                    "approval_type": create_approval_type("bl531_scan"),
                    "execution_plan": execution_plan,
                },
            }

            # Call interrupt()
            # LangGraph will handle the pause/resume automatically
            interrupt(interrupt_data)

            # Execution will STOP here and resume after approval
            # The code below only runs after user approves

        # =======================================================
        # HUMAN APPROVAL WORKFLOW - End Framework Pattern
        # =======================================================

        # ==========================================
        # STEP 1: Execute scan plan
        # ==========================================
        motor_desc = AVAILABLE_MOTORS.get(motor, motor)
        logger.info(
            f"🔄 Step 1: Executing scan: {motor} ({motor_desc}), "
            f"start={start}, stop={stop}, num={num}, detectors={detectors}"
        )
        streamer.status(f"Scanning {motor_desc} from {start} to {stop}...")

        result = bl531.scan(detectors=detectors, motor=motor, start=start, stop=stop, num=num)

        run_uid = result.run_uid
        logger.info(f"✅ Scan completed. run_uid: {run_uid}")
        streamer.status("Scan complete, retrieving data...")

        # ==========================================
        # STEP 2: Retrieve the data
        # ==========================================
        logger.info(f"📥 Step 2: Retrieving scan data for {run_uid}")

        run_data = bl531_data.get_run_data(run_uid)

        logger.info(f"✅ Data retrieved: \n{run_data}")
        streamer.status("Data retrieved successfully!")

        # ==========================================
        # STEP 3: Create formatted context
        # ==========================================
        context = RunDataContext(
            run_uid=run_uid,
            metadata=run_data.metadata,
            detector_data=run_data.detectors,
            motor_data=run_data.motors,
            other_data=run_data.other,
            available_images=list(run_data.images.keys()),
        )

        # Log summary
        summary = context.get_summary()
        logger.info(f"📊 Scan summary: \n{summary}")

        # If motor data available, stream position info
        if motor in run_data.motors and len(run_data.motors[motor]) > 0:
            positions = run_data.motors[motor]
            streamer.status(
                f"✅ Scanned {len(positions)} positions: "
                f"{motor_desc} from {positions[0]: .3f} to {positions[-1]: .3f}"
            )

        # Store and return
        result_updates = StateManager.store_context(
            state, registry.context_types.RUN_DATA_CONTEXT, context_key, context
        )

        # Clean up approval state ONLY if we actually resumed from approval
        if has_approval_resume:
            approval_cleanup = clear_approval_state()
            return {**result_updates, **approval_cleanup}

        return result_updates

    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify scan errors."""

        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout, retrying...",
                metadata={"type": "connection_error"},
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid scan parameters: {str(exc)}",
                metadata={"type": "invalid_parameter"},
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Scan error: {str(exc)}",
                metadata={"type": "execution_error"},
            )

    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""

        # Example 1: Angle scan with intensity
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="gisaxs_scan",
                capability="bl531_scan",
                task_objective=(
                    "Scan grazing incidence angle from 0.1 to 0.2 degrees "
                    "in 5 steps, measuring beam intensity."
                ),
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria=(
                    "Returns scan data with angle positions and diode " "intensity readings"
                ),
                inputs=[
                    {"MOTOR_NAME": "gi_angle"},
                    {"START_POSITION": "0.1"},
                    {"STOP_POSITION": "0.2"},
                    {"NUM_POINTS": "5"},
                    {"DETECTORS": '["diode"]'},
                ],
            ),
            scenario_description=("User: 'Scan beam intensity for grazing angle 0.1 to 0.2'"),
            notes="Angle scan with diode for intensity measurement",
        )

        # Example 2: Height scan with images
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="height_scan",
                capability="bl531_scan",
                task_objective="Scan vertical position from -1mm to 1mm in 10 steps, taking images.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns height positions and image data",
                inputs=[
                    {"MOTOR_NAME": "hexapod_motor_Tz"},
                    {"START_POSITION": "-1.0"},
                    {"STOP_POSITION": "1.0"},
                    {"NUM_POINTS": "10"},
                    {"DETECTORS": '["det"]'},
                ],
            ),
            scenario_description="User: 'Scan height from -1 to 1 mm with images'",
            notes="Vertical position scan with detector",
        )

        # Example 3: Lateral scan
        example3 = OrchestratorExample(
            step=PlannedStep(
                context_key="lateral_scan",
                capability="bl531_scan",
                task_objective="Scan lateral position from -2mm to 2mm in 5 steps, measuring intensity.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns lateral positions and intensity readings",
                inputs=[
                    {"MOTOR_NAME": "hexapod_motor_Ty"},
                    {"START_POSITION": "-2.0"},
                    {"STOP_POSITION": "2.0"},
                    {"NUM_POINTS": "5"},
                    {"DETECTORS": '["diode"]'},
                ],
            ),
            scenario_description="User: 'Move horizontally from -2 to 2 mm measuring intensity'",
            notes="Lateral (Y-axis) scan with diode",
        )

        # Example 4: Energy scan
        example4 = OrchestratorExample(
            step=PlannedStep(
                context_key="energy_scan",
                capability="bl531_scan",
                task_objective="Scan fluorescence NEXAFS from sample from 8000 to 9000 eV in 20 steps.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns energy values and detector data",
                inputs=[
                    {"MOTOR_NAME": "mono_energy"},
                    {"START_POSITION": "8000"},
                    {"STOP_POSITION": "9000"},
                    {"NUM_POINTS": "20"},
                    {"DETECTORS": '["mercury"]'},
                ],
            ),
            scenario_description="User: 'Scan fluorescence signal for energy from 8 to 9 keV'",
            notes="Energy scan use motor mono_energy)",
        )

        # Example 5: Rotation scan
        example5 = OrchestratorExample(
            step=PlannedStep(
                context_key="rotation_scan",
                capability="bl531_scan",
                task_objective="Rotate sample around Y-axis from 0 to 90 degrees in 10 steps.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns rotation angles and detector data",
                inputs=[
                    {"MOTOR_NAME": "hexapod_motor_Ry"},
                    {"START_POSITION": "0"},
                    {"STOP_POSITION": "90"},
                    {"NUM_POINTS": "10"},
                    {"DETECTORS": '["det"]'},
                ],
            ),
            scenario_description="User: 'Rotate sample from 0 to 90 degrees'",
            notes="Rotation around Y-axis with imaging",
        )

        # UPDATED Example 6: clearer notes to prevent parenthesis hallucination
        example6 = OrchestratorExample(
            step=PlannedStep(
                context_key="cr_k_edge_scan",
                capability="bl531_scan",
                task_objective="Scan energy around the Cr K-edge ±50 eV in 101 steps, measuring absorption XANES.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns energy values and diode data across the Cr edge region.",
                inputs=[
                    {"MOTOR_NAME": "mono_energy"},
                    {"START_POSITION": "ref:cr_edge.edge_energy_eV-50"},
                    {"STOP_POSITION": "ref:cr_edge.edge_energy_eV+50"},
                    {"NUM_POINTS": "101"},
                    {"DETECTORS": '["diode"]'},
                ],
            ),
            scenario_description="User: 'Scan ±50 eV around Cr K-edge'",
            # CHANGED: Removed "(+/-offset)" notation which confused the LLM
            notes="Uses ref syntax to bind edge lookup output to scan range",
        )

        return OrchestratorGuide(
            instructions=textwrap.dedent(
                """
                **bl531_scan: Scan motor and return data or take data under some specific motor value**

                ═══════════════════════════════════════════════════════════

                **AVAILABLE MOTORS:**

                - "gi_angle" → Grazing incidence angle (degrees)
                - "hexapod_motor_Ty" → Lateral/horizontal (Y-axis, mm)
                - "hexapod_motor_Tz" → Vertical/height (Z-axis, mm)
                - "hexapod_motor_Ry" → Rotation around Y-axis (degrees)
                - "hexapod_motor_Rz" → Rotation around Z-axis (degrees)
                - "mono_energy" → Energy of the beam unit in eV
                - "mercury" → Mercury detector for fluorescence measurements

                ═══════════════════════════════════════════════════════════

                **REQUIRED INPUTS FORMAT:**

                inputs: [
                    {"MOTOR_NAME": "<motor>"},
                    {"START_POSITION": "<number> or <ref>"},
                    {"STOP_POSITION": "<number> or <ref>"},
                    {"NUM_POINTS": "<integer>"},
                    {"DETECTORS": '["det"]'}
                ]

                ═══════════════════════════════════════════════════════════

                **DYNAMIC REFERENCES (CONNECTING STEPS):**

                When using a value from a previous step (like an edge energy lookup)
                to set the scan range, use the `ref:` syntax.

                Format: ref:<context_key>.<field><operator><value>

                ✅ CORRECT SYNTAX:
                "ref:mn_edge.edge_energy_eV-30"  (Subtract 30)
                "ref:mn_edge.edge_energy_eV+30"  (Add 30)
                "ref:mn_edge.edge_energy_eV"     (Exact value)

                ❌ INCORRECT (DO NOT USE PARENTHESES):
                "ref:mn_edge.edge_energy_eV(-30)"
                "ref:mn_edge.edge_energy_eV(+30)"

                **Variable Fields:**
                - XRAY_EDGE_CONTEXT usually provides: `edge_energy_eV`

                ═══════════════════════════════════════════════════════════

                **UNIT CONVERSIONS:**
                Energy: "8 keV" → "8000" (convert to eV)
                Distance: "2 mm" → "2.0" (already mm)

                """
            ),
            examples=[example1, example2, example3, example4, example5, example6],
            priority=10,
        )

    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""

        return TaskClassifierGuide(
            instructions="Use for scanning motors through a range of positions.",
            examples=[
                ClassifierExample(
                    query="Scan beam intensity for angle 0.1 to 0.2",
                    result=True,
                    reason="Scan through angle range with intensity",
                ),
                ClassifierExample(
                    query="Move horizontally from -1 to 1 mm",
                    result=True,
                    reason="Lateral position scan",
                ),
                ClassifierExample(
                    query="Scan height from 0 to 5 mm", result=True, reason="Vertical position scan"
                ),
                ClassifierExample(
                    query="Scan energy from 8 to 9 keV", result=True, reason="Energy scan"
                ),
                ClassifierExample(
                    query="Rotate sample 0 to 180 degrees", result=True, reason="Rotation scan"
                ),
                ClassifierExample(
                    query="take image at energy 10keV",
                    result=True,
                    reason="take data at specific motor value",
                ),
                ClassifierExample(
                    query="Take an image",
                    result=False,
                    reason="don't specify motor position - use bl531_count",
                ),
                ClassifierExample(
                    query="What is intensity?",
                    result=False,
                    reason="Single measurement - use bl531_count",
                ),
            ],
            actions_if_true=ClassifierActions(),
        )
