"""
GISAXS Alignment Capability for BL531 Beamline.

Executes automatic GISAXS alignment to find the reference zero angle.
This is a prerequisite for accurate grazing incidence measurements.
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

logger = get_logger("gisaxs_alignment_capability")
registry = get_registry()


class AlignmentCapabilityError(Exception):
    """Base exception for alignment capability."""
    pass


class AlignmentExecutionError(AlignmentCapabilityError):
    """Raised when alignment execution fails."""
    pass


@capability_node
class GISAXSAlignmentCapability(BaseCapability):
    """Execute automatic GISAXS alignment on the BL531 beamline.
    
    Finds the reference zero angle (critical angle) for grazing incidence measurements.
    This should typically be run before GISAXS scans to ensure accurate angle positioning.
    """
    
    name = "bl531_gisaxs_alignment"
    description = "Execute automatic GISAXS alignment to find reference zero angle"
    provides = ["ALIGNMENT_CONTEXT"]
    requires = []  # No inputs needed - fully automatic
    
    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Execute automatic GISAXS alignment."""
        
        step = StateManager.get_current_step(state)
        streamer = get_streamer("gisaxs_alignment_capability", state)
        
        try:
            context_key = step.get("context_key", "alignment_result")
            
            logger.info("🎯 Starting automatic GISAXS alignment")
            streamer.status("Executing automatic GISAXS alignment procedure...")
            
            # Call API to submit alignment plan
            result = bl531.automatic_gisaxs_alignment()
            
            logger.info(f"✅ GISAXS alignment completed. run_uid: {result.run_uid}")
            streamer.status(f"✅ GISAXS alignment completed (run_uid: {result.run_uid})")
            
            # Create and store output context
            context = AlignmentContext(
                run_uid=result.run_uid,
                alignment_type="automatic_gisaxs",
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
            logger.error(f"GISAXS alignment execution error: {e}")
            raise AlignmentExecutionError(f"GISAXS alignment failed: {str(e)}")
    
    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify alignment errors for intelligent retry coordination."""
        
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorClassification(
                severity=ErrorSeverity.RETRIABLE,
                user_message="Beamline communication timeout during GISAXS alignment, retrying...",
                metadata={"type": "connection_error"}
            )
        elif isinstance(exc, AlignmentExecutionError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"GISAXS alignment failed: {str(exc)}",
                metadata={"type": "alignment_failed"}
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"GISAXS alignment error: {str(exc)}",
                metadata={"type": "unknown_error"}
            )
    
    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""
        
        # Example 1: Direct alignment request
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="alignment_result",
                capability="bl531_gisaxs_alignment",
                task_objective="Execute automatic GISAXS alignment to find reference zero angle.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Alignment completes successfully and returns run_uid.",
                inputs=[]  # ← Changed from {} to []
            ),
            scenario_description="User: 'Align the beamline' or 'Find reference zero angle'",
            notes="No inputs needed - alignment is fully automatic."
        )
        
        # Example 2: Pre-GISAXS alignment
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="pre_scan_alignment",
                capability="bl531_gisaxs_alignment",
                task_objective="Perform alignment before GISAXS scan to ensure accurate angle positioning.",
                expected_output=registry.context_types.ALIGNMENT_CONTEXT,
                success_criteria="Alignment completes successfully.",
                inputs=[]  # ← Changed from {} to []
            ),
            scenario_description="Alignment before GISAXS measurements",
            notes="Best practice: align before GISAXS scans for accurate results."
        )
        
        return OrchestratorGuide(
            instructions=textwrap.dedent("""
                **bl531_gisaxs_alignment: Find reference zero angle**
                
                ═══════════════════════════════════════════════════════════
                
                **PURPOSE:**
                Automatically finds the reference zero angle (critical angle) for
                grazing incidence X-ray scattering (GISAXS) measurements.
                
                ═══════════════════════════════════════════════════════════
                
                **WHEN TO USE:**
                
                ✅ User explicitly asks:
                - "Align the beamline"
                - "Find reference zero angle"
                - "Do GISAXS alignment"
                - "Calibrate grazing incidence angle"
                
                ✅ Best practices (optional):
                - Before GISAXS scans for accurate angle positioning
                - After sample mounting or major beamline changes
                
                ═══════════════════════════════════════════════════════════
                
                **NO INPUTS REQUIRED:**
                
                This capability is fully automatic.
                
                inputs: []  (empty list)
                
                ═══════════════════════════════════════════════════════════
                
                **EXAMPLE WORKFLOWS:**
                
                1. Simple alignment:
                   User: "Align the beamline"
                   → Step 1: bl531_gisaxs_alignment (inputs: [])
                
                2. Alignment + GISAXS scan:
                   User: "Align and then do GISAXS from 0.1 to 0.2"
                   → Step 1: bl531_gisaxs_alignment (inputs: [])
                   → Step 2: bl531_scan (gi_angle from 0.1 to 0.2)
                
                3. Complete GISAXS workflow:
                   User: "Prepare for GISAXS and scan angle 0.1 to 0.2"
                   → Step 1: bl531_gisaxs_alignment
                   → Step 2: bl531_scan (GISAXS parameters)
                
                ═══════════════════════════════════════════════════════════
                
                **OUTPUT:**
                Returns ALIGNMENT_CONTEXT with run_uid for the alignment procedure.
                
                ═══════════════════════════════════════════════════════════
                """),
            examples=[example1, example2],
            priority=10
        )
    
    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""
        
        return TaskClassifierGuide(
            instructions="Use for GISAXS beamline alignment and reference angle calibration.",
            examples=[
                ClassifierExample(
                    query="Align the beamline",
                    result=True,
                    reason="General beamline alignment for GISAXS"
                ),
                ClassifierExample(
                    query="Find reference zero angle",
                    result=True,
                    reason="Finding reference angle requires GISAXS alignment"
                ),
                ClassifierExample(
                    query="Do GISAXS alignment",
                    result=True,
                    reason="Explicit GISAXS alignment request"
                ),
                ClassifierExample(
                    query="Calibrate grazing incidence angle",
                    result=True,
                    reason="Angle calibration is part of GISAXS alignment"
                ),
                ClassifierExample(
                    query="Align and then scan from 0.1 to 0.2",
                    result=True,
                    reason="Includes alignment step before scan"
                ),
                ClassifierExample(
                    query="Align the diode",
                    result=False,
                    reason="Diode alignment - use bl531_diode_alignment"
                ),
                ClassifierExample(
                    query="GISAXS from 0.1 to 0.2",
                    result=False,
                    reason="Just scanning, no alignment - use bl531_scan only"
                ),
                ClassifierExample(
                    query="What is the current angle?",
                    result=False,
                    reason="Question, not alignment command"
                ),
            ],
            actions_if_true=ClassifierActions()
        )