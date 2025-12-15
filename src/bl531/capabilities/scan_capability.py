"""
Scan Plan Capability for BL531 Beamline.

Executes a scan plan, retrieves the data, and returns it formatted.
This is a complete workflow: scan → retrieve → format.
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

logger = get_logger("scan_capability")
registry = get_registry()


class ScanCapabilityError(Exception):
    """Base exception for scan capability."""
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
        
        try:
            # Extract inputs from orchestrator
            inputs_list = step.get('inputs', [])
            combined_inputs = {}
            if isinstance(inputs_list, list):
                for item in inputs_list:
                    if isinstance(item, dict):
                        combined_inputs.update(item)
            else:
                combined_inputs = inputs_list if isinstance(inputs_list, dict) else {}
            
            # Extract required parameters
            motor = combined_inputs.get("MOTOR_NAME")
            start = combined_inputs.get("START_POSITION")
            stop = combined_inputs.get("STOP_POSITION")
            num = combined_inputs.get("NUM_POINTS")
            detectors = combined_inputs.get("DETECTORS", '["det"]')
            
            # Validate inputs
            if not motor or start is None or stop is None or num is None:
                raise ValueError(
                    f"Missing required scan inputs. Got: motor={motor}, start={start}, "
                    f"stop={stop}, num={num}"
                )
            
            # Validate motor is available
            if motor not in AVAILABLE_MOTORS:
                available_list = ', '.join(AVAILABLE_MOTORS.keys())
                raise ValueError(
                    f"Invalid motor: {motor}. Available motors: {available_list}"
                )
            
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
            
            # ==========================================
            # STEP 1: Execute scan plan
            # ==========================================
            motor_desc = AVAILABLE_MOTORS.get(motor, motor)
            logger.info(
                f"🔄 Step 1: Executing scan: {motor} ({motor_desc}), "
                f"start={start}, stop={stop}, num={num}, detectors={detectors}"
            )
            streamer.status(f"Scanning {motor_desc} from {start} to {stop}...")
            
            result = bl531.scan(
                detectors=detectors,
                motor=motor,
                start=start,
                stop=stop,
                num=num
            )
            
            run_uid = result.run_uid
            logger.info(f"✅ Scan completed. run_uid: {run_uid}")
            streamer.status(f"Scan complete, retrieving data...")
            
            # ==========================================
            # STEP 2: Retrieve the data
            # ==========================================
            logger.info(f"📥 Step 2: Retrieving scan data for {run_uid}")
            
            run_data = bl531_data.get_run_data(run_uid)
            
            logger.info(f"✅ Data retrieved:\n{run_data}")
            streamer.status(f"Data retrieved successfully!")
            
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
            
            # Log summary
            summary = context.get_summary()
            logger.info(f"📊 Scan summary:\n{summary}")
            
            # If motor data available, stream position info
            if motor in run_data.motors and len(run_data.motors[motor]) > 0:
                positions = run_data.motors[motor]
                streamer.status(
                    f"✅ Scanned {len(positions)} positions: "
                    f"{motor_desc} from {positions[0]:.3f} to {positions[-1]:.3f}"
                )
            
            # Store and return
            return StateManager.store_context(
                state,
                registry.context_types.RUN_DATA_CONTEXT,
                context_key,
                context
            )
            
        except Exception as e:
            logger.error(f"Scan execution error: {e}")
            raise ScanCapabilityError(f"Scan failed: {str(e)}")
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify scan errors."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid scan parameters: {str(exc)}",
                metadata={"type": "invalid_parameter"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Scan error: {str(exc)}",
                metadata={"type": "execution_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        # Example 1: Angle scan with intensity
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="gisaxs_scan",
                capability="bl531_scan",
                task_objective="Scan grazing incidence angle from 0.1 to 0.2 degrees in 5 steps, measuring beam intensity.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns scan data with angle positions and diode intensity readings",
                inputs=[
                    {"MOTOR_NAME": "gi_angle"},
                    {"START_POSITION": "0.1"},
                    {"STOP_POSITION": "0.2"},
                    {"NUM_POINTS": "5"},
                    {"DETECTORS": '["diode"]'}
                ]
            ),
            scenario_description="User: 'Scan beam intensity for grazing angle 0.1 to 0.2'",
            notes="Angle scan with diode for intensity measurement"
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
                    {"DETECTORS": '["det"]'}
                ]
            ),
            scenario_description="User: 'Scan height from -1 to 1 mm with images'",
            notes="Vertical position scan with detector"
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
                    {"DETECTORS": '["diode"]'}
                ]
            ),
            scenario_description="User: 'Move horizontally from -2 to 2 mm measuring intensity'",
            notes="Lateral (Y-axis) scan with diode"
        )

        # Example 4: Energy scan
        example4 = OrchestratorExample(
            step=PlannedStep(
                context_key="energy_scan",
                capability="bl531_scan",
                task_objective="Scan X-ray energy from 8000 to 9000 eV in 20 steps.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns energy values and detector data",
                inputs=[
                    {"MOTOR_NAME": "mono_energy"},
                    {"START_POSITION": "8000"},
                    {"STOP_POSITION": "9000"},
                    {"NUM_POINTS": "20"},
                    {"DETECTORS": '["diode"]'}
                ]
            ),
            scenario_description="User: 'Scan energy from 8 to 9 keV'",
            notes="Energy scan use motor mono_energy)"
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
                    {"DETECTORS": '["det"]'}
                ]
            ),
            scenario_description="User: 'Rotate sample from 0 to 90 degrees'",
            notes="Rotation around Y-axis with imaging"
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **bl531_scan: Scan motor and return data**
                
                ═══════════════════════════════════════════════════════════
                
                **AVAILABLE MOTORS:**
                
                - "gi_angle" → Grazing incidence angle (degrees)
                - "hexapod_motor_Ty" → Lateral/horizontal (Y-axis, mm)
                - "hexapod_motor_Tz" → Vertical/height (Z-axis, mm)
                - "hexapod_motor_Ry" → Rotation around Y-axis (degrees)
                - "hexapod_motor_Rz" → Rotation around Z-axis (degrees)
                - "mono_energy" → Energy of the beam unit in eV
                
                ═══════════════════════════════════════════════════════════
                
                **MOTOR SELECTION:**
                
                User says → Use motor
                ────────────────────────────────────────
                "angle/tilt/incidence/GISAXS" → gi_angle
                "horizontal/lateral/sideways/x/y" → hexapod_motor_Ty
                "vertical/height/up/down/z" → hexapod_motor_Tz
                "rotate Y/rotation Y" → hexapod_motor_Ry
                "rotate Z/rotation Z" → hexapod_motor_Rz
                "energy/keV/eV" → mono_energy (convert keV→eV!)
                
                ═══════════════════════════════════════════════════════════
                
                **REQUIRED INPUTS FORMAT:**
                
                inputs: [
                    {"MOTOR_NAME": "<motor>"},
                    {"START_POSITION": "<number>"},
                    {"STOP_POSITION": "<number>"},
                    {"NUM_POINTS": "<integer>"},
                    {"DETECTORS": '["det"]'} or {"DETECTORS": '["diode"]'}
                ]
                
                ⚠️  CRITICAL: 
                - All values MUST be strings: "0.1" not 0.1
                - DETECTORS must be string representation: '["det"]' not ["det"]
                - Use list format: [{...}, {...}] not single dict {...}
                
                ═══════════════════════════════════════════════════════════
                
                **DETECTOR CHOICE:**
                
                - Images/scattering patterns → '["det"]'
                - Intensity/current/flux → '["diode"]'
                
                ═══════════════════════════════════════════════════════════
                
                **UNIT CONVERSIONS:**
                
                Energy: "8 keV" → "8000" (convert to eV)
                Distance: "2 mm" → "2.0" (already mm)
                Angle: "0.15 degrees" → "0.15" (already degrees)
                
                ═══════════════════════════════════════════════════════════
                
                **EXAMPLES:**
                
                "Scan beam intensity for angle 0.1 to 0.2"
                → inputs: [
                    {"MOTOR_NAME": "gi_angle"},
                    {"START_POSITION": "0.1"},
                    {"STOP_POSITION": "0.2"},
                    {"NUM_POINTS": "5"},
                    {"DETECTORS": '["diode"]'}
                ]
                
                "Scan height -1 to 1 mm with images"
                → inputs: [
                    {"MOTOR_NAME": "hexapod_motor_Tz"},
                    {"START_POSITION": "-1.0"},
                    {"STOP_POSITION": "1.0"},
                    {"NUM_POINTS": "10"},
                    {"DETECTORS": '["det"]'}
                ]
                
                "Move horizontally -2 to 2 mm"
                → inputs: [
                    {"MOTOR_NAME": "hexapod_motor_Ty"},
                    {"START_POSITION": "-2.0"},
                    {"STOP_POSITION": "2.0"},
                    {"NUM_POINTS": "5"},
                    {"DETECTORS": '["diode"]'}
                ]
                
                "Scan energy 8 to 9 keV"
                → inputs: [
                    {"MOTOR_NAME": "mono"},
                    {"START_POSITION": "8000"},
                    {"STOP_POSITION": "9000"},
                    {"NUM_POINTS": "20"},
                    {"DETECTORS": '["diode"]'}
                ]
                
                ═══════════════════════════════════════════════════════════
                
                **OUTPUT:**
                RUN_DATA_CONTEXT with motor positions and detector arrays
                
                ═══════════════════════════════════════════════════════════
                """),
            examples=[example1, example2, example3, example4, example5],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Use for scanning motors through a range of positions.",
            examples=[
                ClassifierExample(
                    query="Scan beam intensity for angle 0.1 to 0.2",
                    result=True,
                    reason="Scan through angle range with intensity"
                ),
                ClassifierExample(
                    query="Move horizontally from -1 to 1 mm",
                    result=True,
                    reason="Lateral position scan"
                ),
                ClassifierExample(
                    query="Scan height from 0 to 5 mm",
                    result=True,
                    reason="Vertical position scan"
                ),
                ClassifierExample(
                    query="Scan energy from 8 to 9 keV",
                    result=True,
                    reason="Energy scan"
                ),
                ClassifierExample(
                    query="Rotate sample 0 to 180 degrees",
                    result=True,
                    reason="Rotation scan"
                ),
                ClassifierExample(
                    query="Take an image",
                    result=False,
                    reason="Single position - use bl531_count"
                ),
                ClassifierExample(
                    query="What is intensity?",
                    result=False,
                    reason="Single measurement - use bl531_count"
                ),
            ],
            actions_if_true=ClassifierActions()
        )