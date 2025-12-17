"""
Motor Move Capability for BL531 Beamline.

Moves a motor to a specific position by executing a count plan with diode.
This ensures the motor is at the target position and verifies with a measurement.
"""

from typing import Dict, Any, Optional
import textwrap

from osprey.base.decorators import capability_node
from osprey.base.capability import BaseCapability
from osprey.base.errors import ErrorClassification, ErrorSeverity
from osprey.base.examples import (
    OrchestratorGuide, OrchestratorExample, PlannedStep,
    ClassifierActions, ClassifierExample, TaskClassifierGuide
)
from osprey.state import AgentState, StateManager
from osprey.registry import get_registry
from osprey.utils.logger import get_logger
from osprey.utils.streaming import get_streamer

from bl531.context_classes import RunDataContext
from bl531.BL531API import bl531
from bl531.BL531DataAPI import bl531_data

logger = get_logger("move_capability")
registry = get_registry()


class MoveCapabilityError(Exception):
    """Base exception for move capability."""
    pass


# Motor definitions for BL531 beamline
AVAILABLE_MOTORS = {
    'gi_angle': 'Grazing incidence angle',
    'hexapod_motor_Ty': 'Hexapod Y-axis translation (horizontal/lateral)',
    'hexapod_motor_Tz': 'Hexapod Z-axis translation (vertical/height)',
    'hexapod_motor_Ry': 'Hexapod rotation around Y-axis',
    'hexapod_motor_Rz': 'Hexapod rotation around Z-axis',
    'mono_energy': 'Energy of the beam unit in eV'
}

# Common energy values
ENERGY_REFERENCES = {
    'copper_k_edge': 8979,  # eV
    'cu_k_edge': 8979,
    'iron_k_edge': 7112,
    'fe_k_edge': 7112,
    'nickel_k_edge': 8333,
    'ni_k_edge': 8333,
    'cobalt_k_edge': 7709,
    'co_k_edge': 7709,
}


