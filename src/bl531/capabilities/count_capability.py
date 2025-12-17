"""
Count Plan Capability for BL531 Beamline.

Executes a count plan, retrieves the data, and returns it formatted.
This is a complete workflow: measure → retrieve → format.
"""

from typing import Dict, Any, Optional
import textwrap
from datetime import datetime

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

logger = get_logger("count_capability")
registry = get_registry()


class CountCapabilityError(Exception):
    """Base exception for count capability."""
    pass


@capability_node
class CountCapability(BaseCapability):
    """Execute count plan, retrieve data, and return formatted results.
    
    This capability does the complete workflow:
    1. Execute count plan (measure with detectors)
    2. Retrieve the data using run_uid
    3. Return formatted data ready for user
    """
    
    name = "bl531_count"
    description = "Execute count plan and return formatted data"
    provides = ["RUN_DATA_CONTEXT"]
    requires = ["DETECTORS", "NUM_READINGS"]
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute count plan and retrieve data."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("count_capability", state)
        
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
            
            # Get parameters
            detectors = combined_inputs.get("DETECTORS")
            num = combined_inputs.get("NUM_READINGS")
            
            # Convert types
            num = int(num)
            
            # Parse detectors
            if isinstance(detectors, str):
                import ast
                try:
                    detectors = ast.literal_eval(detectors)
                except (ValueError, SyntaxError):
                    detectors = [detectors]
            
            if not isinstance(detectors, list):
                detectors = [detectors]
            
            context_key = step.get("context_key", "count_result")
            
            # ==========================================
            # STEP 1: Execute count plan
            # ==========================================
            logger.info(f"📊 Step 1: Executing count plan: detectors={detectors}, num={num}")
            streamer.status(f"Measuring with {detectors}...")
            
            result = bl531.count(detectors=detectors, num=num)
            run_uid = result.run_uid
            
            logger.info(f"✅ Count completed. run_uid: {run_uid}")
            streamer.status(f"Measurement complete, retrieving data...")
            
            # ==========================================
            # STEP 2: Retrieve the data
            # ==========================================
            logger.info(f"📥 Step 2: Retrieving data for {run_uid}")
            
            run_data = bl531_data.get_run_data(run_uid)
            
            logger.info(f"✅ Data retrieved:\n{run_data}")
            streamer.status(f"Data retrieved successfully!")
            
            # ==========================================
            # STEP 3: Create formatted context
            # ==========================================
            # Create context with ALL array data loaded
            context = RunDataContext(
                run_uid=run_uid,
                metadata=run_data.metadata,
                detector_data=run_data.detectors,  # Full arrays
                motor_data=run_data.motors,        # Full arrays
                other_data=run_data.other,         # Full arrays
                available_images=list(run_data.images.keys())  # Just keys, not data
            )
            logger.info(context)
            # Store and return
            return StateManager.store_context(
                state,
                registry.context_types.RUN_DATA_CONTEXT,
                context_key,
                context
            )
            
        except Exception as e:
            logger.error(f"Count execution error: {e}")
            raise CountCapabilityError(f"Count failed: {str(e)}")
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify errors."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout, retrying...",
                metadata={"type": "connection_error"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Count error: {str(exc)}",
                metadata={"type": "execution_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance."""
        
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="intensity_data",
                capability="bl531_count",
                task_objective="Measure beam intensity and return the value for display to user.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns RUN_DATA_CONTEXT with detector values accessible via get_summary()['beam_intensity'] or ['measurements']['diode']",
                inputs={
                    "DETECTORS": ["diode"],
                    "NUM_READINGS": "1"
                }
            ),
            scenario_description="User: 'What is the beam intensity?'",
            notes="Output: RUN_DATA_CONTEXT.get_summary() returns dict with 'beam_intensity' and 'measurements' fields containing actual values"
        )
        
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="image_data",
                capability="bl531_count",
                task_objective="Take scattering image and return metadata.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Returns RUN_DATA_CONTEXT with image availability info in get_summary()['available_images']",
                inputs={
                    "DETECTORS": ["det"],
                    "NUM_READINGS": "1"
                }
            ),
            scenario_description="User: 'Take an image'",
            notes="Output: RUN_DATA_CONTEXT.get_summary() contains run_uid and available_images list"
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **bl531_count: Measure and return data automatically**
                
                Executes measurement → retrieves data → returns formatted results
                
                ═══════════════════════════════════════════════════════════
                
                **INPUTS:**
                
                {
                    "DETECTORS": ["det"] or ["diode"],
                    "NUM_READINGS": "1" or "3" or "5"
                }
                
                **DETECTOR CHOICE:**
                - Images → ["det"]
                - Intensity → ["diode"]
                
                ═══════════════════════════════════════════════════════════
                
                **EXAMPLES:**
                
                "What is beam intensity?"
                → inputs: {"DETECTORS": ["diode"], "NUM_READINGS": "1"}
                → context_key: "intensity_data"
                
                "Take an image"
                → inputs: {"DETECTORS": ["det"], "NUM_READINGS": "1"}
                → context_key: "image_data"
                
                "Take 3 images"
                → inputs: {"DETECTORS": ["det"], "NUM_READINGS": "3"}
                → context_key: "multi_images"
                
                ═══════════════════════════════════════════════════════════
                
                **OUTPUT - RUN_DATA_CONTEXT:**
                
                Contains measurement data accessible via:
                
                summary = context.RUN_DATA_CONTEXT.<context_key>.get_summary()
                
                For INTENSITY measurements (diode):
                - summary['beam_intensity'] → the intensity value
                - summary['measurements']['diode'] → same value
                - summary['measurements']['ts_diode'] → timestamp
                
                For IMAGE captures (det):
                - summary['available_images'] → list of image keys
                - summary['run_uid'] → for accessing images later
                
                IMPORTANT: Always use get_summary() to access values!
                
                ═══════════════════════════════════════════════════════════
                """),
            examples=[example1, example2],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Classifier guidance."""
        
        return TaskClassifierGuide(
            instructions="Use for measurements at current position (no motor movement).",
            examples=[
                ClassifierExample(
                    query="What is beam intensity?",
                    result=True,
                    reason="Measure intensity at current position"
                ),
                ClassifierExample(
                    query="Take an image",
                    result=True,
                    reason="Take image at current position"
                ),
                ClassifierExample(
                    query="Scan from 0.1 to 0.2",
                    result=False,
                    reason="Scanning - use bl531_scan"
                ),
            ],
            actions_if_true=ClassifierActions()
        )