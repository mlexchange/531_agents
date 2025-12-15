"""
BL531 Beamline Context Classes.

These define the data structures that capabilities exchange and store in agent state.
Each context class represents a distinct data type returned by beamline operations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT CLASSES FOR BL531:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RunDataContext
   - Returned by: count, scan, move capabilities
   - Contains: run_uid, detector data, motor data, arrays
   - Use: For accessing measurement results

2. AlignmentContext
   - Returned by: GISAXS alignment, diode alignment
   - Contains: run_uid, alignment_type, status, timestamp
   - Use: For tracking alignment procedures

3. ScanParametersContext
   - Internal: Used by orchestrator to pass scan parameters
   - Contains: motor, start, stop, num_points, detectors
   - Use: Parameter passing between orchestrator and scan capability

All contexts return run_uid which can be used to retrieve and analyze actual data.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, ClassVar
from pydantic import Field
from osprey.context.base import CapabilityContext


class ScanParametersContext(CapabilityContext):
    """Parameters for executing a scan plan.
    
    The LLM orchestrator extracts these from the user query and creates
    this context, which the scan capability then consumes.
    """
    
    CONTEXT_TYPE: ClassVar[str] = "SCAN_PARAMETERS"
    CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
    motor: str = Field(
        description="Motor to scan: 'hexapod_motor_Ry', 'hexapod_motor_Ty', or 'hexapod_motor_Tz'"
    )
    
    start: float = Field(
        description="Starting position for the scan"
    )
    
    stop: float = Field(
        description="Ending position for the scan"
    )
    
    num_points: int = Field(
        description="Number of measurement points in the scan"
    )
    
    detectors: List[str] = Field(
        default_factory=lambda: ["det"],
        description="List of detectors to read: ['diode'], ['det'], or ['diode', 'det']"
    )
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide access information for LLM."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "access_pattern": f"context.SCAN_PARAMETERS.{key_ref}",
            "available_fields": ["motor", "start", "stop", "num_points", "detectors"],
            "example_usage": f"""# Access scan parameters
motor = context.SCAN_PARAMETERS.{key_ref}.motor
start = context.SCAN_PARAMETERS.{key_ref}.start
stop = context.SCAN_PARAMETERS.{key_ref}.stop
num_points = context.SCAN_PARAMETERS.{key_ref}.num_points
detectors = context.SCAN_PARAMETERS.{key_ref}.detectors""",
            "data_structure": "Single parameter set for one scan operation"
        }
    
    def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate human-readable summary."""
        return {
            "type": "Scan Parameters",
            "motor": self.motor,
            "scan_range": f"{self.start} to {self.stop}",
            "num_points": self.num_points,
            "detectors": ", ".join(self.detectors)
        }


class AlignmentContext(CapabilityContext):
    """Result from automatic alignment procedures.
    
    Used by:
    - GISAXS alignment (finds reference zero angle)
    - Diode alignment (optimizes beam position on diode)
    
    The alignment_type field distinguishes between different alignment procedures.
    """
    
    CONTEXT_TYPE: ClassVar[str] = "ALIGNMENT_CONTEXT"
    CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
    run_uid: str = Field(
        description="Unique identifier for the alignment run in the data catalog"
    )
    
    alignment_type: str = Field(
        description="Type of alignment performed (e.g., 'automatic_gisaxs', 'automatic_diode')"
    )
    
    timestamp: datetime = Field(
        description="When the alignment was performed"
    )
    
    status: str = Field(
        default="completed",
        description="Alignment status: 'completed', 'failed', 'in_progress'"
    )
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide access information for LLM."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "access_pattern": f"context.ALIGNMENT_CONTEXT.{key_ref}",
            "available_fields": ["run_uid", "alignment_type", "timestamp", "status"],
            "example_usage": f"""# Access alignment results
run_uid = context.ALIGNMENT_CONTEXT.{key_ref}.run_uid
status = context.ALIGNMENT_CONTEXT.{key_ref}.status
timestamp = context.ALIGNMENT_CONTEXT.{key_ref}.timestamp""",
            "data_structure": "Single alignment result"
        }
    
    def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate human-readable summary."""
        
        # Friendly names for alignment types
        alignment_names = {
            "automatic_gisaxs": "GISAXS Alignment",
            "automatic_diode": "Diode Alignment"
        }
        
        return {
            "type": alignment_names.get(self.alignment_type, "Alignment"),
            "alignment_type": self.alignment_type,
            "status": self.status,
            "run_uid": self.run_uid,
            "timestamp": self.timestamp.isoformat()
        }


class RunDataContext(CapabilityContext):
    """Retrieved experimental data from a beamline run with all arrays."""
    
    CONTEXT_TYPE: ClassVar[str] = "RUN_DATA_CONTEXT"
    CONTEXT_CATEGORY: ClassVar[str] = "COMPUTATIONAL_DATA"
    
    run_uid: str = Field(
        description="Unique identifier for the run"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Run metadata (plan name, sample info, timestamps, etc.)"
    )
    
    detector_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detector readings as arrays (e.g., diode: [100.5, 102.3, ...])"
    )
    
    motor_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Motor positions as arrays (e.g., gi_angle: [0.1, 0.12, ...])"
    )
    
    other_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Other data arrays (timestamps, counters, etc.)"
    )
    
    available_images: List[str] = Field(
        default_factory=list,
        description="List of available image keys"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When data was retrieved"
    )
    
    def get_summary(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate summary with actual measurement values."""
        
        # Extract detector values from arrays
        detector_values = {}
        for key, data in self.detector_data.items():
            if hasattr(data, 'tolist'):
                values = data.tolist()
                detector_values[key] = values[0] if len(values) == 1 else values
            else:
                detector_values[key] = data
        
        # Extract motor values
        motor_values = {}
        for key, data in self.motor_data.items():
            if hasattr(data, 'tolist'):
                values = data.tolist()
                motor_values[key] = values[0] if len(values) == 1 else values
            else:
                motor_values[key] = data
        
        summary = {
            "type": "Measurement Results",
            "run_uid": self.run_uid,
            "plan": self.metadata.get("plan_name", "count"),
            "measurements": detector_values,  # ← Actual values!
            "motor_positions": motor_values,
            "data_points": len(next(iter(self.detector_data.values()))) if self.detector_data else 0
        }
        
        # Add explicit beam_intensity if diode present
        if "diode" in detector_values:
            summary["beam_intensity"] = detector_values["diode"]
        
        return summary
    
    def get_access_details(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Provide access information for LLM."""
        key_ref = key_name if key_name else "key_name"
        
        return {
            "access_pattern": f"context.RUN_DATA_CONTEXT.{key_ref}",
            "available_fields": ["run_uid", "metadata", "measurements", "beam_intensity"],
            "example_usage": f"""# Get measurement values
summary = context.RUN_DATA_CONTEXT.{key_ref}.get_summary()

# Beam intensity
intensity = summary['beam_intensity']  # Direct
# or
intensity = summary['measurements']['diode']

# Motor positions
positions = summary['motor_positions']""",
        }