"""
title: ALS Assistant Execution History
author: ALS Assistant Team
version: 0.1.0
required_open_webui_version: 0.5.1
icon_url: data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJMMTMuMDkgOC4yNkwyMCA5TDEzLjA5IDE1Ljc0TDEyIDIyTDEwLjkxIDE1Ljc0TDQgOUwxMC45MSA4LjI2TDEyIDJaIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+ # noqa: E501 can't break url
Description: View ALS Assistant Agent execution history for the last response
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Action:
    class Valves(BaseModel):
        pass

    class UserValves(BaseModel):
        show_detailed_steps: bool = Field(
            default=True, description="Show detailed step information"
        )
        show_timestamps: bool = Field(default=True, description="Show execution timestamps")
        show_step_results: bool = Field(
            default=False, description="Show detailed step results (may be verbose)"
        )

    def __init__(self):
        self.valves = self.Valves()

    def extract_execution_history_from_messages(self, messages: list):
        """Extract execution history data from assistant messages."""

        # Look through messages in reverse order (most recent first)
        for message in reversed(messages):
            if message.get("role") == "assistant" and message.get("info"):
                # Check for execution history (OpenWebUI always serializes to JSON)
                if "als_assistant_execution_history_raw" in message["info"]:
                    execution_data = message["info"]["als_assistant_execution_history_raw"]
                    logger.info(f"Found execution history: {len(execution_data)} records")
                    return execution_data

        return None

    def format_execution_history_html(self, execution_history, user_valves) -> str:
        """Format the execution history as HTML for popup display."""
        if not execution_history:
            no_history_style = " ".join(
                [
                    "text-align: center;",
                    "padding: 40px;",
                    "color: #6b7280;",
                    "font-style: italic;",
                ]
            )
            return f'<div style="{no_history_style}">No execution history available.</div>'

        # Calculate step execution time
        step_duration = 0.0
        for record in execution_history:
            start_time_str = record.get("start_time")
            end_time_str = record.get("end_time")
            if start_time_str and end_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    step_duration += (end_time - start_time).total_seconds()
                except Exception:
                    pass

        # --- Shared / reusable styles ---
        header_container_style = " ".join(
            [
                "margin-bottom: 24px;",
                "padding: 20px;",
                "background: #f8fafc;",
                "border-radius: 8px;",
                "border: 1px solid #e2e8f0;",
            ]
        )
        header_flex_style = " ".join(
            [
                "display: flex;",
                "justify-content: space-between;",
                "align-items: center;",
                "margin-bottom: 12px;",
            ]
        )
        header_title_style = " ".join(
            [
                "font-size: 18px;",
                "font-weight: 600;",
                "color: #1f2937;",
            ]
        )
        header_subtitle_style = " ".join(
            [
                "font-size: 14px;",
                "color: #6b7280;",
            ]
        )
        grid_style = " ".join(
            [
                "display: grid;",
                "grid-template-columns: 1fr 1fr;",
                "gap: 16px;",
                "margin-bottom: 12px;",
            ]
        )
        stat_box_style = " ".join(
            [
                "text-align: center;",
                "padding: 12px;",
                "background: white;",
                "border-radius: 6px;",
                "border: 1px solid #e2e8f0;",
            ]
        )
        stat_number_steps_style = " ".join(
            [
                "font-size: 24px;",
                "font-weight: 700;",
                "color: #0369a1;",
            ]
        )
        stat_number_time_style = " ".join(
            [
                "font-size: 24px;",
                "font-weight: 700;",
                "color: #059669;",
            ]
        )
        stat_label_style = " ".join(
            [
                "font-size: 13px;",
                "color: #6b7280;",
                "font-weight: 500;",
            ]
        )
        table_container_style = " ".join(
            [
                "overflow-x: auto;",
                "margin-bottom: 16px;",
            ]
        )
        table_style = " ".join(
            [
                "width: 100%;",
                "border-collapse: collapse;",
                "font-size: 13px;",
            ]
        )
        th_style = " ".join(
            [
                "padding: 8px 12px;",
                "text-align: left;",
                "border: 1px solid #cbd5e1;",
                "font-weight: 600;",
                "color: #374151;",
            ]
        )
        td_field_style = " ".join(
            [
                "padding: 8px 12px;",
                "border: 1px solid #cbd5e1;",
                "font-weight: 500;",
                "color: #374151;",
            ]
        )
        td_value_style = " ".join(
            [
                "padding: 8px 12px;",
                "border: 1px solid #cbd5e1;",
                "color: #1f2937;",
            ]
        )
        td_mono_style = " ".join(
            [
                "padding: 8px 12px;",
                "border: 1px solid #cbd5e1;",
                "color: #1f2937;",
                "font-family: monospace;",
            ]
        )
        step_container_style = " ".join(
            [
                "margin-bottom: 24px;",
                "border: 1px solid #e2e8f0;",
                "border-radius: 8px;",
                "overflow: hidden;",
            ]
        )
        step_title_style = " ".join(
            [
                "margin: 0;",
                "color: #1f2937;",
                "font-size: 16px;",
                "font-weight: 600;",
            ]
        )
        step_body_style = " ".join(
            [
                "padding: 20px;",
            ]
        )
        section_style = " ".join(
            [
                "margin-bottom: 16px;",
            ]
        )
        section_title_style = " ".join(
            [
                "margin: 0 0 8px 0;",
                "font-size: 14px;",
                "font-weight: 600;",
                "color: #374151;",
            ]
        )
        section_content_style = " ".join(
            [
                "background: #f8fafc;",
                "padding: 12px;",
                "border-radius: 4px;",
                "border: 1px solid #e2e8f0;",
                "font-size: 13px;",
                "color: #1f2937;",
            ]
        )
        code_section_style = " ".join(
            [
                "background: #f8fafc;",
                "padding: 12px;",
                "border-radius: 4px;",
                "border: 1px solid #e2e8f0;",
                "font-family: monospace;",
                "font-size: 12px;",
                "color: #1f2937;",
                "max-height: 200px;",
                "overflow-y: auto;",
            ]
        )
        pre_style = " ".join(
            [
                "margin: 0;",
                "white-space: pre-wrap;",
            ]
        )
        error_section_style = " ".join(
            [
                "margin-bottom: 16px;",
                "padding: 12px;",
                "background: #fef2f2;",
                "border-radius: 4px;",
                "border: 1px solid #fecaca;",
            ]
        )
        error_title_style = " ".join(
            [
                "margin: 0 0 8px 0;",
                "font-size: 14px;",
                "font-weight: 600;",
                "color: #dc2626;",
            ]
        )
        error_content_style = " ".join(
            [
                "font-size: 13px;",
                "color: #7f1d1d;",
                "line-height: 1.4;",
            ]
        )
        error_line_style = " ".join(
            [
                "margin-bottom: 4px;",
            ]
        )
        result_code_style = " ".join(
            [
                "background: #f8fafc;",
                "padding: 12px;",
                "border-radius: 4px;",
                "border: 1px solid #e2e8f0;",
                "font-family: monospace;",
                "font-size: 12px;",
                "color: #1f2937;",
                "max-height: 300px;",
                "overflow-y: auto;",
            ]
        )

        # --- Build HTML ---
        html_parts = []

        # Header
        html_parts.append(
            f'<div style="{header_container_style}">'
            f'<div style="{header_flex_style}">'
            f'<div style="{header_title_style}">📊 Execution Overview</div>'
            f'<div style="{header_subtitle_style}">Steps executed in last response</div>'
            f"</div>"
            f'<div style="{grid_style}">'
            f'<div style="{stat_box_style}">'
            f'<div style="{stat_number_steps_style}">{len(execution_history)}</div>'
            f'<div style="{stat_label_style}">Total Steps</div>'
            f"</div>"
            f'<div style="{stat_box_style}">'
            f'<div style="{stat_number_time_style}">{step_duration: .2f}s</div>'
            f'<div style="{stat_label_style}">Step Time</div>'
            f"</div></div></div>"
        )

        # Steps
        for i, record in enumerate(execution_history, 1):
            step = record.get("step", {})
            result = record.get("result", {})
            success = result.get("success", False)

            # Dynamic per-step styles (dependent on success flag)
            header_bg = "#f0f9ff" if success else "#fef2f2"
            status_color = "#059669" if success else "#dc2626"
            step_header_style = " ".join(
                [
                    f"background: {header_bg}",
                    "; ",
                    "padding: 16px; ",
                    "border-bottom: 1px solid #e2e8f0; ",
                ]
            )
            step_status_style = " ".join(
                [
                    "margin-top: 8px;",
                    "font-size: 14px;",
                    "font-weight: 500;",
                    f"color: {status_color}",
                    ";",
                ]
            )
            td_status_style = " ".join(
                [
                    "padding: 8px 12px;",
                    "border: 1px solid #cbd5e1;",
                    f"color: {status_color}",
                    ";",
                    "font-weight: 600;",
                ]
            )

            status_emoji = "✅" if success else "❌"
            status_text = "✓ Success" if success else "✗ Failed"
            description = step.get("description", "Unknown step")

            html_parts.append(
                f'<div style="{step_container_style}">'
                f'<div style="{step_header_style}">'
                f'<h3 style="{step_title_style}">{status_emoji} Step {i}: {description}</h3>'
                f'<div style="{step_status_style}">{status_text}</div>'
                f'</div><div style="{step_body_style}">'
            )

            # Info table
            node_type = step.get("node_type", "unknown")
            html_parts.append(
                f'<div style="{table_container_style}">'
                f'<table style="{table_style}"><thead>'
                f'<tr style="background: #e2e8f0">'
                f'<th style="{th_style}">Field</th>'
                f'<th style="{th_style}">Value</th>'
                f"</tr></thead><tbody>"
                f'<tr><td style="{td_field_style}">Node Type</td>'
                f'<td style="{td_mono_style}">{node_type}</td></tr>'
                f'<tr><td style="{td_field_style}">Status</td>'
                f'<td style="{td_status_style}">{status_emoji} {status_text}</td></tr>'
            )

            success_criteria = step.get("success_criteria")
            if success_criteria:
                html_parts.append(
                    f'<tr><td style="{td_field_style}">Success Criteria</td>'
                    f'<td style="{td_value_style}">{success_criteria}</td></tr>'
                )

            if user_valves.show_timestamps:
                start_time_str = record.get("start_time")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        start_formatted = start_time.strftime("%H:%M:%S")
                        html_parts.append(
                            f'<tr><td style="{td_field_style}">Start Time</td>'
                            f'<td style="{td_value_style}">{start_formatted}</td></tr>'
                        )
                        end_time_str = record.get("end_time")
                        if end_time_str:
                            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                            duration = (end_time - start_time).total_seconds()
                            html_parts.append(
                                f'<tr><td style="{td_field_style}">Duration</td>'
                                f'<td style="{td_value_style}">{duration: .2f}s</td></tr>'
                            )
                    except Exception:
                        pass

            html_parts.append("</tbody></table></div>")

            # Input requirements
            input_requirements = step.get("input_requirements", [])
            if input_requirements and user_valves.show_detailed_steps:
                req_text = ", ".join(input_requirements)
                html_parts.append(
                    f'<div style="{section_style}">'
                    f'<h5 style="{section_title_style}">📝 Input Requirements: </h5>'
                    f'<div style="{section_content_style}">{req_text}</div></div>'
                )

            # Parameters
            parameters = step.get("parameters", {})
            if parameters and user_valves.show_detailed_steps:
                params_json = json.dumps(parameters, indent=2)
                html_parts.append(
                    f'<div style="{section_style}">'
                    f'<h5 style="{section_title_style}">⚙️ Parameters: </h5>'
                    f'<div style="{code_section_style}">'
                    f'<pre style="{pre_style}">{params_json}</pre></div></div>'
                )

            # Error details
            if not success:
                error = result.get("error")
                if error:
                    err_msg = error.get("message", "No error message")
                    err_sev = error.get("severity", "unknown")
                    html_parts.append(
                        f'<div style="{error_section_style}">'
                        f'<h5 style="{error_title_style}">🚨 Error Details: </h5>'
                        f'<div style="{error_content_style}">'
                        f'<div style="{error_line_style}"><strong>Message: </strong>{err_msg}</div>'
                        f"<div><strong>Severity: </strong>{err_sev}</div>"
                        f"</div></div>"
                    )

            # Result data
            if user_valves.show_step_results:
                result_data = result.get("data")
                if result_data:
                    result_json = json.dumps(result_data, indent=2, default=str)
                    html_parts.append(
                        f'<div style="{section_style}">'
                        f'<h5 style="{section_title_style}">📊 Result Data: </h5>'
                        f'<div style="{result_code_style}">'
                        f'<pre style="{pre_style}">{result_json}</pre></div></div>'
                    )

            html_parts.append("</div></div>")

        return "".join(html_parts)

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> Optional[dict]:
        """Display formatted execution history using a popup modal."""
        logger.info(
            f"User - Name: {__user__['name']}, ID: {__user__['id']} - "
            "Requesting ALS Assistant execution history"
        )

        user_valves = __user__.get("valves")
        if not user_valves:
            user_valves = self.UserValves()

        await __event_emitter__(
            {
                "type": "status",
                "data": {"description": "Retrieving execution history...", "done": False},
            }
        )

        try:
            # Log debug information about the request
            logger.info(
                f"Processing execution history request for user "
                f"{__user__.get('name', 'unknown')}"
            )
            logger.info(f"Message count: {len(body.get('messages', []))}")

            # Extract execution history from the last assistant message
            execution_history = self.extract_execution_history_from_messages(
                body.get("messages", [])
            )

            if not execution_history:
                logger.info("No execution history found in messages")

                # Load no history JavaScript
                js_file_path = Path(__file__).parent / "execution_history_no_history.js"

                try:
                    with open(js_file_path, "r", encoding="utf-8") as f:
                        no_history_js = f.read()
                except FileNotFoundError:
                    logger.error(f"JavaScript file not found: {js_file_path}")
                    no_history_js = "alert('Error: JavaScript file not found');"

                await __event_call__(
                    {
                        "type": "execute",
                        "data": {"code": no_history_js},
                    }
                )

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "No execution history available",
                            "done": True,
                        },
                    }
                )
                return None

            logger.info(f"Found execution history: {len(execution_history)} steps")

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": "Formatting execution history...",
                        "done": False,
                    },
                }
            )

            # Format the execution history as HTML for the popup
            formatted_history = self.format_execution_history_html(execution_history, user_valves)

            # Load history display JavaScript
            js_file_path = Path(__file__).parent / "execution_history_display.js"

            try:
                with open(js_file_path, "r", encoding="utf-8") as f:
                    history_js_template = f.read()
            except FileNotFoundError:
                logger.error(f"JavaScript file not found: {js_file_path}")
                history_js_template = "alert('Error: JavaScript file not found');"

            # Replace placeholder with formatted history
            history_js = history_js_template.replace("${FORMATTED_HISTORY}", formatted_history)

            await __event_call__(
                {
                    "type": "execute",
                    "data": {"code": history_js},
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Execution history displayed", "done": True},
                }
            )

            logger.info(
                f"User - Name: {__user__['name']}, ID: {__user__['id']} - "
                f"Execution history popup displayed successfully "
                f"({len(execution_history)} steps)"
            )

        except Exception as e:
            logger.error(f"Error processing execution history: {e}")

            # Load error JavaScript
            js_file_path = Path(__file__).parent / "execution_history_error.js"

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
                        "description": "Error processing execution history",
                        "done": True,
                    },
                }
            )

        return None


# Action registration - required for OpenWebUI to recognize this as an action button
actions = [
    {
        "id": "als_assistant_execution_history",
        "name": "Execution History",
        "description": "View ALS Assistant execution history for the last response",
        "icon_url": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJMMTMuMDkgOC4yNkwyMCA5TDEzLjA5IDE1Ljc0TDEyIDIyTDEwLjkxIDE1Ljc0TDQgOUwxMC45MSA4LjI2TDEyIDJaIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+",  # noqa: E501 can't break url
    }
]
