"""
title: ALS Assistant Agent Context
author: ALS Assistant Team
version: 0.1.0
required_open_webui_version: 0.5.1
icon_url: data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyUzYuNDggMjIgMTIgMjJTMjIgMTcuNTIgMjIgMTJTMTcuNTIgMiAxMiAyWk0xMiAyMEM3LjU5IDIwIDQgMTYuNDEgNCAxMlM3LjU5IDQgMTIgNFMyMCA3LjU5IDIwIDEyUzE2LjQxIDIwIDEyIDIwWiIgZmlsbD0iY3VycmVudENvbG9yIi8+CjxwYXRoIGQ9Ik0xMiA2VjhNMTIgMTZWMThNMTAgMTJIMTRNOCAxMkg2TTE4IDEySDE2IiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+ # noqa: E501 can't break url
Description: View current ALS Assistant Agent context data and available information
"""

import json
import logging
from html import escape
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

    @staticmethod
    def _h(value: Any) -> str:
        """HTML-escape dynamic values before interpolation into HTML."""
        return escape("" if value is None else str(value), quote=True)

    @staticmethod
    def _safe_num(value: Any, default: int = 0) -> int:
        """Best-effort numeric conversion for display."""
        try:
            if isinstance(value, bool):
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_list(value: Any) -> list:
        """Ensure value is a list for iteration."""
        return value if isinstance(value, list) else []

    @staticmethod
    def _safe_dict(value: Any) -> dict:
        """Ensure value is a dict for iteration."""
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _safe_str(value: Any, default: str = "N/A") -> str:
        """Return string-like value or default."""
        if value is None:
            return default
        return str(value)

    def extract_context_summary_from_messages(self, messages: list) -> Optional[Dict[str, Any]]:
        """Extract agent context summary from assistant messages."""
        try:
            logger.info(f"Extracting context from {len(messages)} messages")

            for i, message in enumerate(reversed(messages)):
                try:
                    logger.debug(
                        f"Checking message {i}: role={message.get('role')}, "
                        f"has_info={message.get('info') is not None}"
                    )

                    if message.get("role") == "assistant" and message.get("info"):
                        info_keys = list(message["info"].keys())
                        logger.debug(f"Message {i} info keys: {info_keys}")

                        if "als_assistant_agent_context" in message["info"]:
                            context_data = message["info"]["als_assistant_agent_context"]
                            logger.info(
                                "Found agent context with "
                                f"{context_data.get('total_context_items', 0)} items"
                            )
                            return context_data
                        if "als_assistant_context_summary" in message["info"]:
                            context_data = message["info"]["als_assistant_context_summary"]
                            logger.info(
                                "Found agent context with "
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
        """Format the agent context summary as markdown."""
        context_data = context_summary.get("context_data") or context_summary.get("context_details", {})

        if not context_summary or not context_data:
            return (
                "# 🧠 ALS Assistant Agent Context\n\n"
                "> No context data available. The agent has not yet "
                "collected or processed any data."
            )

        total_categories = context_summary.get("context_types_count") or len(context_data)
        total_items = context_summary.get("total_context_items", 0)

        markdown = "# 🧠 ALS Assistant Agent Context\n\n"
        markdown += f"📊 **Available Context Categories:** {total_categories}\n"
        markdown += f"📋 **Total Context Items:** {total_items}\n\n"

        categories = list(context_data.keys())
        if categories:
            markdown += f"**Categories:** {', '.join(categories)}\n\n"

        markdown += "---\n\n"

        for context_type, contexts_dict in context_data.items():
            category_emoji = self._get_category_emoji(context_type)
            markdown += f"## {category_emoji} {context_type.replace('_', ' ').title()}\n\n"

            for context_key, context_info in self._safe_dict(contexts_dict).items():
                context_type_name = self._safe_dict(context_info).get("type", "Unknown")
                markdown += f"### 🔹 {context_key}\n\n"
                markdown += f"**Type:** {context_type_name}\n\n"

                markdown = self._add_context_summary_table(markdown, context_info, user_valves)

                if user_valves.show_detailed_values:
                    markdown = self._add_detailed_values(markdown, context_info, user_valves)

                markdown += "\n---\n\n"

        markdown += "✨ *Agent context data available for use in subsequent queries*"
        return markdown

    def _get_category_emoji(self, context_type: str) -> str:
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

    def _add_context_summary_table(self, markdown: str, context_info: Dict[str, Any], user_valves) -> str:
        summary_table = "| Field | Value |\n|-------|-------|\n"
        context_info = self._safe_dict(context_info)
        context_type = context_info.get("type", "Unknown")

        if context_type == "PV Addresses":
            summary_table += f"| **Total PVs** | {context_info.get('total_pvs', 0)} |\n"
            summary_table += f"| **Description** | {context_info.get('description', 'N/A')} |\n"

        elif context_type == "Time Range":
            summary_table += f"| **Start Time** | {context_info.get('start_time', 'N/A')} |\n"
            summary_table += f"| **End Time** | {context_info.get('end_time', 'N/A')} |\n"
            summary_table += f"| **Duration** | {context_info.get('duration', 'N/A')} |\n"

        elif context_type == "PV Values":
            pv_data = self._safe_dict(context_info.get("pv_data", {}))
            summary_table += f"| **PV Count** | {len(pv_data)} |\n"

        elif context_type == "Archiver Data":
            summary_table += f"| **Total Points** | {self._safe_num(context_info.get('total_points', 0)):,} |\n"
            summary_table += f"| **PV Count** | {context_info.get('pv_count', 0)} |\n"
            summary_table += f"| **Time Info** | {context_info.get('time_info', 'N/A')} |\n"

        elif context_type in ["Analysis Results", "Visualization Results", "Operation Results"]:
            summary_table += f"| **Field Count** | {context_info.get('field_count', 0)} |\n"
            available_fields = self._safe_list(context_info.get("available_fields", []))
            if available_fields:
                fields_str = ", ".join(map(str, available_fields[:5]))
                if len(available_fields) > 5:
                    fields_str += f" (and {len(available_fields) - 5} more)"
                summary_table += f"| **Available Fields** | {fields_str} |\n"

        elif context_type == "Memory Context":
            summary_table += f"| **Memory Count** | {context_info.get('memory_count', 0)} |\n"
            summary_table += f"| **Oldest Memory** | {context_info.get('oldest_memory', 'N/A')} |\n"
            summary_table += f"| **Newest Memory** | {context_info.get('newest_memory', 'N/A')} |\n"

        elif context_type == "Conversation Results":
            summary_table += f"| **Message Type** | {context_info.get('message_type', 'N/A')} |\n"

        return markdown + summary_table + "\n"

    def _add_detailed_values(self, markdown: str, context_info: Dict[str, Any], user_valves) -> str:
        context_info = self._safe_dict(context_info)
        context_type = context_info.get("type", "Unknown")

        if context_type == "PV Addresses":
            pv_list = self._safe_list(context_info.get("pv_list", []))
            if pv_list:
                markdown += "**PV Addresses:**\n"
                for pv in pv_list[: user_valves.max_sample_items]:
                    markdown += f"- `{pv}`\n"
                if len(pv_list) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(pv_list) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "PV Values":
            pv_data = self._safe_dict(context_info.get("pv_data", {}))
            if pv_data:
                markdown += "**PV Values:**\n"
                count = 0
                for pv_name, pv_info in pv_data.items():
                    if count >= user_valves.max_sample_items:
                        break
                    pv_info = self._safe_dict(pv_info)
                    value = pv_info.get("value", "N/A")
                    units = pv_info.get("units", "")
                    timestamp = pv_info.get("timestamp", "N/A")
                    markdown += f"- `{pv_name}`: {value} {units} *(@ {timestamp})*\n"
                    count += 1
                if len(pv_data) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(pv_data) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "Archiver Data":
            pv_names = self._safe_list(context_info.get("pv_names", []))
            sample_values = self._safe_dict(context_info.get("sample_values", {}))

            if pv_names:
                markdown += "**Available PVs:**\n"
                for pv in pv_names[: user_valves.max_sample_items]:
                    markdown += f"- `{pv}`"
                    if pv in sample_values:
                        values = self._safe_list(sample_values[pv])[:3]
                        values_str = ", ".join(
                            f"{v:.3f}" if isinstance(v, (int, float)) else str(v) for v in values
                        )
                        markdown += f" (sample: {values_str}...)"
                    markdown += "\n"
                if len(pv_names) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(pv_names) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type in ["Analysis Results", "Visualization Results", "Operation Results"]:
            results = self._safe_dict(context_info.get("results", {}))
            if results:
                markdown += "**Results:**\n"
                count = 0
                for key, value in results.items():
                    if count >= user_valves.max_sample_items:
                        break
                    if isinstance(value, (list, dict)) and len(str(value)) > 100:
                        markdown += f"- **{str(key).replace('_', ' ').title()}**: *(large data structure)*\n"
                    else:
                        markdown += f"- **{str(key).replace('_', ' ').title()}**: {value}\n"
                    count += 1
                if len(results) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(results) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "Memory Context":
            memories = self._safe_list(context_info.get("memories", []))
            if memories:
                markdown += "**Memory Entries:**\n"
                for memory in memories[: user_valves.max_sample_items]:
                    memory = self._safe_dict(memory)
                    content = memory.get("content", "N/A")
                    timestamp = memory.get("timestamp", "N/A")
                    markdown += f"- {content} *(@ {timestamp})*\n"
                if len(memories) > user_valves.max_sample_items:
                    markdown += f"- *(and {len(memories) - user_valves.max_sample_items} more)*\n"
                markdown += "\n"

        elif context_type == "Conversation Results":
            full_response = self._safe_str(context_info.get("full_response", "N/A"))
            if full_response and len(full_response) > 200:
                markdown += f"**Response Preview:** {full_response[:200]}...\n\n"
            elif full_response:
                markdown += f"**Full Response:** {full_response}\n\n"

        return markdown

    async def action(self, body: dict, __user__=None, __event_emitter__=None, __event_call__=None) -> Optional[dict]:
        """Display formatted agent context using a popup modal."""
        logger.info(
            f"User - Name: {__user__['name']}, ID: {__user__['id']} - "
            "Requesting ALS Assistant agent context"
        )

        user_valves = __user__.get("valves")
        if not user_valves:
            user_valves = self.UserValves()

        await __event_emitter__(
            {"type": "status", "data": {"description": "Retrieving agent context...", "done": False}}
        )

        try:
            logger.info(f"Processing agent context request for user {__user__.get('name', 'unknown')}")
            logger.info(f"Message count: {len(body.get('messages', []))}")

            context_summary = self.extract_context_summary_from_messages(body.get("messages", []))

            if not context_summary:
                logger.info("No agent context found in messages")
                js_file_path = Path(__file__).parent / "agent_context_no_context.js"

                try:
                    with open(js_file_path, "r", encoding="utf-8") as f:
                        no_context_js = f.read()
                except FileNotFoundError:
                    logger.error(f"JavaScript file not found: {js_file_path}")
                    no_context_js = "alert('Error: JavaScript file not found');"

                await __event_call__({"type": "execute", "data": {"code": no_context_js}})
                await __event_emitter__(
                    {"type": "status", "data": {"description": "No agent context available", "done": True}}
                )
                return None

            logger.info(f"Found agent context: {list(context_summary.keys())}")

            await __event_emitter__(
                {"type": "status", "data": {"description": "Formatting agent context...", "done": False}}
            )

            formatted_context = self.format_context_summary_html(context_summary, user_valves)

            js_file_path = Path(__file__).parent / "agent_context_display.js"
            try:
                with open(js_file_path, "r", encoding="utf-8") as f:
                    context_js_template = f.read()
            except FileNotFoundError:
                logger.error(f"JavaScript file not found: {js_file_path}")
                context_js_template = "alert('Error: JavaScript file not found');"

            formatted_context_json = json.dumps(formatted_context)
            context_js = context_js_template.replace('"${FORMATTED_CONTEXT}"', formatted_context_json)

            await __event_call__({"type": "execute", "data": {"code": context_js}})
            await __event_emitter__(
                {"type": "status", "data": {"description": "Agent context displayed", "done": True}}
            )

            context_categories = len(context_summary.get("context_data", {}) or context_summary.get("context_details", {}))
            logger.info(
                f"User - Name: {__user__['name']}, ID: {__user__['id']} - "
                f"Agent context popup displayed successfully ({context_categories} categories)"
            )

        except Exception as e:
            logger.error(f"Error processing agent context: {e}")

            js_file_path = Path(__file__).parent / "agent_context_error.js"
            try:
                with open(js_file_path, "r", encoding="utf-8") as f:
                    error_js_template = f.read()
            except FileNotFoundError:
                logger.error(f"JavaScript file not found: {js_file_path}")
                error_js_template = "alert('Error: JavaScript file not found');"

            error_js = error_js_template.replace('"${ERROR_MESSAGE}"', json.dumps(str(e)))
            await __event_call__({"type": "execute", "data": {"code": error_js}})
            await __event_emitter__(
                {"type": "status", "data": {"description": "Error processing agent context", "done": True}}
            )

        return None

    def format_context_summary_html(self, context_summary: Dict[str, Any], user_valves) -> str:
        """Format the agent context summary as HTML for popup display (escaped)."""
        context_data = context_summary.get("context_data") or context_summary.get("context_details", {})

        if not context_summary or not context_data:
            no_data_style = "text-align: center; padding: 40px; color: #6b7280; font-style: italic"
            return f'<div style="{no_data_style}">No context data available.</div>'

        total_categories = context_summary.get("context_types_count") or len(context_data)
        total_items = context_summary.get("total_context_items", 0)

        html_parts = []

        overview_container_style = (
            "margin-bottom: 24px; padding: 20px; background: #f8fafc; "
            "border-radius: 8px; border: 1px solid #e2e8f0"
        )
        overview_header_style = (
            "display: flex; justify-content: space-between; "
            "align-items: center; margin-bottom: 12px"
        )
        overview_title_style = "font-size: 18px; font-weight: 600; color: #1f2937"
        overview_subtitle_style = "font-size: 14px; color: #6b7280"
        grid_style = "display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 12px"
        stat_box_style = (
            "text-align: center; padding: 12px; background: white; "
            "border-radius: 6px; border: 1px solid #e2e8f0"
        )
        stat_number_green_style = "font-size: 24px; font-weight: 700; color: #059669"
        stat_number_blue_style = "font-size: 24px; font-weight: 700; color: #0369a1"
        stat_label_style = "font-size: 13px; color: #6b7280; font-weight: 500"
        categories_text_style = "font-size: 14px; color: #4b5563"

        html_parts.append(
            f'<div style="{overview_container_style}">'
            f'<div style="{overview_header_style}">'
            f'<div style="{overview_title_style}">📊 Context Overview</div>'
            f'<div style="{overview_subtitle_style}">Available for use in subsequent queries</div>'
            f"</div>"
            f'<div style="{grid_style}">'
            f'<div style="{stat_box_style}"><div style="{stat_number_green_style}">{self._h(total_categories)}</div>'
            f'<div style="{stat_label_style}">Categories</div></div>'
            f'<div style="{stat_box_style}"><div style="{stat_number_blue_style}">{self._h(total_items)}</div>'
            f'<div style="{stat_label_style}">Total Items</div></div>'
            f"</div>"
        )

        categories = list(self._safe_dict(context_data).keys())
        if categories:
            categories_list = ", ".join(self._h(c) for c in categories)
            html_parts.append(
                f'<div style="{categories_text_style}"><strong>Categories:</strong> {categories_list}</div>'
            )
        html_parts.append("</div>")

        category_container_style = (
            "margin-bottom: 28px; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden"
        )
        category_header_style = "background: #f1f5f9; padding: 16px; border-bottom: 1px solid #e2e8f0"
        category_title_style = "margin: 0; color: #1f2937; font-size: 16px; font-weight: 600"
        category_body_style = "padding: 20px"

        item_container_style = (
            "margin-bottom: 24px; padding: 16px; background: #fafbfc; "
            "border-radius: 6px; border: 1px solid #e2e8f0"
        )
        item_title_style = "margin: 0 0 12px 0; color: #1f2937; font-size: 15px; font-weight: 600"
        item_type_style = "margin-bottom: 12px; font-size: 13px; color: #6b7280"

        for context_type, contexts_dict in self._safe_dict(context_data).items():
            category_emoji = self._get_category_emoji(str(context_type))
            category_name = str(context_type).replace("_", " ").title()

            html_parts.append(
                f'<div style="{category_container_style}">'
                f'<div style="{category_header_style}">'
                f'<h3 style="{category_title_style}">{self._h(category_emoji)} {self._h(category_name)}</h3>'
                f"</div>"
                f'<div style="{category_body_style}">'
            )

            for context_key, context_info in self._safe_dict(contexts_dict).items():
                context_info = self._safe_dict(context_info)
                context_type_name = context_info.get("type", "Unknown")

                html_parts.append(
                    f'<div style="{item_container_style}">'
                    f'<h4 style="{item_title_style}">🔹 {self._h(context_key)}</h4>'
                    f'<div style="{item_type_style}"><strong>Type:</strong> {self._h(context_type_name)}</div>'
                )

                html_parts.append(self._add_context_summary_table_html(context_info, user_valves))

                if user_valves.show_detailed_values:
                    html_parts.append(self._add_detailed_values_html(context_info, user_valves))

                html_parts.append("</div>")

            html_parts.append("</div></div>")

        return "".join(html_parts)

    def _add_context_summary_table_html(self, context_info: Dict[str, Any], user_valves) -> str:
        """Add summary table in HTML format (escaped)."""
        context_info = self._safe_dict(context_info)

        table_container_style = "overflow-x: auto; margin-bottom: 16px"
        table_style = "width: 100%; border-collapse: collapse; font-size: 13px"
        header_row_style = "background: #e2e8f0"
        th_style = (
            "padding: 8px 12px; text-align: left; border: 1px solid #cbd5e1; "
            "font-weight: 600; color: #374151"
        )
        td_field_style = (
            "padding: 8px 12px; border: 1px solid #cbd5e1; "
            "font-weight: 500; color: #374151"
        )
        td_value_style = "padding: 8px 12px; border: 1px solid #cbd5e1; color: #1f2937"

        summary_parts = [
            f'<div style="{table_container_style}"><table style="{table_style}"><thead>',
            f'<tr style="{header_row_style}"><th style="{th_style}">Field</th><th style="{th_style}">Value</th></tr>',
            "</thead><tbody>",
        ]

        context_type = context_info.get("type", "Unknown")

        if context_type == "PV Addresses":
            total_pvs = self._safe_num(context_info.get("total_pvs", 0))
            description = self._safe_str(context_info.get("description", "N/A"))
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Total PVs</td><td style="{td_value_style}">{self._h(total_pvs)}</td></tr>',
                    f'<tr><td style="{td_field_style}">Description</td><td style="{td_value_style}">{self._h(description)}</td></tr>',
                ]
            )

        elif context_type == "Time Range":
            start_time = self._safe_str(context_info.get("start_time", "N/A"))
            end_time = self._safe_str(context_info.get("end_time", "N/A"))
            duration = self._safe_str(context_info.get("duration", "N/A"))
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Start Time</td><td style="{td_value_style}">{self._h(start_time)}</td></tr>',
                    f'<tr><td style="{td_field_style}">End Time</td><td style="{td_value_style}">{self._h(end_time)}</td></tr>',
                    f'<tr><td style="{td_field_style}">Duration</td><td style="{td_value_style}">{self._h(duration)}</td></tr>',
                ]
            )

        elif context_type == "PV Values":
            pv_data = self._safe_dict(context_info.get("pv_data", {}))
            summary_parts.append(
                f'<tr><td style="{td_field_style}">PV Count</td><td style="{td_value_style}">{self._h(len(pv_data))}</td></tr>'
            )

        elif context_type == "Archiver Data":
            total_points = self._safe_num(context_info.get("total_points", 0))
            pv_count = self._safe_num(context_info.get("pv_count", 0))
            time_info = self._safe_str(context_info.get("time_info", "N/A"))
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Total Points</td><td style="{td_value_style}">{self._h(f"{total_points:,}")}</td></tr>',
                    f'<tr><td style="{td_field_style}">PV Count</td><td style="{td_value_style}">{self._h(pv_count)}</td></tr>',
                    f'<tr><td style="{td_field_style}">Time Info</td><td style="{td_value_style}">{self._h(time_info)}</td></tr>',
                ]
            )

        elif context_type in ["Analysis Results", "Visualization Results", "Operation Results"]:
            field_count = self._safe_num(context_info.get("field_count", 0))
            summary_parts.append(
                f'<tr><td style="{td_field_style}">Field Count</td><td style="{td_value_style}">{self._h(field_count)}</td></tr>'
            )
            available_fields = self._safe_list(context_info.get("available_fields", []))
            if available_fields:
                fields_preview = ", ".join(str(f) for f in available_fields[:5])
                if len(available_fields) > 5:
                    fields_preview += f" (and {len(available_fields) - 5} more)"
                summary_parts.append(
                    f'<tr><td style="{td_field_style}">Available Fields</td><td style="{td_value_style}">{self._h(fields_preview)}</td></tr>'
                )

        elif context_type == "Memory Context":
            memory_count = self._safe_num(context_info.get("memory_count", 0))
            oldest_memory = self._safe_str(context_info.get("oldest_memory", "N/A"))
            newest_memory = self._safe_str(context_info.get("newest_memory", "N/A"))
            summary_parts.extend(
                [
                    f'<tr><td style="{td_field_style}">Memory Count</td><td style="{td_value_style}">{self._h(memory_count)}</td></tr>',
                    f'<tr><td style="{td_field_style}">Oldest Memory</td><td style="{td_value_style}">{self._h(oldest_memory)}</td></tr>',
                    f'<tr><td style="{td_field_style}">Newest Memory</td><td style="{td_value_style}">{self._h(newest_memory)}</td></tr>',
                ]
            )

        elif context_type == "Conversation Results":
            message_type = self._safe_str(context_info.get("message_type", "N/A"))
            summary_parts.append(
                f'<tr><td style="{td_field_style}">Message Type</td><td style="{td_value_style}">{self._h(message_type)}</td></tr>'
            )

        summary_parts.append("</tbody></table></div>")
        return "".join(summary_parts)

    def _add_detailed_values_html(self, context_info: Dict[str, Any], user_valves) -> str:
        """Add detailed values section in HTML format (escaped)."""
        context_info = self._safe_dict(context_info)
        context_type = context_info.get("type", "Unknown")
        html_parts = []

        section_container_style = "margin-top: 16px"
        section_title_style = "margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #374151"
        section_content_style = (
            "background: #f8fafc; padding: 12px; border-radius: 4px; border: 1px solid #e2e8f0; "
            "font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto"
        )
        item_style = "margin-bottom: 4px; color: #1f2937"
        more_items_style = "color: #6b7280; font-style: italic"
        center_text_style = "color: #6b7280; font-style: italic; text-align: center; margin-top: 8px"

        if context_type == "PV Addresses":
            pv_list = self._safe_list(context_info.get("pv_list", []))
            if pv_list:
                html_parts.append(
                    f'<div style="{section_container_style}"><h5 style="{section_title_style}">PV Addresses:</h5>'
                    f'<div style="{section_content_style}">'
                )
                for pv in pv_list[: user_valves.max_sample_items]:
                    html_parts.append(f'<div style="{item_style}">• {self._h(pv)}</div>')
                if len(pv_list) > user_valves.max_sample_items:
                    remaining = len(pv_list) - user_valves.max_sample_items
                    html_parts.append(f'<div style="{more_items_style}">• (and {self._h(remaining)} more)</div>')
                html_parts.append("</div></div>")

        elif context_type == "PV Values":
            pv_data = self._safe_dict(context_info.get("pv_data", {}))
            if pv_data:
                pv_value_content_style = (
                    "background: #f8fafc; padding: 12px; border-radius: 4px; border: 1px solid #e2e8f0; "
                    "font-size: 12px; max-height: 200px; overflow-y: auto"
                )
                pv_value_item_style = (
                    "margin-bottom: 8px; padding: 8px; background: white; border-radius: 3px; border: 1px solid #e2e8f0"
                )
                pv_name_style = "color: #1f2937; font-family: monospace"
                pv_value_style = "color: #059669; font-weight: 600"
                pv_timestamp_style = "color: #6b7280; font-size: 11px"

                html_parts.append(
                    f'<div style="{section_container_style}"><h5 style="{section_title_style}">PV Values:</h5>'
                    f'<div style="{pv_value_content_style}">'
                )

                count = 0
                for pv_name, pv_info in pv_data.items():
                    if count >= user_valves.max_sample_items:
                        break
                    pv_info = self._safe_dict(pv_info)
                    value = pv_info.get("value", "N/A")
                    units = pv_info.get("units", "")
                    timestamp = pv_info.get("timestamp", "N/A")

                    html_parts.append(
                        f'<div style="{pv_value_item_style}">'
                        f'<strong style="{pv_name_style}">{self._h(pv_name)}:</strong> '
                        f'<span style="{pv_value_style}">{self._h(value)} {self._h(units)}</span> '
                        f'<span style="{pv_timestamp_style}">@ {self._h(timestamp)}</span>'
                        f"</div>"
                    )
                    count += 1

                if len(pv_data) > user_valves.max_sample_items:
                    remaining = len(pv_data) - user_valves.max_sample_items
                    html_parts.append(f'<div style="{center_text_style}">• (and {self._h(remaining)} more)</div>')

                html_parts.append("</div></div>")

        elif context_type == "Archiver Data":
            pv_names = self._safe_list(context_info.get("pv_names", []))
            sample_values = self._safe_dict(context_info.get("sample_values", {}))

            if pv_names:
                sample_style = "color: #6b7280; font-size: 11px"
                html_parts.append(
                    f'<div style="{section_container_style}"><h5 style="{section_title_style}">Available PVs:</h5>'
                    f'<div style="{section_content_style}">'
                )

                for pv in pv_names[: user_valves.max_sample_items]:
                    row = f'<div style="{item_style}">• {self._h(pv)}'
                    if pv in sample_values:
                        values = self._safe_list(sample_values[pv])[:3]
                        values_str = ", ".join(
                            f"{v:.3f}" if isinstance(v, (int, float)) else str(v) for v in values
                        )
                        row += f' <span style="{sample_style}">(sample: {self._h(values_str)}...)</span>'
                    row += "</div>"
                    html_parts.append(row)

                if len(pv_names) > user_valves.max_sample_items:
                    remaining = len(pv_names) - user_valves.max_sample_items
                    html_parts.append(f'<div style="{center_text_style}">• (and {self._h(remaining)} more)</div>')

                html_parts.append("</div></div>")

        elif context_type in ["Analysis Results", "Visualization Results", "Operation Results"]:
            results = self._safe_dict(context_info.get("results", {}))
            if results:
                results_content_style = (
                    "background: #f8fafc; padding: 12px; border-radius: 4px; border: 1px solid #e2e8f0; "
                    "font-size: 12px; max-height: 200px; overflow-y: auto"
                )
                result_item_style = (
                    "margin-bottom: 8px; padding: 8px; background: white; border-radius: 3px; border: 1px solid #e2e8f0"
                )
                result_key_style = "color: #1f2937"
                result_large_style = "color: #6b7280; font-style: italic"
                result_value_style = "color: #059669"

                html_parts.append(
                    f'<div style="{section_container_style}"><h5 style="{section_title_style}">Results:</h5>'
                    f'<div style="{results_content_style}">'
                )

                count = 0
                for key, value in results.items():
                    if count >= user_valves.max_sample_items:
                        break
                    display_key = str(key).replace("_", " ").title()

                    if isinstance(value, (list, dict)) and len(str(value)) > 100:
                        html_parts.append(
                            f'<div style="{result_item_style}"><strong style="{result_key_style}">{self._h(display_key)}:</strong> '
                            f'<span style="{result_large_style}">(large data structure)</span></div>'
                        )
                    else:
                        html_parts.append(
                            f'<div style="{result_item_style}"><strong style="{result_key_style}">{self._h(display_key)}:</strong> '
                            f'<span style="{result_value_style}">{self._h(value)}</span></div>'
                        )
                    count += 1

                if len(results) > user_valves.max_sample_items:
                    remaining = len(results) - user_valves.max_sample_items
                    html_parts.append(f'<div style="{center_text_style}">• (and {self._h(remaining)} more)</div>')

                html_parts.append("</div></div>")

        elif context_type == "Memory Context":
            memories = self._safe_list(context_info.get("memories", []))
            if memories:
                memory_content_style = (
                    "background: #f8fafc; padding: 12px; border-radius: 4px; border: 1px solid #e2e8f0; "
                    "font-size: 12px; max-height: 200px; overflow-y: auto"
                )
                memory_item_style = (
                    "margin-bottom: 8px; padding: 8px; background: white; border-radius: 3px; border: 1px solid #e2e8f0"
                )
                memory_content_style_inner = "color: #1f2937; margin-bottom: 4px"
                memory_timestamp_style = "color: #6b7280; font-size: 11px"

                html_parts.append(
                    f'<div style="{section_container_style}"><h5 style="{section_title_style}">Memory Entries:</h5>'
                    f'<div style="{memory_content_style}">'
                )

                for memory in memories[: user_valves.max_sample_items]:
                    memory = self._safe_dict(memory)
                    content = memory.get("content", "N/A")
                    timestamp = memory.get("timestamp", "N/A")
                    html_parts.append(
                        f'<div style="{memory_item_style}">'
                        f'<div style="{memory_content_style_inner}">{self._h(content)}</div>'
                        f'<div style="{memory_timestamp_style}">@ {self._h(timestamp)}</div>'
                        f"</div>"
                    )

                if len(memories) > user_valves.max_sample_items:
                    remaining = len(memories) - user_valves.max_sample_items
                    html_parts.append(f'<div style="{center_text_style}">• (and {self._h(remaining)} more)</div>')

                html_parts.append("</div></div>")

        elif context_type == "Conversation Results":
            full_response = self._safe_str(context_info.get("full_response", "N/A"))
            if full_response:
                response_content_style = (
                    "background: #f8fafc; padding: 12px; border-radius: 4px; border: 1px solid #e2e8f0; "
                    "font-size: 12px; max-height: 200px; overflow-y: auto"
                )
                response_text_style = "color: #1f2937; line-height: 1.4"

                html_parts.append(
                    f'<div style="{section_container_style}"><h5 style="{section_title_style}">Response:</h5>'
                    f'<div style="{response_content_style}">'
                )

                if len(full_response) > 200:
                    preview = full_response[:200]
                    html_parts.append(
                        f'<div style="{response_text_style}"><strong>Preview:</strong> {self._h(preview)}...</div>'
                    )
                else:
                    html_parts.append(
                        f'<div style="{response_text_style}"><strong>Full Response:</strong> {self._h(full_response)}</div>'
                    )

                html_parts.append("</div></div>")

        return "".join(html_parts)


actions = [
    {
        "id": "als_assistant_agent_context",
        "name": "Agent Context",
        "description": "View current ALS Assistant agent context data and available information",
        "icon_url": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyUzYuNDggMjIgMTIgMjJTMjIgMTcuNTIgMjIgMTJTMTcuNTIgMiAxMiAyWk0xMiAyMEM3LjU5IDIwIDQgMTYuNDEgNCAxMlM3LjU5IDQgMTIgNFMyMCA3LjU5IDIwIDEyUzE2LjQxIDIwIDEyIDIwWiIgZmlsbD0iY3VycmVudENvbG9yIi8+CjxwYXRoIGQ9Ik0xMiA2VjhNMTIgMTZWMThNMTAgMTJIMTRNOCAxMkg2TTE4IDEySDE2IiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+",
    }
]