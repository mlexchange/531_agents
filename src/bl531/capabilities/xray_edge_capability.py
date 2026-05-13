"""
X-ray Edge Energy Capability for BL531 Beamline.

Retrieves X-ray absorption edge energies (K, L, M edges) for elements
using the xraydb library as the primary source and the Henke LBL database
for verification. Essential for planning resonant scattering experiments.
"""

import re
import textwrap
from typing import Any, Dict, List, Optional

# isort: off
import requests

from osprey.base.capability import BaseCapability  # noqa: I100
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
from bl531.context_classes import XrayEdgeContext  # noqa: I100 bug in linter

logger = get_logger("xray_edge_capability")
registry = get_registry()

# ==============================================================================
# HENKE LBL DATABASE ACCESS CLASS
# ==============================================================================


class HenkeXrayData:
    """
    A class to retrieve X-ray edge energies from the Henke LBL database.
    This serves as a secondary verification source.
    """

    def __init__(self):
        self.data_url = "https://henke.lbl.gov/cgi-bin/pert_cgi.pl"
        self.headers = {
            "User-Agent": "osprey-bl531-capability/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://henke.lbl.gov",
            "Referer": "https://henke.lbl.gov/optical_constants/pert_form.html",
        }

    def get_all_edges(self, element: str) -> Optional[Dict[str, float]]:
        """
        Get all edge energies for an element from the Henke database.
        Returns a dictionary of edge energies or None on failure.
        """
        payload = {"Element": element, "Energy": "10000"}  # Energy is a dummy value
        try:
            response = requests.post(self.data_url, data=payload, headers=self.headers, timeout=5)
            response.raise_for_status()

            # Use regex to find the "Electron Binding Energies" section
            edge_pattern = re.compile(r"([A-Z]\d?)\s+([\d.]+)\s+\(ref\.\d+\)")
            edge_matches = edge_pattern.findall(response.text)

            if not edge_matches:
                return {}

            edges = {edge_name: float(edge_energy) for edge_name, edge_energy in edge_matches}

            # Normalize K1 to K for consistency with xraydb
            if "K1" in edges:
                edges["K"] = edges.pop("K1")

            return edges
        except requests.exceptions.RequestException as e:
            logger.warning(f"Henke DB request failed for {element}: {e}")
            return None


class XrayEdgeCapabilityError(Exception):
    """Base exception for X-ray edge capability."""


