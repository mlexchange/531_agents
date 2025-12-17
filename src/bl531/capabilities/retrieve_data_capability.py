"""
Data Retrieval Capability for BL531 Beamline.

Retrieves experimental data from completed runs via Tiled.
ONLY use when run_uid is available from a previous experiment or user provides it.
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
from bl531.BL531DataAPI import bl531_data

logger = get_logger("retrieve_data_capability")
registry = get_registry()


class DataRetrievalError(Exception):
    """Base exception for data retrieval capability."""
    pass


@capability_node
class RetrieveDataCapability(BaseCapability):
    """Retrieve experimental data from a completed beamline run.
    
    IMPORTANT: This capability ONLY retrieves existing data. 
    It CANNOT collect new data - you must run an experiment first!
    
    Takes a run_uid (from SCAN_PLAN_CONTEXT, COUNT_PLAN_CONTEXT, or ALIGNMENT_CONTEXT)
    and fetches the actual experimental data.
    """
    
    name = "bl531_retrieve_data"
    description = "Retrieve experimental data from a completed run using run_uid (does NOT run experiments)"
    provides = ["RUN_DATA_CONTEXT"]
    requires = ["RUN_UID"]
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Retrieve data for a run with all arrays loaded."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("retrieve_data_capability", state)
        
        try:
            # Extract run_uid from inputs
            inputs_list = step.get('inputs', [])
            combined_inputs = {}
            if isinstance(inputs_list, list):
                for item in inputs_list:
                    if isinstance(item, dict):
                        combined_inputs.update(item)
            else:
                combined_inputs = inputs_list if isinstance(inputs_list, dict) else {}
            
            run_uid = combined_inputs.get("RUN_UID")
            
            if not run_uid:
                raise ValueError("No RUN_UID provided. Cannot retrieve data without a run_uid.")
            
            context_key = step.get("context_key", "run_data")
            
            logger.info(f"📥 Retrieving data for run_uid: {run_uid}")
            streamer.status(f"Fetching data for {run_uid}...")
            
            # Get data from Tiled - includes all arrays except images
            run_data = bl531_data.get_run_data(run_uid)
            
            logger.info(f"✅ Retrieved data:\n{run_data}")
            streamer.status(
                f"Data retrieved: {len(run_data.detectors)} detectors, "
                f"{len(run_data.motors)} motors, {len(run_data.other)} other"
            )
            
            # Create context with ALL array data loaded
            context = RunDataContext(
                run_uid=run_uid,
                metadata=run_data.metadata,
                detector_data=run_data.detectors,  # Full arrays
                motor_data=run_data.motors,        # Full arrays
                other_data=run_data.other,         # Full arrays
                available_images=list(run_data.images.keys())  # Just keys, not data
            )
            
            # Log what was loaded
            logger.info(f"📊 Loaded arrays:")
            for key, data in context.detector_data.items():
                if hasattr(data, 'shape'):
                    logger.info(f"   - detector '{key}': shape {data.shape}")
            for key, data in context.motor_data.items():
                if hasattr(data, 'shape'):
                    logger.info(f"   - motor '{key}': shape {data.shape}")
            
            return StateManager.store_context(
                state,
                registry.context_types.RUN_DATA_CONTEXT,
                context_key,
                context
            )
            
        except Exception as e:
            logger.error(f"Data retrieval error: {e}")
            raise DataRetrievalError(f"Failed to retrieve data: {str(e)}")

    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify data retrieval errors."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Tiled server connection timeout, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid run_uid: {str(exc)}",
                metadata={"type": "invalid_run_uid"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Data retrieval error: {str(exc)}",
                metadata={"type": "retrieval_failed"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        # Example 1: Scan + retrieve workflow
        scan_then_retrieve = OrchestratorExample(
            step=PlannedStep(
                context_key="scan_data",
                capability="bl531_retrieve_data",
                task_objective="Retrieve experimental data from the completed GISAXS scan.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Data retrieved successfully with detector and motor information.",
                inputs={"RUN_UID": "9e1b986b-f523-4ae1-96a8-177e0f6cc672"}
            ),
            scenario_description="Step 2 after scan: retrieve the data using run_uid from Step 1",
            notes="CRITICAL: This comes AFTER bl531_scan step which produced the run_uid"
        )
        
        # Example 2: User provides specific run_uid
        user_provided_uid = OrchestratorExample(
            step=PlannedStep(
                context_key="requested_data",
                capability="bl531_retrieve_data",
                task_objective="Retrieve data for the run_uid specified by user.",
                expected_output=registry.context_types.RUN_DATA_CONTEXT,
                success_criteria="Data retrieved for the specified run_uid.",
                inputs={"RUN_UID": "9e1b986b-f523-4ae1-96a8-177e0f6cc672"}
            ),
            scenario_description="User: 'Get data for run 9e1b986b-f523-4ae1-96a8-177e0f6cc672'",
            notes="User explicitly provides run_uid - can retrieve directly"
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **bl531_retrieve_data: Fetch data from completed experiments**
                
                ═══════════════════════════════════════════════════════════
                
                **INPUT REQUIRED:**
                
                {
                    "RUN_UID": "<actual run_uid string>"
                }
                
                ⚠️  RUN_UID must be the ACTUAL UUID, not a context_key!
                
                ═══════════════════════════════════════════════════════════
                
                **HOW TO GET RUN_UID:**
                
                From previous step - use this EXACT pattern:
                
                If Step 1 had context_key="beam_intensity":
                → "RUN_UID": "{{COUNT_PLAN_CONTEXT.beam_intensity.run_uid}}"
                
                If Step 1 had context_key="my_scan":
                → "RUN_UID": "{{SCAN_PLAN_CONTEXT.my_scan.run_uid}}"
                
                From user directly:
                → "RUN_UID": "9e1b986b-f523-4ae1-96a8-177e0f6cc672"
                
                ═══════════════════════════════════════════════════════════
                
                **CORRECT EXAMPLES:**
                
                ✅ "RUN_UID": "{{COUNT_PLAN_CONTEXT.beam_intensity.run_uid}}"
                ✅ "RUN_UID": "{{SCAN_PLAN_CONTEXT.gisaxs_scan.run_uid}}"
                ✅ "RUN_UID": "9e1b986b-f523-4ae1-96a8-177e0f6cc672"
                
                ❌ "RUN_UID": "beam_intensity"  (This is WRONG - it's just the key name!)
                ❌ "RUN_UID": "COUNT_PLAN_CONTEXT.beam_intensity"  (Missing template syntax!)
                
                ═══════════════════════════════════════════════════════════
                """),
            examples=[scan_then_retrieve, user_provided_uid],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions=textwrap.dedent("""
                Only classify as TRUE if:
                1. User wants to retrieve EXISTING data (implies run_uid is available)
                2. User explicitly provides a run_uid to fetch
                
                Classify as FALSE if:
                - User wants new measurements (need to run experiment FIRST)
                - No run_uid exists or can be referenced
                """),
            examples=[
                # TRUE - can retrieve existing data
                ClassifierExample(
                    query="Get the data from that scan",
                    result=True,
                    reason="Refers to previous scan - run_uid should exist from prior step"
                ),
                ClassifierExample(
                    query="Show me the results",
                    result=True,
                    reason="Asking for results implies experiment already ran"
                ),
                ClassifierExample(
                    query="What were the motor positions from the last run?",
                    result=True,
                    reason="Asking about past data - run_uid from previous experiment"
                ),
                ClassifierExample(
                    query="Retrieve data for run 9e1b986b-f523-4ae1-96a8-177e0f6cc672",
                    result=True,
                    reason="User explicitly provides run_uid"
                ),
                ClassifierExample(
                    query="Access data from run abc123",
                    result=True,
                    reason="User provides run_uid directly"
                ),
                
                # FALSE - need to run experiment first
                ClassifierExample(
                    query="Show me the diode readings",
                    result=False,
                    reason="No existing data - must run bl531_count FIRST to get readings"
                ),
                ClassifierExample(
                    query="What is the current intensity?",
                    result=False,
                    reason="Need to measure intensity first - use bl531_count, not retrieve"
                ),
                ClassifierExample(
                    query="Get motor positions",
                    result=False,
                    reason="No context of existing data - cannot retrieve without run_uid"
                ),
                ClassifierExample(
                    query="Take an image and show it",
                    result=False,
                    reason="Need to take image first (bl531_count), then retrieve. Not just retrieve."
                ),
                ClassifierExample(
                    query="Do a GISAXS scan",
                    result=False,
                    reason="This is running experiment, not retrieving data"
                ),
                ClassifierExample(
                    query="Measure beam intensity",
                    result=False,
                    reason="This is measurement command - use bl531_count, not retrieve"
                ),
            ],
            actions_if_true=ClassifierActions()
        )