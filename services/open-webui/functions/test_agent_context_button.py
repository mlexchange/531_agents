"""
Test script for agent_context_button.py

Run with: python test_agent_context_button.py
"""

import asyncio
import sys
from pathlib import Path

# Add the functions directory to path so we can import agent_context_button
sys.path.insert(0, str(Path(__file__).parent))

from agent_context_button import Action  # noqa: E402


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


def create_mock_agent_context():
    """Create mock agent context data."""
    return {
        "context_types_count": 3,
        "total_context_items": 5,
        "context_data": {
            "PV_ADDRESSES": {
                "beamline_531_pvs": {
                    "type": "PV Addresses",
                    "total_pvs": 10,
                    "description": "Beamline 531 process variables",
                    "pv_list": [
                        "BL531:TEMP1",
                        "BL531:TEMP2",
                        "BL531:PRESSURE1",
                        "BL531:FLOW1",
                        "BL531:VALVE1",
                    ],
                }
            },
            "TIME_RANGE": {
                "analysis_period": {
                    "type": "Time Range",
                    "start_time": "2025-01-01T00:00:00Z",
                    "end_time": "2025-01-02T00:00:00Z",
                    "duration": "24 hours",
                }
            },
            "ARCHIVER_DATA": {
                "temperature_data": {
                    "type": "Archiver Data",
                    "total_points": 86400,
                    "pv_count": 2,
                    "time_info": "2025-01-01 to 2025-01-02",
                    "pv_names": ["BL531:TEMP1", "BL531:TEMP2"],
                    "sample_values": {
                        "BL531:TEMP1": [20.5, 20.6, 20.4],
                        "BL531:TEMP2": [21.2, 21.3, 21.1],
                    },
                }
            },
        },
    }


def create_old_format_agent_context():
    """Create mock agent context data in old format."""
    return {
        "context_details": {
            "PV_ADDRESSES": {
                "beamline_pvs": {
                    "type": "PV Addresses",
                    "total_pvs": 5,
                    "description": "Test PVs",
                    "pv_list": ["TEST:PV1", "TEST:PV2", "TEST:PV3"],
                }
            },
            "PV_VALUES": {
                "current_values": {
                    "type": "PV Values",
                    "pv_data": {
                        "TEST:PV1": {
                            "value": 42.5,
                            "units": "°C",
                            "timestamp": "2025-01-01T12:00:00Z",
                        },
                        "TEST:PV2": {
                            "value": 100.0,
                            "units": "PSI",
                            "timestamp": "2025-01-01T12:00:00Z",
                        },
                    },
                }
            },
        },
        "total_context_items": 2,
    }


async def test_no_agent_context():
    """Test when no agent context is available."""
    print("\n" + "=" * 80)
    print("TEST 1: No Agent Context")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall()
    user = create_mock_user()

    # Body with messages but no agent context
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
    assert len(caller.calls) == 1, "Should execute JavaScript for 'no context' popup"