@capability_node
class XrayEdgeCapability(BaseCapability):
    """Retrieve X-ray absorption edge energies for elements.

    Uses xraydb to provide accurate edge energy data for:
    - K-edge (most common for resonant scattering)
    - L-edges (L1, L2, L3)
    - M-edges (M1-M5)

    Essential for planning resonant scattering experiments where the
    X-ray energy must be tuned near an absorption edge of the sample.
    """

    name = "xray_edge_lookup"
    description = "Get X-ray absorption edge energies (K, L, M) for elements"
    provides = ["XRAY_EDGE_CONTEXT"]
    requires: List[str] = []  # No context inputs required - uses parameters instead

    @staticmethod
    async def execute(state: AgentState, **kwargs) -> Dict[str, Any]:
        """Retrieve edge energy for specified element and edge type."""
        step = StateManager.get_current_step(state)
        streamer = get_streamer("xray_edge_capability", state)
        henke_db = HenkeXrayData()

        try:
            import xraydb

            # Extract parameters (literal values, not context references)
            parameters = step.get("parameters", {})
            element = parameters.get("ELEMENT")
            edge_type = parameters.get("EDGE_TYPE", "K").upper()

            if not element:
                raise ValueError("ELEMENT is required (e.g., 'Fe', 'Cu', 'Ti')")
            element = element.strip().capitalize()

            # ==========================================
            # STEP 1: Look up element with xraydb (Primary Source)
            # ==========================================
            logger.info(f"🔍 Looking up element '{element}' using xraydb...")
            streamer.status(f"Looking up {element} edge using xraydb...")

            try:
                atomic_number = xraydb.atomic_number(element)
            except (ValueError, KeyError) as e:
                raise ValueError(f"Invalid element symbol: '{element}'") from e
            logger.info(f"✅ Found {element} (Z={atomic_number}) with xraydb.")

            # ==========================================
            # STEP 2: Get all edges from xraydb
            # ==========================================
            all_edges_xraydb = {}
            edge_types_to_check = ["K", "L1", "L2", "L3", "M1", "M2", "M3", "M4", "M5"]
            for edge in edge_types_to_check:
                try:
                    energy = xraydb.xray_edge(element, edge).energy
                    if energy > 0:
                        all_edges_xraydb[edge] = energy
                except (ValueError, AttributeError):
                    continue

            if not all_edges_xraydb:
                raise XrayEdgeCapabilityError(
                    f"No absorption edge data found for {element} in xraydb."
                )

            # ==========================================
            # STEP 3: Handle requested edge
            # ==========================================
            requested_edge_energy = all_edges_xraydb.get(edge_type)
            if not requested_edge_energy:
                available = ", ".join(sorted(all_edges_xraydb.keys()))
                logger.warning(
                    f"Requested edge '{edge_type}' not in xraydb for {element}. Available: {available}"
                )
                # Default to K-edge if available, otherwise first available
                default_edge = (
                    "K" if "K" in all_edges_xraydb else sorted(all_edges_xraydb.keys())[0]
                )
                requested_edge_energy = all_edges_xraydb[default_edge]
                streamer.status(
                    f"⚠️ Edge '{edge_type}' not found. Defaulting to {default_edge}-edge."
                )
                edge_type = default_edge

            logger.info(
                f"✅ Found {element} {edge_type}-edge in xraydb: {requested_edge_energy: .1f} eV"
            )
            streamer.status(
                f"Found {element} {edge_type}-edge in xraydb: {requested_edge_energy: .1f} eV"
            )

            # ==========================================
            # STEP 4: Verify with Henke LBL Database (Secondary Source)
            # ==========================================
            logger.info(f"🌐 Verifying edge energy for {element} with Henke LBL database...")
            streamer.status("Verifying with Henke LBL database...")

            all_edges_henke = henke_db.get_all_edges(element)
            if all_edges_henke is not None:
                henke_energy = all_edges_henke.get(edge_type)
                if henke_energy:
                    diff = abs(requested_edge_energy - henke_energy)
                    logger.info(
                        f"Henke DB value for {edge_type}-edge: {henke_energy: .1f} eV (Diff: {diff: .2f} eV)"
                    )
                    if diff < 2.0:  # Tolerance of 2 eV
                        streamer.status(
                            f"✅ Verification successful. Henke DB value is {henke_energy: .1f} eV."
                        )
                    else:
                        msg = (
                            f"⚠️ Verification shows a difference. "
                            f"Henke DB value is {henke_energy: .1f} eV. Using xraydb value."
                        )
                        streamer.status(msg)
                        logger.warning(msg)
                else:
                    streamer.status(f"ⓘ {edge_type}-edge NOT in Henke DB for verification.")
                    logger.info(f"Edge '{edge_type}' NOT in Henke DB for {element}.")
            else:
                streamer.status("Could not connect to Henke DB for verification.")

            # ==========================================
            # STEP 5: Create formatted context
            # ==========================================
            context_key = step.get("context_key", "edge_energy")
            context = XrayEdgeContext(
                element=element,
                atomic_number=atomic_number,
                edge_type=edge_type,
                edge_energy_eV=requested_edge_energy,
                edge_energy_keV=requested_edge_energy / 1000,
                all_edges=all_edges_xraydb,
            )

            summary = context.get_summary()
            logger.info(f"📊 Final edge energy summary: \n{summary}")
            streamer.status(
                f"✅ Confirmed {element} {edge_type}-edge: {requested_edge_energy: .1f} eV "
                f"({requested_edge_energy/1000: .3f} keV)"
            )

            return StateManager.store_context(
                state, registry.context_types.XRAY_EDGE_CONTEXT, context_key, context
            )

        except ImportError as e:
            logger.error("xraydb library not installed")
            raise XrayEdgeCapabilityError(
                "xraydb library not installed. Install with: pip install xraydb"
            ) from e
        except Exception as e:
            logger.error(f"Edge lookup error: {e}")
            raise XrayEdgeCapabilityError(f"Edge lookup failed: {str(e)}")

    @staticmethod
    def classify_error(exc: Exception, context: dict) -> ErrorClassification:
        """Classify edge lookup errors."""

        if isinstance(exc, ImportError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message="xraydb library not available. Contact beamline staff.",
                metadata={"type": "library_missing"},
            )
        elif isinstance(exc, ValueError):
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Invalid element or edge type: {str(exc)}",
                metadata={"type": "invalid_element"},
            )
        else:
            return ErrorClassification(
                severity=ErrorSeverity.CRITICAL,
                user_message=f"Edge lookup error: {str(exc)}",
                metadata={"type": "lookup_error"},
            )

    def _create_orchestrator_guide(self) -> Optional[OrchestratorGuide]:
        """Provide orchestration guidance for the AI planner."""

        # Example 1: Iron K-edge
        example1 = OrchestratorExample(
            step=PlannedStep(
                context_key="fe_k_edge",
                capability="xray_edge_lookup",
                task_objective="Get the K-edge energy for iron (Fe) for resonant scattering setup.",
                expected_output=registry.context_types.XRAY_EDGE_CONTEXT,
                success_criteria="Returns Fe K-edge energy in eV and keV",
                inputs=[],  # No context inputs needed
                parameters={"ELEMENT": "Fe", "EDGE_TYPE": "K"},
            ),
            scenario_description="User: 'What is the K-edge of iron?'",
            notes="Iron K-edge is commonly used for resonant scattering studies",
        )

        # Example 2: Copper K-edge (default)
        example2 = OrchestratorExample(
            step=PlannedStep(
                context_key="cu_edge",
                capability="xray_edge_lookup",
                task_objective="Get the K-edge energy for copper.",
                expected_output=registry.context_types.XRAY_EDGE_CONTEXT,
                success_criteria="Returns Cu K-edge energy",
                inputs=[],  # No context inputs needed
                parameters={"ELEMENT": "Cu"},  # EDGE_TYPE will default to K
            ),
            scenario_description="User: 'Get copper edge energy'",
            notes="EDGE_TYPE defaults to K if not specified",
        )

        # Example 3: Nickel L-edge
        example3 = OrchestratorExample(
            step=PlannedStep(
                context_key="ni_l3_edge",
                capability="xray_edge_lookup",
                task_objective="Get the L3-edge energy for nickel for soft X-ray resonant studies.",
                expected_output=registry.context_types.XRAY_EDGE_CONTEXT,
                success_criteria="Returns Ni L3-edge energy",
                inputs=[],  # No context inputs needed
                parameters={"ELEMENT": "Ni", "EDGE_TYPE": "L3"},
            ),
            scenario_description="User: 'What is the nickel L3 edge energy?'",
            notes="L3-edge is useful for soft X-ray resonant scattering",
        )

        # Example 4: Titanium for planning scan
        example4 = OrchestratorExample(
            step=PlannedStep(
                context_key="ti_edge",
                capability="xray_edge_lookup",
                task_objective="Look up titanium K-edge to plan energy scan range.",
                expected_output=registry.context_types.XRAY_EDGE_CONTEXT,
                success_criteria="Returns Ti K-edge energy for scan planning",
                inputs=[],  # No context inputs needed
                parameters={"ELEMENT": "Ti"},
            ),
            scenario_description="User: 'I need the Ti edge energy to plan my scan'",
            notes="Common workflow: lookup edge → plan energy scan around edge",
        )

        return OrchestratorGuide(
            instructions=textwrap.dedent(
                """
                **xray_edge_lookup: Get X-ray absorption edge energies**

                ═══════════════════════════════════════════════════════════

                **PURPOSE:**
                Retrieve accurate X-ray absorption edge energies for elements.
                Essential for resonant scattering experiments where beam energy
                must be tuned near an element's absorption edge.

                ═══════════════════════════════════════════════════════════

                **REQUIRED PARAMETERS:**

                parameters: {
                    "ELEMENT": "<element_symbol>",
                    "EDGE_TYPE": "<edge>"  # optional, defaults to "K"
                }

                **OUTPUT CONTEXT:**
                This capability produces an XRAY_EDGE_CONTEXT.

                **Key Fields for Referencing:**
                - `edge_energy_eV` (Float: Energy in eV, e.g., 7112.0)
                - `edge_energy_keV` (Float: Energy in keV, e.g., 7.112)

                To use this in a scan, reference it as:
                `ref:<context_key>.edge_energy_eV`

                ═══════════════════════════════════════════════════════════

                **EXAMPLES:**

                "What is the K-edge of iron?"
                → parameters: {"ELEMENT": "Fe", "EDGE_TYPE": "K"}

                "Look up Ti edge for resonant scan"
                → parameters: {"ELEMENT": "Ti"}

                ═══════════════════════════════════════════════════════════
                """
            ),
            examples=[example1, example2, example3, example4],
            priority=10,
        )

    def _create_classifier_guide(self) -> Optional[TaskClassifierGuide]:
        """Provide guidance for the initial task classifier AI."""

        return TaskClassifierGuide(
            instructions=(
                "Use for looking up X-ray absorption edge energies of elements. "
                "IMPORTANT: Also use when the user wants to scan 'around' or 'near' an edge, "
                "even if they don't explicitly ask to look it up first. If the user mentions "
                "scanning near/around a K-edge, L-edge, or absorption edge, this capability "
                "should be used to get the accurate energy value before planning the scan."
            ),
            examples=[
                # ──────────────────────────────────────────────────────────
                # EXPLICIT EDGE LOOKUPS (Direct requests)
                # ──────────────────────────────────────────────────────────
                ClassifierExample(
                    query="What is the K-edge of iron?",
                    result=True,
                    reason="Explicit request for edge energy lookup",
                ),
                ClassifierExample(
                    query="Get copper edge energy",
                    result=True,
                    reason="Direct edge energy request",
                ),
                ClassifierExample(
                    query="I need the Fe K-edge for my scan",
                    result=True,
                    reason="User explicitly needs edge value",
                ),
                ClassifierExample(
                    query="What is the nickel L3 edge?",
                    result=True,
                    reason="L-edge energy lookup request",
                ),
                ClassifierExample(
                    query="Look up titanium absorption edge",
                    result=True,
                    reason="Explicit absorption edge inquiry",
                ),
                # ──────────────────────────────────────────────────────────
                # IMPLIED EDGE LOOKUPS (Workflow requires it)
                # ──────────────────────────────────────────────────────────
                ClassifierExample(
                    query="Scan energy around the Mn K-edge from -20 to +20 eV",
                    result=True,
                    reason=(
                        "User wants to scan 'around' the Mn K-edge - we must look up "
                        "the accurate edge energy first before planning the scan range"
                    ),
                ),
                ClassifierExample(
                    query="Do a resonant scan near the Cu K-edge",
                    result=True,
                    reason=(
                        "Resonant scattering requires scanning near an edge - "
                        "edge lookup is required to determine the center energy"
                    ),
                ),
                ClassifierExample(
                    query="Scan around the iron absorption edge with 50 eV range",
                    result=True,
                    reason=(
                        "User needs the edge energy to define the scan center, "
                        "even though they didn't explicitly ask for a lookup"
                    ),
                ),
                ClassifierExample(
                    query="Perform XANES scan across the Ti K-edge",
                    result=True,
                    reason=(
                        "XANES (X-ray Absorption Near Edge Structure) scans are "
                        "centered on an absorption edge - lookup is required"
                    ),
                ),
                ClassifierExample(
                    query="I want to do resonant scattering on a nickel sample",
                    result=True,
                    reason=(
                        "Resonant scattering implies tuning to an absorption edge - "
                        "we need to look up Ni K-edge or L-edge"
                    ),
                ),
                # ──────────────────────────────────────────────────────────
                # NOT EDGE LOOKUPS (Other operations)
                # ──────────────────────────────────────────────────────────
                ClassifierExample(
                    query="Scan energy from 7000 to 8000 eV",
                    result=False,
                    reason=(
                        "User provided absolute energy values - no edge lookup needed, "
                        "this is a direct scan execution"
                    ),
                ),
                ClassifierExample(
                    query="What is the current beam energy?",
                    result=False,
                    reason=(
                        "This is measuring current state, not looking up reference data - "
                        "use bl531_count instead"
                    ),
                ),
                ClassifierExample(
                    query="Move energy to 7500 eV",
                    result=False,
                    reason="This is a move operation with absolute value, not an edge lookup",
                ),
                ClassifierExample(
                    query="Scan angle from 0.1 to 0.2 degrees",
                    result=False,
                    reason="Angle scan, not energy scan - no edge lookup needed",
                ),
            ],
            actions_if_true=ClassifierActions(),
        )
