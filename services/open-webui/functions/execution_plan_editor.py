"""
title: Execution Plan Editor
author: ALS Assistant Team
version: 1.0.0
required_open_webui_version: 0.5.1
icon_url: data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTkgNWgxdjE0SDlWNXptMy0yaC0xdjJoMVYzem0yIDBIOXYyaDVWM3ptMi0zSDlWMkg5djE0aDJWNmgxdjEwaDJWNmgxdjEwaDJWNmgxdjEwaDJWNmgxdjEwaDJWNmgxdjEwaDJWNiIgZmlsbD0iY3VycmVudENvbG9yIi8+CjxwYXRoIGQ9Ik0xMS41IDEyLjVsMyAzIDcuNS03LjUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgZmlsbD0ibm9uZSIvPgo8L3N2Zz4K # noqa: E501 can't break url
Description: Interactive execution plan editor for ALS Assistant Agent.
    Create, modify, and validate multi-step execution plans with visual dependency
    management and real-time validation.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Set up logger
logger = logging.getLogger(__name__)

# Import the config system for consistent configuration
try:
    # Add the framework source path to enable imports
    framework_src = Path("/app/src")
    if framework_src.exists():
        sys.path.insert(0, str(framework_src))

    from osprey.utils.config import get_agent_dir

    def get_execution_plans_path() -> Path:
        """Get the execution plans directory path using config system.

        This uses the exact same configuration system as the framework,
        ensuring complete consistency with the orchestrator.

        Returns:
            Path to the execution plans directory
        """
        execution_plans_dir = get_agent_dir("execution_plans_dir")
        return Path(execution_plans_dir)

    logger.info("Using config system for path resolution")

except ImportError as e:
    logger.warning(f"Could not import config system: {e}")
    logger.warning("Falling back to direct configuration loading")

    def get_execution_plans_path() -> Path:
        """Fallback path resolution when config is not available."""
        # Use hardcoded path that matches standard framework configuration
        return Path("/app/_agent_data/execution_plans")


# Registry data loading functionality - uses real registry data instead of dummy data
def load_registry_data(agent_data_dir: Optional[str] = None) -> dict:
    """
    Load registry data from JSON files exported by the registry system.

    Args:
        agent_data_dir: Base directory for agent data (defaults to mounted path)

    Returns:
        Dictionary containing success flag, data/error info, and capabilities/context types/templates
    """
    try:
        # Use config system for consistent paths
        if agent_data_dir is None:
            try:
                # Use config to get the exact same path as the framework
                agent_data_dir = get_agent_dir("registry_exports_dir")
                # Get parent directory (agent_data_dir) since registry_exports is a subdirectory
                agent_data_dir = str(Path(agent_data_dir).parent)
            except Exception:
                # Fallback to standard path if config fails
                agent_data_dir = "/app/_agent_data"
                logger.warning(f"Using fallback path: {agent_data_dir}")

        registry_exports_dir = Path(agent_data_dir) / "registry_exports"

        # Load the complete registry export
        registry_export_file = registry_exports_dir / "registry_export.json"

        if registry_export_file.exists():
            with open(registry_export_file, "r", encoding="utf-8") as f:
                registry_data = json.load(f)

            logger.info(f"Loaded registry data from: {registry_export_file}")
            logger.info(
                f"Registry data contains: {len(registry_data.get('capabilities', []))} capabilities, "
                f"{len(registry_data.get('context_types', []))} context types, "
                f"{len(registry_data.get('templates', []))} templates"
            )

            return {
                "success": True,
                "capabilities": registry_data.get("capabilities", []),
                "context_types": registry_data.get("context_types", []),
                "templates": registry_data.get("templates", []),
            }
        else:
            error_msg = f"Registry export file not found: {registry_export_file}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "capabilities": [],
                "context_types": [],
                "templates": [],
            }

    except Exception as e:
        error_msg = f"Failed to load registry data: {e}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "capabilities": [],
            "context_types": [],
            "templates": [],
        }


class Action:
    class Valves(BaseModel):
        plans_data_path: str = Field(
            default=os.getenv("PLAN_EDITOR_DATA", "/app/data/plan_editor"),
            description="Directory for execution plan storage (must be mounted to host)",
        )
        max_plans_per_user: int = Field(
            default=100, description="Maximum number of saved plans per user"
        )

    class UserValves(BaseModel):
        show_validation_warnings: bool = Field(
            default=True, description="Show validation warnings in addition to errors"
        )
        auto_validate: bool = Field(
            default=True, description="Automatically validate plans as they are edited"
        )
        enable_templates: bool = Field(
            default=True, description="Enable template loading and saving"
        )
        enable_advanced_features: bool = Field(
            default=True, description="Enable advanced features like dependency visualization"
        )

    def __init__(self):
        self.valves = self.Valves()

    def extract_context_summary_from_messages(self, messages: list) -> Optional[Dict[str, Any]]:
        """Extract agent context summary from assistant messages."""

        try:
            logger.info(f"Extracting context from {len(messages)} messages")

            # Look through messages in reverse order (most recent first)
            for i, message in enumerate(reversed(messages)):
                try:
                    logger.debug(
                        f"Checking message {i}: role={message.get('role')}, "
                        f"has_info={message.get('info') is not None}"
                    )

                    if message.get("role") == "assistant" and message.get("info"):
                        info_keys = list(message["info"].keys())
                        logger.debug(f"Message {i} info keys: {info_keys}")

                        # Check for context summary (check both old and new key names for compatibility)
                        if "als_assistant_agent_context" in message["info"]:
                            context_data = message["info"]["als_assistant_agent_context"]
                            logger.info(
                                f"Found agent context with {context_data.get('total_context_items', 0)} items"
                            )
                            return context_data
                        elif "als_assistant_context_summary" in message["info"]:
                            context_data = message["info"]["als_assistant_context_summary"]
                            logger.info(
                                f"Found agent context with "
                                f"{len(context_data.get('context_details', {}))} categories"
                            )
                            return context_data

                except Exception as e:
                    logger.error(f"Error processing message {i}: {e}")
                    continue

            logger.info("No agent context found in any message")
            return None

        except Exception as e:
            logger.error(f"Error extracting context from messages: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    def extract_available_context_keys(
        self, context_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract available context keys from agent context summary."""
        available_contexts: List[Dict[str, Any]] = []

        try:
            # Handle both new and old data formats
            context_data = context_summary.get("context_data") or context_summary.get(
                "context_details", {}
            )

            if not context_data:
                return available_contexts

            # Process each context category
            for context_type, contexts_dict in context_data.items():
                # Process each context item in this category
                for context_key, context_info in contexts_dict.items():
                    context_type_name = context_info.get("type", "Unknown")

                    # Map context types to standard names
                    standard_type = self._map_context_type(context_type_name)

                    available_contexts.append(
                        {
                            "contextKey": context_key,
                            "contextType": standard_type,
                            "source": "agent_context",
                            "description": context_info.get("description", ""),
                            "category": context_type,
                        }
                    )

            logger.info(f"Extracted {len(available_contexts)} context keys from agent context")
            return available_contexts

        except Exception as e:
            logger.error(f"Error extracting context keys: {e}")
            return available_contexts

    def _map_context_type(self, context_type_name: str) -> str:
        """Map agent context types to standard context type names."""
        type_mapping = {
            "PV Addresses": "PV_ADDRESSES",
            "Time Range": "TIME_RANGE",
            "PV Values": "PV_VALUES",
            "Archiver Data": "ARCHIVER_DATA",
            "Analysis Results": "ANALYSIS_RESULTS",
            "Visualization Results": "VISUALIZATION_RESULTS",
            "Operation Results": "OPERATION_RESULTS",
            "Memory Context": "MEMORY_CONTEXT",
            "Conversation Results": "CONVERSATION_RESULTS",
        }

        return type_mapping.get(context_type_name, context_type_name.upper().replace(" ", "_"))

    def _get_user_id(self, user_info: Dict) -> str:
        """Get user ID from user info, using email prefix if available."""
        if not user_info:
            raise ValueError("User information not available")

        user_id = user_info.get("id")

        if user_info.get("email"):
            user_email = user_info.get("email")
            if user_email and "@" in user_email:
                user_id = user_email.split("@")[0]

        if not user_id:
            raise ValueError("User ID not available")

        return user_id

    def _get_user_plans_directory(self, user_id: str) -> Path:
        """Get the directory for user's saved plans."""
        # Sanitize user_id for filename
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
        return Path(self.valves.plans_data_path) / safe_user_id

    def _validate_plan(
        self, plan_steps: List[Dict], available_context_keys: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Enhanced validation of execution plan using registry data and agent context."""
        errors: List[str] = []
        warnings: List[str] = []

        if not plan_steps:
            return {"is_valid": False, "errors": ["Plan cannot be empty"], "warnings": []}

        # Load registry data for validation
        registry_data = load_registry_data()
        if not registry_data["success"]:
            errors.append(f"Cannot validate plan: {registry_data['error']}")
            return {"is_valid": False, "errors": errors, "warnings": warnings}

        valid_capabilities = {cap["name"] for cap in registry_data.get("capabilities", [])}
        valid_context_types = {ctx["type_name"] for ctx in registry_data.get("context_types", [])}

        # Track context keys and their types (including from agent context)
        context_key_types = {}

        # Add available context keys from agent context
        if available_context_keys:
            for ctx in available_context_keys:
                context_key_types[ctx["contextKey"]] = ctx["contextType"]

        for i, step in enumerate(plan_steps):
            step_id = f"Step {i+1} ({step.get('context_key', 'unknown')})"

            # Check required fields
            required_fields = ["context_key", "capability", "task_objective", "expected_output"]
            for field in required_fields:
                if not step.get(field):
                    errors.append(f"{step_id}: Missing required field '{field}'")

            # Check if capability exists
            capability = step.get("capability")
            if capability and capability not in valid_capabilities:
                errors.append(f"{step_id}: Unknown capability '{capability}'")

            # Check if expected output is valid
            expected_output = step.get("expected_output")
            if expected_output and expected_output not in valid_context_types:
                errors.append(f"{step_id}: Unknown context type '{expected_output}'")

            # Check if inputs reference valid context keys
            if step.get("inputs"):
                for input_item in step["inputs"]:
                    for _, context_key in input_item.items():
                        if context_key not in context_key_types:
                            errors.append(
                                f"{step_id}: Input references unknown context key '{context_key}'"
                            )

            # Track context key from this step
            context_key = step.get("context_key")
            if context_key:
                if context_key in context_key_types:
                    # Check if it's from agent context or duplicate in plan
                    if any(
                        ctx["contextKey"] == context_key for ctx in (available_context_keys or [])
                    ):
                        warnings.append(
                            f"{step_id}: Context key '{context_key}' already exists in agent context"
                        )
                    else:
                        errors.append(f"{step_id}: Duplicate context key '{context_key}'")
                else:
                    context_key_types[context_key] = expected_output

        return {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _save_plan(self, plan_steps: List[Dict], user_id: str) -> Dict[str, Any]:
        """Save execution plan to file."""
        try:
            user_plans_dir = self._get_user_plans_directory(user_id)
            user_plans_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_plan_{timestamp}.json"
            file_path = user_plans_dir / filename

            plan_data = {
                "__metadata__": {
                    "version": "1.0",
                    "user_id": user_id,
                    "created_at": datetime.now().isoformat(),
                    "serialization_type": "execution_plan",
                },
                "steps": plan_steps,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False)

            return {"success": True, "filename": filename, "path": str(file_path)}
        except Exception as e:
            logger.error(f"Error saving execution plan: {e}")
            return {"success": False, "error": str(e)}

    async def check_pending_plan(self, __event_emitter__=None, __event_call__=None) -> dict:
        """Check if there's a pending execution plan awaiting approval."""
        try:
            # Load registry data to check file paths
            registry_data = load_registry_data()
            if not registry_data["success"]:
                return {"has_pending": False, "error": "Registry data not available"}

            # Use framework configuration for consistent paths
            execution_plans_dir = get_execution_plans_path()
            pending_plans_dir = execution_plans_dir / "pending_plans"
            plan_file = pending_plans_dir / "pending_execution_plan.json"

            if plan_file.exists():
                with open(plan_file, "r", encoding="utf-8") as f:
                    plan_data = json.load(f)
                return {
                    "has_pending": True,
                    "plan_data": plan_data,
                    "message": "Found pending execution plan for review",
                }
            else:
                return {"has_pending": False}

        except Exception as e:
            logger.error(f"Error checking for pending plan: {e}")
            return {"has_pending": False, "error": str(e)}

    async def save_modified_plan(
        self, plan_data: dict, __event_emitter__=None, __event_call__=None
    ) -> dict:
        """Save modified execution plan for approval processing."""
        try:
            # Use framework configuration for consistent paths
            execution_plans_dir = get_execution_plans_path()
            pending_plans_dir = execution_plans_dir / "pending_plans"
            pending_plans_dir.mkdir(parents=True, exist_ok=True)

            modified_plan_file = pending_plans_dir / "modified_execution_plan.json"

            # Ensure plan_data has the correct format
            if "steps" not in plan_data or "__metadata__" not in plan_data:
                # If it's just a steps array, wrap it properly
                if isinstance(plan_data, list):
                    plan_data = {
                        "__metadata__": {
                            "version": "1.0",
                            "modified_at": datetime.now().isoformat(),
                            "serialization_type": "modified_execution_plan",
                        },
                        "steps": plan_data,
                    }
                else:
                    # Add metadata if missing
                    plan_data["__metadata__"] = {
                        "version": "1.0",
                        "modified_at": datetime.now().isoformat(),
                        "serialization_type": "modified_execution_plan",
                    }
            else:
                # Update existing metadata
                plan_data["__metadata__"]["modified_at"] = datetime.now().isoformat()

            with open(modified_plan_file, "w", encoding="utf-8") as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "message": f"Modified plan saved with {len(plan_data.get('steps', []))} steps",
            }

        except Exception as e:
            logger.error(f"Error saving modified plan: {e}")
            return {"success": False, "error": str(e)}

    async def create_plan_editor_interface(
        self,
        __event_emitter__=None,
        __event_call__=None,
        user_id: Optional[str] = None,
        body: Optional[dict] = None,
    ) -> Optional[Dict]:
        """Create interactive execution plan editor using JavaScript."""

        # Check for pending plan first
        pending_check = await self.check_pending_plan(__event_emitter__, __event_call__)

        # Load real registry data
        registry_data = load_registry_data()

        # Set up registry data - use empty arrays if not available
        has_registry_data = registry_data["success"]

        # Extract agent context from messages
        agent_context_summary = None
        available_context_keys = []

        if body and body.get("messages"):
            agent_context_summary = self.extract_context_summary_from_messages(
                body.get("messages", [])
            )
            if agent_context_summary:
                available_context_keys = self.extract_available_context_keys(agent_context_summary)
                logger.info(f"Found {len(available_context_keys)} context keys from agent context")

        # Prepare JSON data for the editor (empty arrays if no data)
        capabilities_json = json.dumps(registry_data.get("capabilities", [])).replace('"', '\\"')
        context_types_json = json.dumps(registry_data.get("context_types", [])).replace('"', '\\"')
        templates_json = json.dumps(registry_data.get("templates", [])).replace('"', '\\"')
        available_context_keys_json = json.dumps(available_context_keys).replace('"', '\\"')

        # Prepare pending plan data
        pending_plan_json = "null"
        editor_mode = "normal"
        if pending_check.get("has_pending"):
            pending_plan_json = json.dumps(pending_check["plan_data"]).replace('"', '\\"')
            editor_mode = "approval_review"

        try:
            # Emit status
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Loading execution plan editor...", "done": False},
                }
            )

            # Load JavaScript from external file
            js_file_path = Path(__file__).parent / "execution_plan_editor.js"

            try:
                with open(js_file_path, "r", encoding="utf-8") as f:
                    editor_js_template = f.read()
            except FileNotFoundError:
                logger.error(f"JavaScript file not found: {js_file_path}")
                return {"action": "error", "message": "Editor script not found"}

            # Prepare variables for replacement
            has_registry_str = "true" if has_registry_data else "false"
            registry_error_escaped = ""
            if not has_registry_data and registry_data.get("error"):
                registry_error_escaped = (
                    registry_data["error"].replace("'", "\\'").replace("\n", "\\n")
                )

            # Replace placeholders with actual values
            editor_js = editor_js_template.replace("${CAPABILITIES_JSON}", capabilities_json)
            editor_js = editor_js.replace("${CONTEXT_TYPES_JSON}", context_types_json)
            editor_js = editor_js.replace("${TEMPLATES_JSON}", templates_json)
            editor_js = editor_js.replace(
                "${AVAILABLE_CONTEXT_KEYS_JSON}", available_context_keys_json
            )
            editor_js = editor_js.replace("${PENDING_PLAN_JSON}", pending_plan_json)
            editor_js = editor_js.replace("${EDITOR_MODE}", editor_mode)
            editor_js = editor_js.replace("${HAS_REGISTRY_DATA}", has_registry_str)
            editor_js = editor_js.replace("${REGISTRY_ERROR}", registry_error_escaped)

            # Execute JavaScript
            result = await __event_call__(
                {
                    "type": "execute",
                    "data": {"code": editor_js},
                }
            )

            return result

        except Exception as e:
            logger.error(f"Error creating plan editor interface: {e}")
            return {"action": "error", "message": str(e)}

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> Optional[dict]:
        """Main action handler for execution plan editor."""

        try:
            # Get user info
            user_id = self._get_user_id(__user__)
            logger.info(f"Execution Plan Editor - User: {user_id}")

            user_valves = __user__.get("valves")
            if not user_valves:
                user_valves = self.UserValves()

            # Emit initial status
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Initializing execution plan editor...", "done": False},
                }
            )

            # Create editor interface
            editor_result = await self.create_plan_editor_interface(
                __event_emitter__, __event_call__, user_id, body
            )

            if editor_result and editor_result.get("action") == "save":
                # Save the execution plan
                plan_data = editor_result.get("plan", [])

                if plan_data:
                    # Extract agent context for validation
                    agent_context_summary = None
                    available_context_keys = []

                    if body and body.get("messages"):
                        agent_context_summary = self.extract_context_summary_from_messages(
                            body.get("messages", [])
                        )
                        if agent_context_summary:
                            available_context_keys = self.extract_available_context_keys(
                                agent_context_summary
                            )

                    # Validate the plan with agent context
                    validation_result = self._validate_plan(plan_data, available_context_keys)

                    if validation_result["is_valid"]:
                        # Save to file
                        save_result = self._save_plan(plan_data, user_id)

                        if save_result["success"]:
                            plan_summary = "\\n".join(
                                [
                                    f"{i+1}. {step.get('context_key', 'unknown')}: "
                                    f"{step.get('capability', 'unknown')}"
                                    for i, step in enumerate(plan_data)
                                ]
                            )

                            await __event_emitter__(
                                {
                                    "type": "message",
                                    "data": {
                                        "content": (
                                            f"# ✅ Execution Plan Saved Successfully\\n\\n"
                                            f"**Plan Details:**\\n"  # noqa: E231 string
                                            f"- Steps: {len(plan_data)}\\n"
                                            f"- Saved to: `{save_result['filename']}`\\n"
                                            f"- Validation: Passed\\n\\n"
                                            f"**Plan Summary:**\\n{plan_summary}"  # noqa: E231 string
                                        )
                                    },
                                }
                            )
                        else:
                            await __event_emitter__(
                                {
                                    "type": "message",
                                    "data": {
                                        "content": (
                                            f"# ❌ Error Saving Plan\\n\\n"
                                            f"{save_result.get('error', 'Unknown error')}"
                                        )
                                    },
                                }
                            )
                    else:
                        # Show validation errors
                        error_msg = "# ⚠️ Plan Validation Failed\\n\\n**Errors:**\\n" + "\\n".join(
                            [f"- {error}" for error in validation_result["errors"]]
                        )
                        if validation_result["warnings"]:
                            error_msg += "\\n\\n**Warnings:**\\n" + "\\n".join(
                                [f"- {warning}" for warning in validation_result["warnings"]]
                            )

                        await __event_emitter__(
                            {
                                "type": "message",
                                "data": {"content": error_msg},
                            }
                        )
                else:
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {
                                "content": "# 📝 Empty Plan\\n\\nNo steps were defined in the execution plan."
                            },
                        }
                    )

            elif editor_result and editor_result.get("action") == "save_modified":
                # Save modified execution plan for approval processing
                plan_data = editor_result.get("plan_data", {})

                if plan_data:
                    save_result = await self.save_modified_plan(
                        plan_data, __event_emitter__, __event_call__
                    )

                    if save_result["success"]:
                        await __event_emitter__(
                            {
                                "type": "message",
                                "data": {
                                    "content": (
                                        f"# ✅ Modified Plan Saved Successfully\\n\\n"
                                        f"{save_result['message']}\\n\\n"
                                        f"**Next Steps:**\\n"  # noqa: E231 string
                                        f"Return to chat and respond with **'yes'** to approve "
                                        f"the modified execution plan."
                                    )
                                },
                            }
                        )
                    else:
                        await __event_emitter__(
                            {
                                "type": "message",
                                "data": {
                                    "content": (
                                        f"# ❌ Error Saving Modified Plan\\n\\n"
                                        f"{save_result.get('error', 'Unknown error')}"
                                    )
                                },
                            }
                        )
                else:
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {
                                "content": "# ❌ Error Saving Modified Plan\\n\\nNo plan data received."
                            },
                        }
                    )

            elif editor_result and editor_result.get("action") == "save_as_is":
                # User wants to use the original plan as-is
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {
                            "content": (
                                "# ✅ Original Plan Ready for Approval\\n\\n"
                                "**Next Steps:**\\n"
                                "Return to chat and respond with **'yes'** to approve "
                                "the original execution plan."
                            )
                        },
                    }
                )

            elif editor_result and editor_result.get("action") == "editor_opened":
                # Editor was successfully opened
                mode = editor_result.get("mode", "normal")
                if mode == "approval_review":
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {
                                "content": (
                                    "# 📋 Execution Plan Review Mode\\n\\n"
                                    "**Review the pending execution plan above.**\\n\\n"
                                    "- **Use Plan As-Is**: Accept the original plan without changes\\n"
                                    "- **Save Modifications**: Edit the plan and save your changes\\n\\n"
                                    "After making your choice, return to chat and respond with "
                                    "**'yes'** to proceed with approval."
                                )
                            },
                        }
                    )
                else:
                    await __event_emitter__(
                        {
                            "type": "message",
                            "data": {
                                "content": (
                                    "# 📋 Execution Plan Editor\\n\\n"
                                    "**Create and configure your multi-step execution plan above.**\\n\\n"
                                    "- Add steps by clicking capabilities or using the **Add Step** button\\n"
                                    "- Configure inputs and outputs for each step\\n"
                                    "- Use **Save Plan** to save your configuration\\n\\n"
                                    "The editor will validate your plan and show any issues before saving."
                                )
                            },
                        }
                    )

            elif editor_result and editor_result.get("action") == "error":
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {
                            "content": (
                                f"# ❌ Editor Error\\n\\n"
                                f"{editor_result.get('message', 'Unknown error occurred')}"
                            )
                        },
                    }
                )

            else:
                # Editor was opened and closed normally - no specific message needed
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {
                            "content": (
                                "# 📋 Execution Plan Editor\\n\\n"
                                "Editor opened successfully. Use the interface above to create "
                                "or review execution plans."
                            )
                        },
                    }
                )

            # Final status
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Execution plan editor completed", "done": True},
                }
            )

        except Exception as e:
            logger.error(f"Execution Plan Editor error: {e}")
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {"content": f"# ❌ Error\\n\\nExecution plan editor failed: {str(e)}"},
                }
            )
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Execution plan editor failed", "done": True},
                }
            )
        return None
