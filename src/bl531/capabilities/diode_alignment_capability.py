"""
Diode Alignment Capability for BL531 Beamline.

Executes automatic diode alignment to optimize beam position on the diode detector.
This ensures accurate intensity measurements.
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

from bl531.context_classes import AlignmentContext
from bl531.BL531API import bl531

logger = get_logger("diode_alignment_capability")
registry = get_registry()


class DiodeAlignmentCapabilityError(Exception):
    """Base exception for diode alignment capability."""
    pass


class DiodeAlignmentExecutionError(DiodeAlignmentCapabilityError):
    """Raised when diode alignment execution fails."""
    pass


@capability_node
class DiodeAlignmentCapability(BaseCapability):
    """Execute automatic diode alignment on the BL531 beamline.
    
    Automatically optimizes the beam position on the diode detector for
    accurate intensity measurements. This should be run:
    - After energy changes
    - After major beam adjustments
    - Before critical intensity measurements
    """
    
    name = "bl531_diode_alignment"
    description = "Execute automatic diode alignment to optimize beam position"
    provides = ["ALIGNMENT_CONTEXT"]
    requires = []  # No inputs needed - fully automatic
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute automatic diode alignment."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("diode_alignment_capability", state)
        
        try:
            context_key = step.get("context_key", "diode_alignment_result")
            
            logger.info("🎯 Starting automatic diode alignment")
            streamer.status("Executing automatic diode alignment procedure...")
            
            # Call API to execute diode alignment
            result = bl531.automatic_diode_alignment()
            
            logger.info(f"✅ Diode alignment completed. run_uid: {result.run_uid}")
            streamer.status(f"Diode alignment completed with run_uid: {result.run_uid}")
            
            # Create and store output context
            context = AlignmentContext(
                run_uid=result.run_uid,
                alignment_type="automatic_diode",
                timestamp=result.timestamp,
                status="completed"
            )
            
            return StateManager.store_context(
                state,
                registry.context_types.ALIGNMENT_CONTEXT,
                context_key,
                context
            )
            
        except Exception as e:
            logger.error(f"Diode alignment execution error: {e}")
            raise DiodeAlignmentExecutionError(f"Diode alignment failed: {str(e)}")
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify diode alignment errors for intelligent retry coordination."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout during diode alignment, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, DiodeAlignmentExecutionError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Diode alignment failed: {str(exc)}",
                metadata={"type": "alignment_failed"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Diode alignment error: {str(exc)}",
                metadata={"type": "unknown_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        # Example 1: Direct diode alignment request
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="diode_alignment_result",
                capability="bl531_diode_alignment",
                task_objective="Execute automatic diode alignment to optimize beam position on diode detector.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Alignment completes successfully and returns run_uid.",
                inputs=[]  # No inputs required
            ),
            scenario_description="User: 'Align the diode' or 'Optimize diode position'",
            notes="No inputs needed - alignment is fully automatic."
        )
        
        # Example 2: After energy change
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="post_energy_alignment",
                capability="bl531_diode_alignment",
                task_objective="Align diode after energy change to ensure accurate intensity readings.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Diode alignment completes successfully.",
                inputs=[]
            ),
            scenario_description="After changing energy, align diode for accurate measurements",
            notes="Best practice: align diode after energy changes"
        )
        
        # Example 3: Before intensity measurements
        example3 = OrchestratorExample(
            step=PlannedStep(
                context_key="pre_measurement_alignment",
                capability="bl531_diode_alignment",
                task_objective="Align diode before critical intensity measurements.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Diode optimally positioned.",
                inputs=[]
            ),
            scenario_description="Align before intensity scans",
            notes="Ensures maximum signal and accurate readings"
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **bl531_diode_alignment: Optimize diode position**
                
                ═══════════════════════════════════════════════════════════
                
                **PURPOSE:**
                Automatically aligns the diode detector to optimize beam position
                for accurate intensity measurements.
                
                ═══════════════════════════════════════════════════════════
                
                **WHEN TO USE:**
                
                ✅ User explicitly asks:
                - "Align the diode"
                - "Optimize diode position"
                - "Calibrate intensity detector"
                
                ✅ Best practices (optional):
                - After changing energy
                - Before critical intensity measurements
                - After major beam adjustments
                
                ═══════════════════════════════════════════════════════════
                
                **NO INPUTS REQUIRED:**
                
                This capability is fully automatic.
                
                inputs: []  (empty list)
                
                ═══════════════════════════════════════════════════════════
                
                **EXAMPLE WORKFLOWS:**
                
                1. Simple alignment:
                   User: "Align the diode"
                   → Step 1: bl531_diode_alignment (inputs: [])
                
                2. Energy change + alignment + measurement:
                   User: "Change energy to 10 keV and measure intensity"
                   → Step 1: bl531_move (energy to 10000 eV)
                   → Step 2: bl531_diode_alignment (align diode)
                   → Step 3: bl531_count (measure intensity)
                
                3. Alignment + intensity scan:
                   User: "Align diode then scan energy from 8 to 9 keV"
                   → Step 1: bl531_diode_alignment
                   → Step 2: bl531_scan (energy scan with diode)
                
                ═══════════════════════════════════════════════════════════
                
                **OUTPUT:**
                Returns ALIGNMENT_CONTEXT with run_uid for the alignment procedure.
                
                ═══════════════════════════════════════════════════════════
                """),
            examples=[example1, example2, example3],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Use for diode detector alignment and optimization.",
            examples=[
                ClassifierExample(
                    query="Align the diode",
                    result=True,
                    reason="Direct diode alignment request"
                ),
                ClassifierExample(
                    query="Optimize diode position",
                    result=True,
                    reason="Optimizing diode requires alignment"
                ),
                ClassifierExample(
                    query="Calibrate intensity detector",
                    result=True,
                    reason="Calibrating diode detector"
                ),
                ClassifierExample(
                    query="Align diode after energy change",
                    result=True,
                    reason="Alignment needed after energy adjustment"
                ),
                ClassifierExample(
                    query="Align beam on diode",
                    result=True,
                    reason="Beam alignment on diode detector"
                ),
                ClassifierExample(
                    query="Align the beamline",
                    result=False,
                    reason="General beamline alignment - use bl531_gisaxs_alignment"
                ),
                ClassifierExample(
                    query="What is beam intensity?",
                    result=False,
                    reason="Measurement question - use bl531_count"
                ),
                ClassifierExample(
                    query="Scan energy",
                    result=False,
                    reason="Scanning - use bl531_scan"
                ),
            ],
            actions_if_true=ClassifierActions()
        )