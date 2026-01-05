"""
Test script for execution_history_button.py

Run with: python test_execution_history_button.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the functions directory to path so we can import execution_history_button
sys.path.insert(0, str(Path(__file__).parent))

from execution_history_button import Action  # noqa: E402


class MockEventEmitter:
    """Mock event emitter for testing."""

    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)
        print(f"📤 EVENT: {event['type']}")
        if event.get("data"):
            data_preview = str(event["data"])[:100]
            print(f"   Data: {data_preview}...")


class MockEventCall:
    """Mock event call for testing."""

    def __init__(self):
        self.calls = []

    async def __call__(self, event):
        self.calls.append(event)
        print(f"📞 CALL: {event['type']}")

        if event["type"] == "execute":
            code = event["data"].get("code", "")
            print(f"   JavaScript code length: {len(code)} chars")
            print(f"   First 100 chars: {code[:100]}...")

        return None


def create_mock_user(user_id="test_user", name="Test User"):
    """Create a mock user object."""
    return {
        "id": user_id,
        "name": name,
        "email": f"{user_id}@example.com",
        "valves": None,
    }


def create_mock_execution_history():
    """Create mock execution history data."""
    now = datetime.now(timezone.utc)
    start_time = now.isoformat()
    end_time = now.replace(second=now.second + 5).isoformat()

    return [
        {
            "step": {
                "node_type": "PV_SEARCH",
                "description": "Search for process variables",
                "success_criteria": "Found matching PVs",
                "input_requirements": ["SEARCH_PATTERN"],
                "parameters": {"pattern": "BL531:*", "limit": 100},
            },
            "result": {
                "success": True,
                "data": {"pv_count": 42, "pvs": ["BL531:TEMP1", "BL531:TEMP2"]},
            },
            "start_time": start_time,
            "end_time": end_time,
        },
        {
            "step": {
                "node_type": "ARCHIVER_DATA_RETRIEVAL",
                "description": "Retrieve archiver data",
                "success_criteria": "Data retrieved successfully",
                "input_requirements": ["PV_ADDRESSES", "TIME_RANGE"],
                "parameters": {
                    "pvs": ["BL531:TEMP1"],
                    "start": "2025-01-01T00:00:00Z",
                    "end": "2025-01-02T00:00:00Z",
                },
            },
            "result": {
                "success": True,
                "data": {"points": 1000, "duration": "24h"},
            },
            "start_time": end_time,
            "end_time": now.replace(second=now.second + 10).isoformat(),
        },
        {
            "step": {
                "node_type": "DATA_ANALYSIS",
                "description": "Analyze temperature trends",
                "success_criteria": "Analysis completed",
                "input_requirements": ["ARCHIVER_DATA"],
                "parameters": {"method": "trend_analysis"},
            },
            "result": {
                "success": False,
                "error": {
                    "message": "Insufficient data points for analysis",
                    "severity": "warning",
                },
            },
            "start_time": now.replace(second=now.second + 10).isoformat(),
            "end_time": now.replace(second=now.second + 12).isoformat(),
        },
    ]


async def test_no_execution_history():
    """Test when no execution history is available."""
    print("\n" + "=" * 80)
    print("TEST 1: No Execution History")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall()
    user = create_mock_user()

    # Body with messages but no execution history
    body = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!", "info": {}},
        ]
    }

    result = await action.action(
        body=body, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print(f"✅ Total events emitted: {len(emitter.events)}")
    print(f"✅ Total calls made: {len(caller.calls)}")
    assert len(caller.calls) == 1, "Should execute JavaScript for 'no history' popup"


async def test_with_execution_history():
    """Test with valid execution history."""
    print("\n" + "=" * 80)
    print("TEST 2: With Execution History")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall()
    user = create_mock_user()

    # Create execution history
    execution_history = create_mock_execution_history()

    # Body with messages containing execution history
    body = {
        "messages": [
            {"role": "user", "content": "Show me PV data"},
            {
                "role": "assistant",
                "content": "Here's the data...",
                "info": {"als_assistant_execution_history_raw": execution_history},
            },
        ]
    }

    result = await action.action(
        body=body, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print(f"✅ Total events emitted: {len(emitter.events)}")
    print(f"✅ Total calls made: {len(caller.calls)}")
    print(f"✅ Execution history steps: {len(execution_history)}")

    assert len(caller.calls) == 1, "Should execute JavaScript for history popup"


async def test_html_formatting():
    """Test HTML formatting of execution history."""
    print("\n" + "=" * 80)
    print("TEST 3: HTML Formatting")
    print("=" * 80)

    action = Action()
    user_valves = Action.UserValves(
        show_detailed_steps=True, show_timestamps=True, show_step_results=True
    )

    execution_history = create_mock_execution_history()

    html = action.format_execution_history_html(execution_history, user_valves)

    print(f"✅ Generated HTML length: {len(html)} chars")
    print(f"✅ Contains step count: {'Total Steps' in html}")
    print(f"✅ Contains success indicators: {'✅' in html}")
    print(f"✅ Contains error indicators: {'❌' in html}")
    print(f"✅ Contains timing info: {'Duration' in html}")

    assert len(html) > 0, "HTML should not be empty"
    assert "Total Steps" in html, "Should contain steps summary"
    assert "✅" in html, "Should contain success emoji"
    assert "❌" in html, "Should contain error emoji"


async def test_extraction_from_messages():
    """Test extraction of execution history from messages."""
    print("\n" + "=" * 80)
    print("TEST 4: Extraction from Messages")
    print("=" * 80)

    action = Action()
    execution_history = create_mock_execution_history()

    # Test with execution history in last message
    messages = [
        {"role": "user", "content": "Test"},
        {
            "role": "assistant",
            "content": "Response",
            "info": {"als_assistant_execution_history_raw": execution_history},
        },
    ]

    extracted = action.extract_execution_history_from_messages(messages)
    print(f"✅ Extracted history: {len(extracted) if extracted else 0} steps")
    assert extracted == execution_history, "Should extract correct history"

    # Test with no execution history
    messages_no_history = [
        {"role": "user", "content": "Test"},
        {"role": "assistant", "content": "Response", "info": {}},
    ]

    extracted_none = action.extract_execution_history_from_messages(messages_no_history)
    print(f"✅ No history case: {extracted_none}")
    assert extracted_none is None, "Should return None when no history"


async def test_user_valves():
    """Test different user valve configurations."""
    print("\n" + "=" * 80)
    print("TEST 5: User Valves Configuration")
    print("=" * 80)

    action = Action()
    execution_history = create_mock_execution_history()

    # Test with all features enabled
    valves_all = Action.UserValves(
        show_detailed_steps=True, show_timestamps=True, show_step_results=True
    )
    html_all = action.format_execution_history_html(execution_history, valves_all)
    print(f"✅ All features HTML length: {len(html_all)} chars")

    # Test with minimal features
    valves_minimal = Action.UserValves(
        show_detailed_steps=False, show_timestamps=False, show_step_results=False
    )
    html_minimal = action.format_execution_history_html(execution_history, valves_minimal)
    print(f"✅ Minimal features HTML length: {len(html_minimal)} chars")

    assert len(html_all) > len(html_minimal), "Full HTML should be longer than minimal"
    print("✅ User valves affect output correctly")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪" * 40)
    print("EXECUTION HISTORY BUTTON TEST SUITE")
    print("🧪" * 40)

    try:
        await test_no_execution_history()
        await test_with_execution_history()
        await test_html_formatting()
        await test_extraction_from_messages()
        await test_user_valves()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    finally:
        print("\n✨ Test suite completed")
