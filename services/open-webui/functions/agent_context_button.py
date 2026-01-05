"""
title: ALS Assistant Agent Context
author: ALS Assistant Team
version: 0.1.0
required_open_webui_version: 0.5.1
icon_url: data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyUzYuNDggMjIgMTIgMjJTMjIgMTcuNTIgMjIgMTJTMTcuNTIgMiAxMiAyWk0xMiAyMEM3LjU5IDIwIDQgMTYuNDEgNCAxMlM3LjU5IDQgMTIgNFMyMCA3LjU5IDIwIDEyUzE2LjQxIDIwIDEyIDIwWiIgZmlsbD0iY3VycmVudENvbG9yIi8+CjxwYXRoIGQ9Ik0xMiA2VjhNMTIgMTZWMThNMTAgMTJIMTRNOCAxMkg2TTE4IDEySDE2IiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+ # noqa: E501 can't break url
Description: View current ALS Assistant Agent context data and available information
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Action:
    class Valves(BaseModel):
        pass

    class UserValves(BaseModel):
        show_detailed_values: bool = Field(
            default=True, description="Show detailed data values and sample data"
        )
        show_technical_info: bool = Field(
            default=False, description="Show technical information like data types and structure"
        )
        max_sample_items: int = Field(
            default=5, description="Maximum number of sample items to show for lists"
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

    def format_context_summary_markdown(self, context_summary: Dict[str, Any], user_valves) -> str:
        """Format the agent context summary as a well-structured markdown string."""
        # Handle both new and old data formats
        context_data = context_summary.get("context_data") or context_summary.get(
            "context_details", {}
        )

        if not context_summary or not context_data:
            return (
                "# 🧠 ALS Assistant Agent Context\n\n"
                "> No context data available. The agent has not yet "
                "collected or processed any data."
            )

        # Header with overview - handle both new and old formats
        total_categories = context_summary.get("context_types_count") or len(context_data)
        total_items = context_summary.get("total_context_items", 0)

        markdown = "# 🧠 ALS Assistant Agent Context\n\n"
        markdown += f"📊 **Available Context Categories:** {total_categories}\n"  # noqa: E231 string
        markdown += f"📋 **Total Context Items:** {total_items}\n\n"  # noqa: E231 string

        categories = list(context_data.keys())
        if categories:
            markdown += f"**Categories:** {', '.join(categories)}\n\n"  # noqa: E231 string

        markdown += "---\n\n"

        # Process each context category
        for context_type, contexts_dict in context_data.items():
            # Category header
            category_emoji = self._get_category_emoji(context_type)
            markdown += f"## {category_emoji} {context_type.replace('_', ' ').title()}\n\n"

            # Process each context item in this category
            for context_key, context_info in contexts_dict.items():
                context_type_name = context_info.get("type", "Unknown")
                markdown += f"### 🔹 {context_key}\n\n"
                markdown += f"**Type:** {context_type_name}\n\n"  # noqa: E231 string

                # Create summary table
                markdown = self._add_context_summary_table(markdown, context_info, user_valves)

                # Add detailed values if requested
                if user_valves.show_detailed_values:
                    markdown = self._add_detailed_values(markdown, context_info, user_valves)

                markdown += "\n---\n\n"

        # Footer
        markdown += "✨ *Agent context data available for use in subsequent queries*"

        return markdown

    def _get_category_emoji(self, context_type: str) -> str:
        """Get appropriate emoji for context category."""
        emoji_map = {
            "PV_ADDRESSES": "📍",
            "TIME_RANGE": "⏰",
            "PV_VALUES": "📊",
            "ARCHIVER_DATA": "📈",
            "ANALYSIS_RESULTS": "🔬",
            "VISUALIZATION_RESULTS": "📊",
            "OPERATION_RESULTS": "⚙️",
            "MEMORY_CONTEXT": "🧠",
            "CONVERSATION_RESULTS": "💬",
        }
        return emoji_map.get(context_type, "📁")

    def _add_context_summary_table(
        self, markdown: str, context_info: Dict[str, Any], user_valves
    ) -> str:
        """Add a summary table for the context item."""
        # Common fields
        summary_table = "| Field | Value |\n|-------|-------|\n"

        # Type-specific summary information
        context_type = context_info.get("type", "Unknown")

        if context_type == "PV Addresses":
            total_pvs = context_info.get("total_pvs", 0)
            summary_table += f"| **Total PVs** | {total_pvs} |\n"
            description = context_info.get("description", "N/A")
            summary_table += f"| **Description** | {description} |\n"

        elif context_type == "Time Range":
            start_time = context_info.get("start_time", "N/A")
            end_time = context_info.get("end_time", "N/A")
            duration = context_info.get("duration", "N/A")
            summary_table += f"| **Start Time** | {start_time} |\n"
            summary_table += f"| **End Time** | {end_time} |\n"
            summary_table += f"| **Duration** | {duration} |\n"

        elif context_type == "PV Values":
            pv_data = context_info.get("pv_data", {})
            summary_table += f"| **PV Count** | {len(pv_data)} |\n"

        elif context_type == "Archiver Data":
            total_points = context_info.get("total_points", 0)
            pv_count = context_info.get("pv_count", 0)
            time_info = context_info.get("time_info", "N/A")
            summary_table += f"| **Total Points** | {total_points:,} |\n"  # noqa: E231 string
            summary_table += f"| **PV Count** | {pv_count} |\n"
            summary_table += f"| **Time Info** | {time_info} |\n"

        elif context_type in ["Analysis Results", "Visualization Results", "Operation Results"]:
            field_count = context_info.get("field_count", 0)
            summary_table += f"| **Field Count** | {field_count} |\n"
            available_fields = context_info.get("available_fields", [])
            if available_fields:
                fields_str = ", ".join(available_fields[:5])
                if len(available_fields) > 5:
                    fields_str += f" (and {len(available_fields) - 5} more)"
                summary_table += f"| **Available Fields** | {fields_str} |\n"

        elif context_type == "Memory Context":
            memory_count = context_info.get("memory_count", 0)
            oldest_memory = context_info.get("oldest_memory", "N/A")
            newest_memory = context_info.get("newest_memory", "N/A")
            summary_table += f"| **Memory Count** | {memory_count} |\n"
            summary_table += f"| **Oldest Memory** | {oldest_memory} |\n"
            summary_table += f"| **Newest Memory** | {newest_memory} |\n"

        elif context_type == "Conversation Results":
            message_type = context_info.get("message_type", "N/A")
            summary_table += f"| **Message Type** | {message_type} |\n"

        return markdown + summary_table + "\n"

    def _add_detailed_values(self, markdown: str, context_info: Dict[str, Any], user_valves) -> str:
        """Add detailed values section."""
        context_type = context_info.get("type", "Unknown")

        if context_type == "PV Addresses":
            pv_list = context_info.get("pv_list", [])
            if pv_list:
                markdown += "**PV Addresses:**\n"
                for _, pv in enumerate(pv_list[: user_valves.max_sample_items]):
                    markdown += f"- `{pv}`\n"
                if len(pv_list) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(pv_list) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "PV Values":
            pv_data = context_info.get("pv_data", {})
            if pv_data:
                markdown += "**PV Values:**\n"
                count = 0
                for pv_name, pv_info in pv_data.items():
                    if count >= user_valves.max_sample_items:
                        break
                    value = pv_info.get("value", "N/A")
                    units = pv_info.get("units", "")
                    timestamp = pv_info.get("timestamp", "N/A")
                    markdown += f"- `{pv_name}`: {value} {units} *(@ {timestamp})*\n"
                    count += 1
                if len(pv_data) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(pv_data) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "Archiver Data":
            pv_names = context_info.get("pv_names", [])
            sample_values = context_info.get("sample_values", {})

            if pv_names:
                markdown += "**Available PVs:**\n"
                for pv in pv_names[: user_valves.max_sample_items]:
                    markdown += f"- `{pv}`"
                    if pv in sample_values:
                        values = sample_values[pv][:3]  # Show first 3 sample values
                        values_str = ", ".join(
                            [
                                f"{v:.3f}"  # noqa: E231 string
                                if isinstance(v, (int, float))
                                else str(v)
                                for v in values
                            ]
                        )
                        markdown += f" (sample: {values_str}...)"
                    markdown += "\n"
                if len(pv_names) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(pv_names) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type in ["Analysis Results", "Visualization Results", "Operation Results"]:
            results = context_info.get("results", {})
            if results:
                markdown += "**Results:**\n"
                count = 0
                for key, value in results.items():
                    if count >= user_valves.max_sample_items:
                        break
                    if isinstance(value, (list, dict)) and len(str(value)) > 100:
                        markdown += (
                            f"- **{key.replace('_', ' ').title()}**: *(large data structure)*\n"
                        )
                    else:
                        markdown += f"- **{key.replace('_', ' ').title()}**: {value}\n"
                    count += 1
                if len(results) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(results) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "Memory Context":
            memories = context_info.get("memories", [])
            if memories:
                markdown += "**Memory Entries:**\n"
                for _, memory in enumerate(memories[: user_valves.max_sample_items]):
                    content = memory.get("content", "N/A")
                    timestamp = memory.get("timestamp", "N/A")
                    markdown += f"- {content} *(@ {timestamp})*\n"
                if len(memories) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(memories) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "Conversation Results":
            full_response = context_info.get("full_response", "N/A")
            if full_response and len(full_response) > 200:
                markdown += (
                    f"**Response Preview:** {full_response[:200]}...\n\n"  # noqa: E231 string
                )
            elif full_response:
                markdown += f"**Full Response:** {full_response}\n\n"  # noqa: E231 string

        return markdown

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> Optional[dict]:
        """Display formatted agent context using a popup modal."""
        logger.info(
            f"User - Name: {__user__['name']}, ID: {__user__['id']} - "
            "Requesting ALS Assistant agent context"
        )

        user_valves = __user__.get("valves")
        if not user_valves:
            user_valves = self.UserValves()

        await __event_emitter__(
            {
                "type": "status",
                "data": {"description": "Retrieving agent context...", "done": False},
            }
        )

        try:
            # Log debug information about the request
            logger.info(
                f"Processing agent context request for user " f"{__user__.get('name', 'unknown')}"
            )
            logger.info(f"Message count: {len(body.get('messages', []))}")

            # Extract context summary from the last assistant message
            context_summary = self.extract_context_summary_from_messages(body.get("messages", []))

            if not context_summary:
                logger.info("No agent context found in messages")

                # Load no context JavaScript
                js_file_path = Path(__file__).parent / "agent_context_no_context.js"

                try:
                    with open(js_file_path, "r", encoding="utf-8") as f:
                        no_context_js = f.read()
                except FileNotFoundError:
                    logger.error(f"JavaScript file not found: {js_file_path}")
                    no_context_js = "alert('Error: JavaScript file not found');"

                await __event_call__(
                    {
                        "type": "execute",
                        "data": {"code": no_context_js},
                    }
                )

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "No agent context available",
                            "done": True,
                        },
                    }
                )
                return None

            logger.info(f"Found agent context: {list(context_summary.keys())}")

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Formatting agent context...",
                        "done": False,
                    },
                }
            )

            # Format the context summary as HTML for the popup
            formatted_context = self.format_context_summary_html(context_summary, user_valves)

            # Load context display JavaScript
            js_file_path = Path(__file__).parent / "agent_context_display.js"

            try:
                with open(js_file_path, "r", encoding="utf-8") as f:
                    context_js_template = f.read()
            except FileNotFoundError:
                logger.error(f"JavaScript file not found: {js_file_path}")
                context_js_template = "alert('Error: JavaScript file not found');"

            # Replace placeholder with formatted context
            context_js = context_js_template.replace("${FORMATTED_CONTEXT}", formatted_context)

            await __event_call__(
                {
                    "type": "execute",
                    "data": {"code": context_js},
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Agent context displayed", "done": True},
                }
            )

            context_categories = len(
                context_summary.get("context_data", {})
                or context_summary.get("context_details", {})
            )
            logger.info(
                f"User - Name: {__user__['name']}, ID: {__user__['id']} - "
                f"Agent context popup displayed successfully "
                f"({context_categories} categories)"
            )

        except Exception as e:
            logger.error(f"Error processing agent context: {e}")

            # Load error JavaScript
            js_file_path = Path(__file__).parent / "agent_context_error.js"

            try:
                with open(js_file_path, "r", encoding="utf-8") as f:
                    error_js_template = f.read()
            except FileNotFoundError:
                logger.error(f"JavaScript file not found: {js_file_path}")
                error_js_template = "alert('Error: JavaScript file not found');"

            # Replace placeholder with error message
            error_message_escaped = str(e).replace("'", "\\'").replace("\n", "\\n")
            error_js = error_js_template.replace("${ERROR_MESSAGE}", error_message_escaped)

            await __event_call__(
                {
                    "type": "execute",
                    "data": {"code": error_js},
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Error processing agent context",
                        "done": True,
                    },
                }
            )

        return None

    def format_context_summary_html(self, context_summary: Dict[str, Any], user_valves) -> str:
        """Format the agent context summary as HTML for the popup display."""
        # Handle both new and old data formats
        context_data = context_summary.get("context_data") or context_summary.get(
            "context_details", {}
        )

        if not context_summary or not context_data:
            no_data_style = (
                "text-align: center; " "padding: 40px; " "color: #6b7280; " "font-style: italic"
            )
            return f'<div style="{no_data_style}">No context data available.</div>'

        # Header with overview - handle both new and old formats
        total_categories = context_summary.get("context_types_count") or len(context_data)
        total_items = context_summary.get("total_context_items", 0)

        # Build HTML using list
        html_parts = []

        # Define reusable styles
        overview_container_style = (
            "margin-bottom: 24px; "
            "padding: 20px; "
            "background: #f8fafc; "
            "border-radius: 8px; "
            "border: 1px solid #e2e8f0"
        )

        overview_header_style = (
            "display: flex; "
            "justify-content: space-between; "
            "align-items: center; "
            "margin-bottom: 12px"
        )

        overview_title_style = "font-size: 18px; " "font-weight: 600; " "color: #1f2937"

        overview_subtitle_style = "font-size: 14px; color: #6b7280"

        grid_style = (
            "display: grid; " "grid-template-columns: 1fr 1fr; " "gap: 16px; " "margin-bottom: 12px"
        )

        stat_box_style = (
            "text-align: center; "
            "padding: 12px; "
            "background: white; "
            "border-radius: 6px; "
            "border: 1px solid #e2e8f0"
        )

        stat_number_green_style = "font-size: 24px; " "font-weight: 700; " "color: #059669"

        stat_number_blue_style = "font-size: 24px; " "font-weight: 700; " "color: #0369a1"

        stat_label_style = "font-size: 13px; " "color: #6b7280; " "font-weight: 500"

        categories_text_style = "font-size: 14px; color: #4b5563"

        # Build overview section
        html_parts.append(
            f'<div style="{overview_container_style}">'
            f'<div style="{overview_header_style}">'
            f'<div style="{overview_title_style}">📊 Context Overview</div>'
            f'<div style="{overview_subtitle_style}">'
            f"Available for use in subsequent queries</div></div>"
            f'<div style="{grid_style}">'
            f'<div style="{stat_box_style}">'
            f'<div style="{stat_number_green_style}">{total_categories}</div>'
            f'<div style="{stat_label_style}">Categories</div></div>'
            f'<div style="{stat_box_style}">'
            f'<div style="{stat_number_blue_style}">{total_items}</div>'
            f'<div style="{stat_label_style}">Total Items</div></div></div>'
        )

        categories = list(context_data.keys())
        if categories:
            categories_list = ", ".join(categories)
            html_parts.append(
                f'<div style="{categories_text_style}">'
                f"<strong>Categories:</strong> {categories_list}</div>"  # noqa: E231 string
            )

        html_parts.append("</div>")

        # Define category container styles
        category_container_style = (
            "margin-bottom: 28px; "
            "border: 1px solid #e2e8f0; "
            "border-radius: 8px; "
            "overflow: hidden"
        )

        category_header_style = (
            "background: #f1f5f9; " "padding: 16px; " "border-bottom: 1px solid #e2e8f0"
        )

        category_title_style = (
            "margin: 0; " "color: #1f2937; " "font-size: 16px; " "font-weight: 600"
        )

        category_body_style = "padding: 20px"

        # Process each context category
        for context_type, contexts_dict in context_data.items():
            # Category header
            category_emoji = self._get_category_emoji(context_type)
            category_name = context_type.replace("_", " ").title()

            html_parts.append(
                f'<div style="{category_container_style}">'
                f'<div style="{category_header_style}">'
                f'<h3 style="{category_title_style}">'
                f"{category_emoji} {category_name}</h3></div>"
                f'<div style="{category_body_style}">'
            )

            # Define context item styles
            item_container_style = (
                "margin-bottom: 24px; "
                "padding: 16px; "
                "background: #fafbfc; "
                "border-radius: 6px; "
                "border: 1px solid #e2e8f0"
            )

            item_title_style = (
                "margin: 0 0 12px 0; " "color: #1f2937; " "font-size: 15px; " "font-weight: 600"
            )

            item_type_style = "margin-bottom: 12px; " "font-size: 13px; " "color: #6b7280"

            # Process each context item in this category
            for context_key, context_info in contexts_dict.items():
                context_type_name = context_info.get("type", "Unknown")

                html_parts.append(
                    f'<div style="{item_container_style}">'
                    f'<h4 style="{item_title_style}">🔹 {context_key}</h4>'
                    f'<div style="{item_type_style}">'
                    f"<strong>Type:</strong> {context_type_name}</div>"  # noqa: E231 string
                )

                # Create summary table
                html_parts.append(self._add_context_summary_table_html(context_info, user_valves))

                # Add detailed values if requested
                if user_valves.show_detailed_values:
                    html_parts.append(self._add_detailed_values_html(context_info, user_valves))

                html_parts.append("</div>")

            html_parts.append("</div></div>")

        return "".join(html_parts)

    def _add_context_summary_table_html(self, context_info: Dict[str, Any], user_valves) -> str:
        """Add a summary table for the context item in HTML format."""
        # Define table styles
        table_container_style = "overflow-x: auto; margin-bottom: 16px"
        table_style = "width: 100%; border-collapse: collapse; font-size: 13px"
        header_row_style = "background: #e2e8f0"
        th_style = (
            "padding: 8px 12px; "
            "text-align: left; "
            "border: 1px solid #cbd5e1; "
            "font-weight: 600; "
            "color: #374151"
        )
        td_field_style = (
            "padding: 8px 12px; "
            "border: 1px solid #cbd5e1; "
            "font-weight: 500; "
            "color: #374151"
        )
        td_value_style = "padding: 8px 12px; " "border: 1px solid #cbd5e1; " "color: #1f2937"

        # Start table
        summary_parts = [
            f'<div style="{table_container_style}">'
            f'<table style="{table_style}"><thead>'
            f'<tr style="{header_row_style}">'
            f'<th style="{th_style}">Field</th>'
            f'<th style="{th_style}">Value</th>'
            f"</tr></thead><tbody>"
        ]

        # Type-specific summary information
        context_type = context_info.get("type", "Unknown")

        if context_type == "PV Addresses":
            total_pvs = context_info.get("total_pvs", 0)
            description = context_info.get("description", "N/A")
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Total PVs</td>'
                    f'<td style="{td_value_style}">{total_pvs}</td></tr>',
                    f'<tr><td style="{td_field_style}">Description</td>'
                    f'<td style="{td_value_style}">{description}</td></tr>',
                ]
            )

        elif context_type == "Time Range":
            start_time = context_info.get("start_time", "N/A")
            end_time = context_info.get("end_time", "N/A")
            duration = context_info.get("duration", "N/A")
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Start Time</td>'
                    f'<td style="{td_value_style}">{start_time}</td></tr>',
                    f'<tr><td style="{td_field_style}">End Time</td>'
                    f'<td style="{td_value_style}">{end_time}</td></tr>',
                    f'<tr><td style="{td_field_style}">Duration</td>'
                    f'<td style="{td_value_style}">{duration}</td></tr>',
                ]
            )

        elif context_type == "PV Values":
            pv_data = context_info.get("pv_data", {})
            summary_parts.append(
                f'<tr><td style="{td_field_style}">PV Count</td>'
                f'<td style="{td_value_style}">{len(pv_data)}</td></tr>'
            )

        elif context_type == "Archiver Data":
            total_points = context_info.get("total_points", 0)
            pv_count = context_info.get("pv_count", 0)
            time_info = context_info.get("time_info", "N/A")
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Total Points</td>'
                    f'<td style="{td_value_style}">{total_points:,}</td></tr>',  # noqa: E231 string
                    f'<tr><td style="{td_field_style}">PV Count</td>'
                    f'<td style="{td_value_style}">{pv_count}</td></tr>',
                    f'<tr><td style="{td_field_style}">Time Info</td>'
                    f'<td style="{td_value_style}">{time_info}</td></tr>',
                ]
            )

        elif context_type in [
            "Analysis Results",
            "Visualization Results",
            "Operation Results",
        ]:
            field_count = context_info.get("field_count", 0)
            summary_parts.append(
                f'<tr><td style="{td_field_style}">Field Count</td>'
                f'<td style="{td_value_style}">{field_count}</td></tr>'
            )

            available_fields = context_info.get("available_fields", [])
            if available_fields:
                fields_str = ", ".join(available_fields[:5])
                if len(available_fields) > 5:
                    fields_str += f" (and {len(available_fields) - 5} more)"
                summary_parts.append(
                    f'<tr><td style="{td_field_style}">Available Fields</td>'
                    f'<td style="{td_value_style}">{fields_str}</td></tr>'
                )

        elif context_type == "Memory Context":
            memory_count = context_info.get("memory_count", 0)
            oldest_memory = context_info.get("oldest_memory", "N/A")
            newest_memory = context_info.get("newest_memory", "N/A")
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Memory Count</td>'
                    f'<td style="{td_value_style}">{memory_count}</td></tr>',
                    f'<tr><td style="{td_field_style}">Oldest Memory</td>'
                    f'<td style="{td_value_style}">{oldest_memory}</td></tr>',
                    f'<tr><td style="{td_field_style}">Newest Memory</td>'
                    f'<td style="{td_value_style}">{newest_memory}</td></tr>',
                ]
            )

        elif context_type == "Conversation Results":
            message_type = context_info.get("message_type", "N/A")
            summary_parts.append(
                f'<tr><td style="{td_field_style}">Message Type</td>'
                f'<td style="{td_value_style}">{message_type}</td></tr>'
            )

        summary_parts.append("</tbody></table></div>")
        return "".join(summary_parts)

    def _add_detailed_values_html(self, context_info: Dict[str, Any], user_valves) -> str:
        """Add detailed values section in HTML format."""
        context_type = context_info.get("type", "Unknown")
        html_parts = []

        # Define common styles
        section_container_style = "margin-top: 16px"
        section_title_style = (
            "margin: 0 0 8px 0; " "font-size: 14px; " "font-weight: 600; " "color: #374151"
        )
        section_content_style = (
            "background: #f8fafc; "
            "padding: 12px; "
            "border-radius: 4px; "
            "border: 1px solid #e2e8f0; "
            "font-family: monospace; "
            "font-size: 12px; "
            "max-height: 200px; "
            "overflow-y: auto"
        )
        item_style = "margin-bottom: 4px; color: #1f2937"
        more_items_style = "color: #6b7280; " "font-style: italic"

        if context_type == "PV Addresses":
            pv_list = context_info.get("pv_list", [])
            if pv_list:
                html_parts.append(
                    f'<div style="{section_container_style}">'
                    f'<h5 style="{section_title_style}">PV Addresses:</h5>'  # noqa: E231 string
                    f'<div style="{section_content_style}">'
                )

                for pv in pv_list[: user_valves.max_sample_items]:
                    html_parts.append(f'<div style="{item_style}">• {pv}</div>')

                if len(pv_list) > user_valves.max_sample_items:
                    remaining = len(pv_list) - user_valves.max_sample_items
                    html_parts.append(
                        f'<div style="{more_items_style}">• (and {remaining} more)</div>'
                    )

                html_parts.append("</div></div>")

        elif context_type == "PV Values":
            pv_data = context_info.get("pv_data", {})
            if pv_data:
                pv_value_content_style = (
                    "background: #f8fafc; "
                    "padding: 12px; "
                    "border-radius: 4px; "
                    "border: 1px solid #e2e8f0; "
                    "font-size: 12px; "
                    "max-height: 200px; "
                    "overflow-y: auto"
                )
                pv_value_item_style = (
                    "margin-bottom: 8px; "
                    "padding: 8px; "
                    "background: white; "
                    "border-radius: 3px; "
                    "border: 1px solid #e2e8f0"
                )
                pv_name_style = "color: #1f2937; font-family: monospace"
                pv_value_style = "color: #059669; font-weight: 600"
                pv_timestamp_style = "color: #6b7280; font-size: 11px"
                center_text_style = (
                    "color: #6b7280; "
                    "font-style: italic; "
                    "text-align: center; "
                    "margin-top: 8px"
                )

                html_parts.append(
                    f'<div style="{section_container_style}">'
                    f'<h5 style="{section_title_style}">PV Values:</h5>'  # noqa: E231 string
                    f'<div style="{pv_value_content_style}">'
                )

                count = 0
                for pv_name, pv_info in pv_data.items():
                    if count >= user_valves.max_sample_items:
                        break
                    value = pv_info.get("value", "N/A")
                    units = pv_info.get("units", "")
                    timestamp = pv_info.get("timestamp", "N/A")

                    html_parts.append(
                        f'<div style="{pv_value_item_style}">'
                        f'<strong style="{pv_name_style}">{pv_name}:</strong> '  # noqa: E231 string
                        f'<span style="{pv_value_style}">{value} {units}</span> '
                        f'<span style="{pv_timestamp_style}">@ {timestamp}</span>'
                        f"</div>"
                    )
                    count += 1

                if len(pv_data) > user_valves.max_sample_items:
                    remaining = len(pv_data) - user_valves.max_sample_items
                    html_parts.append(
                        f'<div style="{center_text_style}">• (and {remaining} more)</div>'
                    )

                html_parts.append("</div></div>")

        elif context_type == "Archiver Data":
            pv_names = context_info.get("pv_names", [])
            sample_values = context_info.get("sample_values", {})

            if pv_names:
                sample_style = "color: #6b7280; font-size: 11px"
                center_text_style = (
                    "color: #6b7280; "
                    "font-style: italic; "
                    "text-align: center; "
                    "margin-top: 8px"
                )

                html_parts.append(
                    f'<div style="{section_container_style}">'
                    f'<h5 style="{section_title_style}">Available PVs:</h5>'  # noqa: E231 string
                    f'<div style="{section_content_style}">'
                )

                for pv in pv_names[: user_valves.max_sample_items]:
                    html_parts.append(f'<div style="{item_style}">• {pv}')

                    if pv in sample_values:
                        values = sample_values[pv][:3]
                        values_str = ", ".join(
                            [
                                f"{v:.3f}"  # noqa: E231 string
                                if isinstance(v, (int, float))
                                else str(v)
                                for v in values
                            ]
                        )
                        html_parts.append(
                            f' <span style="{sample_style}">(sample: {values_str}...)</span>'
                        )

                    html_parts.append("</div>")

                if len(pv_names) > user_valves.max_sample_items:
                    remaining = len(pv_names) - user_valves.max_sample_items
                    html_parts.append(
                        f'<div style="{center_text_style}">• (and {remaining} more)</div>'
                    )

                html_parts.append("</div></div>")

        elif context_type in [
            "Analysis Results",
            "Visualization Results",
            "Operation Results",
        ]:
            results = context_info.get("results", {})
            if results:
                results_content_style = (
                    "background: #f8fafc; "
                    "padding: 12px; "
                    "border-radius: 4px; "
                    "border: 1px solid #e2e8f0; "
                    "font-size: 12px; "
                    "max-height: 200px; "
                    "overflow-y: auto"
                )
                result_item_style = (
                    "margin-bottom: 8px; "
                    "padding: 8px; "
                    "background: white; "
                    "border-radius: 3px; "
                    "border: 1px solid #e2e8f0"
                )
                result_key_style = "color: #1f2937"
                result_large_style = "color: #6b7280; font-style: italic"
                result_value_style = "color: #059669"
                center_text_style = (
                    "color: #6b7280; "
                    "font-style: italic; "
                    "text-align: center; "
                    "margin-top: 8px"
                )

                html_parts.append(
                    f'<div style="{section_container_style}">'
                    f'<h5 style="{section_title_style}">Results:</h5>'  # noqa: E231 string
                    f'<div style="{results_content_style}">'
                )

                count = 0
                for key, value in results.items():
                    if count >= user_valves.max_sample_items:
                        break
                    display_key = key.replace("_", " ").title()

                    html_parts.append(f'<div style="{result_item_style}">')

                    if isinstance(value, (list, dict)) and len(str(value)) > 100:
                        html_parts.append(
                            f'<strong style="{result_key_style}">{display_key}:</strong> '  # noqa: E231 string
                            f'<span style="{result_large_style}">(large data structure)</span>'
                        )
                    else:
                        html_parts.append(
                            f'<strong style="{result_key_style}">{display_key}:</strong> '  # noqa: E231 string
                            f'<span style="{result_value_style}">{value}</span>'
                        )

                    html_parts.append("</div>")
                    count += 1

                if len(results) > user_valves.max_sample_items:
                    remaining = len(results) - user_valves.max_sample_items
                    html_parts.append(
                        f'<div style="{center_text_style}">• (and {remaining} more)</div>'
                    )

                html_parts.append("</div></div>")

        elif context_type == "Memory Context":
            memories = context_info.get("memories", [])
            if memories:
                memory_content_style = (
                    "background: #f8fafc; "
                    "padding: 12px; "
                    "border-radius: 4px; "
                    "border: 1px solid #e2e8f0; "
                    "font-size: 12px; "
                    "max-height: 200px; "
                    "overflow-y: auto"
                )
                memory_item_style = (
                    "margin-bottom: 8px; "
                    "padding: 8px; "
                    "background: white; "
                    "border-radius: 3px; "
                    "border: 1px solid #e2e8f0"
                )
                memory_content_style_inner = "color: #1f2937; margin-bottom: 4px"
                memory_timestamp_style = "color: #6b7280; font-size: 11px"
                center_text_style = (
                    "color: #6b7280; "
                    "font-style: italic; "
                    "text-align: center; "
                    "margin-top: 8px"
                )

                html_parts.append(
                    f'<div style="{section_container_style}">'
                    f'<h5 style="{section_title_style}">Memory Entries:</h5>'  # noqa: E231 string
                    f'<div style="{memory_content_style}">'
                )

                for memory in memories[: user_valves.max_sample_items]:
                    content = memory.get("content", "N/A")
                    timestamp = memory.get("timestamp", "N/A")

                    html_parts.append(
                        f'<div style="{memory_item_style}">'
                        f'<div style="{memory_content_style_inner}">{content}</div>'
                        f'<div style="{memory_timestamp_style}">@ {timestamp}</div>'
                        f"</div>"
                    )

                if len(memories) > user_valves.max_sample_items:
                    remaining = len(memories) - user_valves.max_sample_items
                    html_parts.append(
                        f'<div style="{center_text_style}">• (and {remaining} more)</div>'
                    )

                html_parts.append("</div></div>")

        elif context_type == "Conversation Results":
            full_response = context_info.get("full_response", "N/A")
            if full_response:
                response_content_style = (
                    "background: #f8fafc; "
                    "padding: 12px; "
                    "border-radius: 4px; "
                    "border: 1px solid #e2e8f0; "
                    "font-size: 12px; "
                    "max-height: 200px; "
                    "overflow-y: auto"
                )
                response_text_style = "color: #1f2937; line-height: 1.4"

                html_parts.append(
                    f'<div style="{section_container_style}">'
                    f'<h5 style="{section_title_style}">Response:</h5>'  # noqa: E231 string
                    f'<div style="{response_content_style}">'
                )

                if len(full_response) > 200:
                    html_parts.append(
                        f'<div style="{response_text_style}">'
                        f"<strong>Preview:</strong> {full_response[:200]}..."  # noqa: E231 string
                        f"</div>"
                    )
                else:
                    html_parts.append(
                        f'<div style="{response_text_style}">'
                        f"<strong>Full Response:</strong> {full_response}"  # noqa: E231 string
                        f"</div>"
                    )

                html_parts.append("</div></div>")

        return "".join(html_parts)


# Action registration - required for OpenWebUI to recognize this as an action button
actions = [
    {
        "id": "als_assistant_agent_context",
        "name": "Agent Context",
        "description": "View current ALS Assistant agent context data and available information",
        "icon_url": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyUzYuNDggMjIgMTIgMjJTMjIgMTcuNTIgMjIgMTJTMTcuNTIgMiAxMiAyWk0xMiAyMEM3LjU5IDIwIDQgMTYuNDEgNCAxMlM3LjU5IDQgMTIgNFMyMCA3LjU5IDIwIDEyUzE2LjQxIDIwIDEyIDIwWiIgZmlsbD0iY3VycmVudENvbG9yIi8+CjxwYXRoIGQ9Ik0xMiA2VjhNMTIgMTZWMThNMTAgMTJIMTRNOCAxMkg2TTE4IDEySDE2IiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+",  # noqa: E501 can't break url
    }
]
