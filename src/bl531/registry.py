"""
BL531 Application Registry.

This registry registers all BL531-specific capabilities and context classes
with the Alpha Berkeley Framework. It uses the COMPACT style which automatically
includes framework capabilities (routing, memory, Python, etc.).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BL531 COMPONENTS REGISTERED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAPABILITIES:
  - bl531_count: Execute count plan and return data
  - bl531_scan: Execute scan plan and return data
  - bl531_gisaxs_alignment: Execute automatic GISAXS alignment
  - bl531_retrieve_data: Retrieve data from completed runs

CONTEXT CLASSES:
  - RUN_DATA_CONTEXT: Measurement data with detector/motor values
  - ALIGNMENT_CONTEXT: Output from alignment capability

FRAMEWORK CAPABILITIES (Automatic):
  - routing: Routes tasks to appropriate capabilities
  - memory: Short and long-term memory management
  - python: Execute Python code for data analysis
  - classifier: Classify tasks to determine required capabilities
  - respond: Communicate results to user

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from osprey.registry import (
    extend_framework_registry,
    CapabilityRegistration,
    ContextClassRegistration,
    RegistryConfig,
    RegistryConfigProvider
)


class Bl531RegistryProvider(RegistryConfigProvider):
    """Registry provider for BL531 beamline application.
    
    Registers all BL531-specific capabilities and context classes.
    The framework discovers and uses this class at startup.
    """
    
    def get_registry_config(self) -> RegistryConfig:
        """Get application registry configuration.
        
        Returns:
            RegistryConfig: Complete registry with framework + BL531 components
        """
        
        return extend_framework_registry(
            
            # ┌────────────────────────────────────────────────────────────┐
            # │ CAPABILITIES: BL531 Beamline Control Plans                 │
            # └────────────────────────────────────────────────────────────┘
            
            capabilities=[
                
                # ────────────────────────────────────────────────────────
                # COUNT CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes count plan, retrieves data, returns formatted results
                # Complete workflow: measure → retrieve → format
                CapabilityRegistration(
                    name="bl531_count",
                    module_path="bl531.capabilities.count_capability",
                    class_name="CountCapability",
                    description="Execute count plan and return measurement data (detectors, no motor movement)",
                    provides=["RUN_DATA_CONTEXT"],
                    requires=["DETECTORS", "NUM_READINGS"]
                ),

                # ────────────────────────────────────────────────────────
                # SCAN CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes scan plan, retrieves data, returns formatted results
                # Complete workflow: scan → retrieve → format
                CapabilityRegistration(
                    name="bl531_scan",
                    module_path="bl531.capabilities.scan_capability",
                    class_name="ScanCapability",
                    description="Execute scan plan and return scan data (motor + detectors)",
                    provides=["RUN_DATA_CONTEXT"],
                    requires=["MOTOR_NAME", "START_POSITION", "STOP_POSITION", "NUM_POINTS", "DETECTORS"]
                ),
                
                # ────────────────────────────────────────────────────────
                # GISAXS ALIGNMENT CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes automatic GISAXS alignment to find reference zero angle
                CapabilityRegistration(
                    name="bl531_gisaxs_alignment",
                    module_path="bl531.capabilities.gisaxs_alignment_capability",
                    class_name="GISAXSAlignmentCapability",
                    description="Execute automatic GISAXS alignment to find reference zero angle",
                    provides=["ALIGNMENT_CONTEXT"],
                    requires=[]
                ),

                # ────────────────────────────────────────────────────────
                # DIODE ALIGNMENT CAPABILITY
                # ────────────────────────────────────────────────────────
                # Executes automatic diode alignment to find optimum position for diode

                CapabilityRegistration(
                    name="bl531_diode_alignment",
                    module_path="bl531.capabilities.diode_alignment_capability",
                    class_name="DiodeAlignmentCapability",
                    description="Execute automatic diode alignment to optimize beam position",
                    provides=["ALIGNMENT_CONTEXT"],
                    requires=[]
                ),
                
                # ────────────────────────────────────────────────────────
                # RETRIEVE DATA CAPABILITY
                # ────────────────────────────────────────────────────────
                # Retrieves data from completed runs using run_uid
                # For manual data access or re-retrieving past experiments
                CapabilityRegistration(
                    name="bl531_retrieve_data",
                    module_path="bl531.capabilities.retrieve_data_capability",
                    class_name="RetrieveDataCapability",
                    description="Retrieve experimental data from completed runs using run_uid",
                    provides=["RUN_DATA_CONTEXT"],
                    requires=["RUN_UID"]
                ),

                CapabilityRegistration(
                    name="bl531_move",
                    module_path="bl531.capabilities.move_capability",
                    class_name="MoveCapability",
                    description="Move a motor to a specific position",
                    provides=[],
                    requires=["MOTOR_NAME", "TARGET_POSITION"]
                ),
                
            ],
            
            # ┌────────────────────────────────────────────────────────────┐
            # │ CONTEXT CLASSES: Data structures for capability outputs    │
            # └────────────────────────────────────────────────────────────┘

            context_classes=[
                
                # ────────────────────────────────────────────────────────
                # RUN DATA CONTEXT
                # ────────────────────────────────────────────────────────
                # Complete experimental data from a run
                # Contains: detector values, motor positions, metadata, arrays
                # Returned by: bl531_count, bl531_scan, bl531_retrieve_data
                ContextClassRegistration(
                    context_type="RUN_DATA_CONTEXT",
                    module_path="bl531.context_classes",
                    class_name="RunDataContext"
                ),
                
                # ────────────────────────────────────────────────────────
                # ALIGNMENT CONTEXT
                # ────────────────────────────────────────────────────────
                # Output from GISAXS alignment
                # Contains: run_uid, alignment_type, status, timestamp
                ContextClassRegistration(
                    context_type="ALIGNMENT_CONTEXT",
                    module_path="bl531.context_classes",
                    class_name="AlignmentContext"
                ),
                
            ],
            
            # No data sources needed for BL531 (pure control API)
            data_sources=[],
            
            # No custom prompt providers needed
            framework_prompt_providers=[],
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USAGE NOTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# WHAT GETS REGISTERED:
#
# Capabilities (4):
#   1. bl531_count - Measure with detectors and return data
#   2. bl531_scan - Scan motor and return data
#   3. bl531_gisaxs_alignment - Automatic alignment
#   4. bl531_retrieve_data - Fetch data from past runs
#
# Context Classes (2):
#   1. RUN_DATA_CONTEXT - Measurement data (detectors, motors, arrays)
#   2. ALIGNMENT_CONTEXT - Alignment results
#
# Framework Capabilities (Automatic, ~6):
#   - routing: Task routing between capabilities
#   - memory: Context memory management
#   - python: Python code execution for analysis
#   - classifier: Task classification and planning
#   - respond: Communicate with user
#   - user_approval: Request user confirmation (if needed)
#
# DATA FLOW:
#
#   User Query: "What is beam intensity?"
#       ↓
#   Classifier → Recognize measurement request
#       ↓
#   Router → Route to bl531_count
#       ↓
#   bl531_count:
#       1. Submit count plan (detectors=["diode"])
#       2. Retrieve data (get run_uid)
#       3. Format data (create RUN_DATA_CONTEXT)
#       ↓
#   Context Store → Save RUN_DATA_CONTEXT with actual values
#       ↓
#   Respond → Display: "Beam intensity is -3.632"
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXAMPLE CONVERSATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Example 1: Simple measurement
# -------------------------------
# User: "What is beam intensity?"
# System:
#   1. bl531_count(detectors=["diode"], num=1)
#   2. Returns RUN_DATA_CONTEXT with beam_intensity=-3.632
#   3. Respond: "The beam intensity is -3.632"
#
# Example 2: Scan
# ----------------
# User: "Scan angle from 0.1 to 0.2 in 5 steps"
# System:
#   1. bl531_scan(motor="gi_angle", start=0.1, stop=0.2, num=5)
#   2. Returns RUN_DATA_CONTEXT with arrays
#   3. Respond: "Scan completed. 5 measurements at angles [0.1, 0.125, 0.15, 0.175, 0.2]"
#
# Example 3: Alignment
# ---------------------
# User: "Align the beamline"
# System:
#   1. bl531_gisaxs_alignment()
#   2. Returns ALIGNMENT_CONTEXT with run_uid
#   3. Respond: "Alignment completed with run_uid: abc123..."
#
# Example 4: Retrieve past data
# ------------------------------
# User: "Get data for run abc-123-xyz"
# System:
#   1. bl531_retrieve_data(run_uid="abc-123-xyz")
#   2. Returns RUN_DATA_CONTEXT with data
#   3. Respond: "Retrieved data shows beam intensity was -3.8 at that time"
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━