@capability_node
class MoveCapability(BaseCapability):
    """Move a motor to a target position using count plan.
    
    This capability:
    1. Moves motor to target position
    2. Takes a reading with diode detector (via count plan)
    3. Returns confirmation with measurement
    
    Available motors:
    - gi_angle: Grazing incidence angle
    - hexapod_motor_Ty: Lateral position (Y translation)
    - hexapod_motor_Tz: Vertical position (Z translation)
    - hexapod_motor_Ry: Rotation around Y axis
    - hexapod_motor_Rz: Rotation around Z axis
    - mono: X-ray energy in eV
    """
    
    name = "bl531_move"
    description = "Move a motor to a specific position and verify with count"
    provides = ["RUN_DATA_CONTEXT"]
    requires = ["MOTOR_NAME", "TARGET_POSITION"]
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Move motor to target position using count."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("move_capability", state)
        
        try:
            # Extract inputs
            inputs_list = step.get('inputs', [])
            combined_inputs = {}
            if isinstance(inputs_list, list):
                for item in inputs_list:
                    if isinstance(item, dict):
                        combined_inputs.update(item)
            else:
                combined_inputs = inputs_list if isinstance(inputs_list, dict) else {}
            
            # Extract parameters
            motor = combined_inputs.get("MOTOR_NAME")
            target = combined_inputs.get("TARGET_POSITION")
            
            # Validate inputs
            if not motor or target is None:
                raise ValueError(
                    f"Missing required move inputs. Got: motor={motor}, target={target}"
                )
            
            # Validate motor
            if motor not in AVAILABLE_MOTORS:
                available_list = ', '.join(AVAILABLE_MOTORS.keys())
                raise ValueError(
                    f"Invalid motor: {motor}. Available motors: {available_list}"
                )
            
            # Convert target to float
            target = float(target)
            
            context_key = step.get("context_key", "move_result")
            motor_desc = AVAILABLE_MOTORS.get(motor, motor)
            
            # ==========================================
            # STEP 1: Move motor using BL531 API
            # ==========================================

            logger.info(f"📊 Moving the motor now")
            # Move the motor
            result = bl531.scan(
                detectors=["diode"],
                motor=motor,
                start=target,
                stop=target,
                num=1
            )
            run_uid = result.run_uid
            
            logger.info(f"✅ motor movement completed. run_uid: {run_uid}")
            streamer.status(f"Verification now, retrieving data...")
            
            # ==========================================
            # STEP 2: Retrieve the data
            # ==========================================
            logger.info(f"📥 Retrieving data for {run_uid}")
            
            run_data = bl531_data.get_run_data(run_uid)
            
            logger.info(f"✅ Data retrieved")
            
            # ==========================================
            # STEP 3: Create formatted context
            # ==========================================
            context = RunDataContext(
                run_uid=run_uid,
                metadata=run_data.metadata,
                detector_data=run_data.detectors,
                motor_data=run_data.motors,
                other_data=run_data.other,
                available_images=list(run_data.images.keys())
            )
            
            # Add move information to metadata
            if 'diode' in run_data.detectors and len(run_data.detectors['diode']) > 0:
                diode_value = float(run_data.detectors['diode'][0])
                logger.info(f"✅ Move complete: {motor} = {target}, diode = {diode_value}")
                streamer.status(f"✅ {motor_desc} set to {target} (intensity: {diode_value})")
            else:
                logger.info(f"✅ Move complete: {motor} = {target}")
                streamer.status(f"✅ {motor_desc} set to {target}")
            
            # Store and return
            return StateManager.store_context(
                state,
                registry.context_types.RUN_DATA_CONTEXT,
                context_key,
                context
            )
            
        except Exception as e:
            logger.error(f"Move execution error: {e}")
            raise MoveCapabilityError(f"Move failed: {str(e)}")
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify move errors."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid move parameters: {str(exc)}",
                metadata={"type": "invalid_parameter"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Move error: {str(exc)}",
                metadata={"type": "execution_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance."""
        
        # Example 1: Set energy to copper K-edge
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="energy_set",
                capability="bl531_move",
                task_objective="Set X-ray energy to copper K-edge (8979 eV) and verify.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Energy set and verified with diode reading",
                inputs=[
                    {"MOTOR_NAME": "mono"},
                    {"TARGET_POSITION": "8979"}
                ]
            ),
            scenario_description="User: 'Change energy to copper K edge'",
            notes="Cu K-edge is 8979 eV. Takes diode reading after move."
        )

        # Example 2: Move to specific angle
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="angle_set",
                capability="bl531_move",
                task_objective="Move grazing incidence angle to 0.15 degrees and verify.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Angle set and verified with measurement",
                inputs=[
                    {"MOTOR_NAME": "gi_angle"},
                    {"TARGET_POSITION": "0.15"}
                ]
            ),
            scenario_description="User: 'Set angle to 0.15'",
            notes="Moves angle and takes verification reading"
        )
        
        # Example 3: Move height
        example3 = OrchestratorExample(
            step=PlannedStep(
                context_key="height_set",
                capability="bl531_move",
                task_objective="Move sample height to 2.5 mm and verify.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Height set with verification",
                inputs=[
                    {"MOTOR_NAME": "hexapod_motor_Tz"},
                    {"TARGET_POSITION": "2.5"}
                ]
            ),
            scenario_description="User: 'Move height to 2.5 mm'",
            notes="Vertical position change with verification"
        )
        
        # Example 4: Energy in keV
        example4 = OrchestratorExample(
            step=PlannedStep(
                context_key="energy_set_kev",
                capability="bl531_move",
                task_objective="Set X-ray energy to 10 keV (10000 eV) and verify.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Energy set and verified",
                inputs=[
                    {"MOTOR_NAME": "mono"},
                    {"TARGET_POSITION": "10000"}
                ]
            ),
            scenario_description="User: 'Set energy to 10 keV'",
            notes="Convert keV to eV: 10 keV = 10000 eV"
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **bl531_move: Move motor and verify with count**
                
                Moves motor to target position and takes diode reading for verification.
                
                ═══════════════════════════════════════════════════════════
                
                **AVAILABLE MOTORS:**
                
                - "mono_energy" → X-ray energy (eV)
                - "gi_angle" → Grazing incidence angle (degrees)
                - "hexapod_motor_Ty" → Lateral position (mm)
                - "hexapod_motor_Tz" → Vertical position (mm)
                - "hexapod_motor_Ry" → Rotation around Y (degrees)
                - "hexapod_motor_Rz" → Rotation around Z (degrees)
                
                ═══════════════════════════════════════════════════════════
                
                **MOTOR SELECTION:**
                
                User says → Motor
                ────────────────────────────────────────
                "energy/keV/eV/K-edge" → mono_energy
                "angle/tilt/incidence" → gi_angle
                "height/vertical/z" → hexapod_motor_Tz
                "lateral/horizontal/y" → hexapod_motor_Ty
                "rotate Y/rotation Y" → hexapod_motor_Ry
                "rotate Z/rotation Z" → hexapod_motor_Rz
                
                ═══════════════════════════════════════════════════════════
                
                **ENERGY REFERENCES:**
                
                Copper K-edge → 8979 eV
                Iron K-edge → 7112 eV
                Nickel K-edge → 8333 eV
                Cobalt K-edge → 7709 eV
                
                ═══════════════════════════════════════════════════════════
                
                **REQUIRED INPUTS:**
                
                inputs: [
                    {"MOTOR_NAME": "<motor>"},
                    {"TARGET_POSITION": "<value>"}
                ]
                
                ⚠️  IMPORTANT:
                - All values as strings: "8979" not 8979
                - Energy: Convert keV→eV (multiply by 1000)
                - Use list format: [{...}, {...}]
                
                ═══════════════════════════════════════════════════════════
                
                **EXAMPLES:**
                
                "Change energy to copper K edge"
                → inputs: [
                    {"MOTOR_NAME": "mono_energy"},
                    {"TARGET_POSITION": "8979"}
                ]
                
                "Set energy to 10 keV"
                → inputs: [
                    {"MOTOR_NAME": "mono_energy"},
                    {"TARGET_POSITION": "10000"}
                ]
                
                "Move angle to 0.15 degrees"
                → inputs: [
                    {"MOTOR_NAME": "gi_angle"},
                    {"TARGET_POSITION": "0.15"}
                ]
                
                "Set height to 2.5 mm"
                → inputs: [
                    {"MOTOR_NAME": "hexapod_motor_Tz"},
                    {"TARGET_POSITION": "2.5"}
                ]
                
                ═══════════════════════════════════════════════════════════
                
                **WORKFLOW:**
                
                1. Moves motor to target position
                2. Takes diode reading (count with num=1)
                3. Returns RUN_DATA_CONTEXT with verification data
                
                ═══════════════════════════════════════════════════════════
                
                **WHEN TO USE:**
                
                ✅ Use bl531_move when:
                - "Set/change/move to <value>"
                - "Go to <position>"
                - Single target position
                
                ❌ Don't use bl531_move when:
                - "Scan from X to Y" → use bl531_scan
                - "Take image" → use bl531_count
                
                ═══════════════════════════════════════════════════════════
                """),
            examples=[example1, example2, example3, example4],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Classifier guidance."""
        
        return TaskClassifierGuide(
            instructions="Use for moving motors to specific positions (not scanning).",
            examples=[
                ClassifierExample(
                    query="Change energy to copper K edge",
                    result=True,
                    reason="Set energy to specific value"
                ),
                ClassifierExample(
                    query="Set energy to 10 keV",
                    result=True,
                    reason="Move mono to target energy"
                ),
                ClassifierExample(
                    query="Move angle to 0.15",
                    result=True,
                    reason="Single position movement"
                ),
                ClassifierExample(
                    query="Set height to 2.5 mm",
                    result=True,
                    reason="Move to target height"
                ),
                ClassifierExample(
                    query="Go to iron K edge",
                    result=True,
                    reason="Move energy to specific edge"
                ),
                ClassifierExample(
                    query="Scan energy from 8 to 9 keV",
                    result=False,
                    reason="Scanning - use bl531_scan"
                ),
                ClassifierExample(
                    query="Take an image",
                    result=False,
                    reason="Measurement only - use bl531_count"
                ),
            ],
            actions_if_true=ClassifierActions()
        )