async def test_with_agent_context_new_format():
    """Test with valid agent context (new format)."""
    print("\n" + "=" * 80)
    print("TEST 2: With Agent Context (New Format)")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall()
    user = create_mock_user()

    # Create agent context
    agent_context = create_mock_agent_context()

    # Body with messages containing agent context
    body = {
        "messages": [
            {"role": "user", "content": "Show me the context"},
            {
                "role": "assistant",
                "content": "Here's the context...",
                "info": {"als_assistant_agent_context": agent_context},
            },
        ]
    }

    result = await action.action(
        body=body, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print(f"✅ Total events emitted: {len(emitter.events)}")
    print(f"✅ Total calls made: {len(caller.calls)}")
    print(f"✅ Context categories: {agent_context['context_types_count']}")

    assert len(caller.calls) == 1, "Should execute JavaScript for context popup"


async def test_with_agent_context_old_format():
    """Test with valid agent context (old format)."""
    print("\n" + "=" * 80)
    print("TEST 3: With Agent Context (Old Format)")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall()
    user = create_mock_user()

    # Create agent context in old format
    agent_context = create_old_format_agent_context()

    # Body with messages containing agent context (old key name)
    body = {
        "messages": [
            {"role": "user", "content": "Show me the context"},
            {
                "role": "assistant",
                "content": "Here's the context...",
                "info": {"als_assistant_context_summary": agent_context},
            },
        ]
    }

    result = await action.action(
        body=body, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print(f"✅ Total events emitted: {len(emitter.events)}")
    print(f"✅ Total calls made: {len(caller.calls)}")
    print(f"✅ Context categories: {len(agent_context.get('context_details', {}))}")

    assert len(caller.calls) == 1, "Should execute JavaScript for context popup"


async def test_html_formatting():
    """Test HTML formatting of agent context."""
    print("\n" + "=" * 80)
    print("TEST 4: HTML Formatting")
    print("=" * 80)

    action = Action()
    user_valves = Action.UserValves(
        show_detailed_values=True,
        show_technical_info=False,
        max_sample_items=5,
    )

    agent_context = create_mock_agent_context()

    html = action.format_context_summary_html(agent_context, user_valves)

    print(f"✅ Generated HTML length: {len(html)} chars")
    print(f"✅ Contains context overview: {'Context Overview' in html}")
    print(f"✅ Contains PV addresses: {'PV Addresses' in html}")
    print(f"✅ Contains categories: {'Categories' in html}")

    assert len(html) > 0, "HTML should not be empty"
    assert "Context Overview" in html, "Should contain overview section"
    assert "PV_ADDRESSES" in html or "PV Addresses" in html


async def test_extraction_from_messages():
    """Test extraction of agent context from messages."""
    print("\n" + "=" * 80)
    print("TEST 5: Extraction from Messages")
    print("=" * 80)

    action = Action()
    agent_context = create_mock_agent_context()

    # Test with agent context in last message
    messages = [
        {"role": "user", "content": "Test"},
        {
            "role": "assistant",
            "content": "Response",
            "info": {"als_assistant_agent_context": agent_context},
        },
    ]

    extracted = action.extract_context_summary_from_messages(messages)
    print(
        f"✅ Extracted context: "
        f"{extracted.get('context_types_count', 0) if extracted else 0} categories"
    )
    assert extracted == agent_context, "Should extract correct context"

    # Test with no agent context
    messages_no_context = [
        {"role": "user", "content": "Test"},
        {"role": "assistant", "content": "Response", "info": {}},
    ]

    extracted_none = action.extract_context_summary_from_messages(messages_no_context)
    print(f"✅ No context case: {extracted_none}")
    assert extracted_none is None, "Should return None when no context"


async def test_user_valves():
    """Test different user valve configurations."""
    print("\n" + "=" * 80)
    print("TEST 6: User Valves Configuration")
    print("=" * 80)

    action = Action()
    agent_context = create_mock_agent_context()

    # Test with detailed values enabled
    valves_detailed = Action.UserValves(
        show_detailed_values=True,
        show_technical_info=True,
        max_sample_items=10,
    )
    html_detailed = action.format_context_summary_html(agent_context, valves_detailed)
    print(f"✅ Detailed HTML length: {len(html_detailed)} chars")

    # Test with minimal values
    valves_minimal = Action.UserValves(
        show_detailed_values=False,
        show_technical_info=False,
        max_sample_items=3,
    )
    html_minimal = action.format_context_summary_html(agent_context, valves_minimal)
    print(f"✅ Minimal HTML length: {len(html_minimal)} chars")

    assert len(html_detailed) > len(html_minimal), "Detailed HTML should be longer"
    print("✅ User valves affect output correctly")


async def test_category_emoji():
    """Test category emoji mapping."""
    print("\n" + "=" * 80)
    print("TEST 7: Category Emoji Mapping")
    print("=" * 80)

    action = Action()

    test_categories = [
        "PV_ADDRESSES",
        "TIME_RANGE",
        "ARCHIVER_DATA",
        "ANALYSIS_RESULTS",
        "UNKNOWN_CATEGORY",
    ]

    for category in test_categories:
        emoji = action._get_category_emoji(category)
        print(f"✅ {category}: {emoji}")
        assert emoji, f"Should have emoji for {category}"


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪" * 40)
    print("AGENT CONTEXT BUTTON TEST SUITE")
    print("🧪" * 40)

    try:
        await test_no_agent_context()
        await test_with_agent_context_new_format()
        await test_with_agent_context_old_format()
        await test_html_formatting()
        await test_extraction_from_messages()
        await test_user_valves()
        await test_category_emoji()

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
