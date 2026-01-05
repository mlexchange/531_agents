"""
Test script for execution_plan_editor.py

Run with: python test_execution_plan_editor.py
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Set up test environment BEFORE importing Action
test_dir = tempfile.mkdtemp(prefix="plan_editor_test_")
os.environ["PLAN_EDITOR_DATA"] = test_dir

# Add the functions directory to path so we can import execution_plan_editor
sys.path.insert(0, str(Path(__file__).parent))
# isort: off
from execution_plan_editor import Action  # noqa: E402 - import after env setup required for test

# isort: on
# Mock the load_registry_data function to use our test data
original_load_registry_data = None


def setup_mock_registry():
    """Setup mock registry data that returns our test data."""
    global original_load_registry_data
    import execution_plan_editor

    original_load_registry_data = execution_plan_editor.load_registry_data

    def mock_load_registry_data(agent_data_dir=None):
        return {
            "success": True,
            "capabilities": [
                {
                    "name": "PV_SEARCH",
                    "description": "Search for PV addresses",
                    "provides": ["PV_ADDRESSES"],
                    "requires": [],
                },
                {
                    "name": "ARCHIVER_DATA_RETRIEVAL",
                    "description": "Retrieve archiver data",
                    "provides": ["ARCHIVER_DATA"],
                    "requires": ["PV_ADDRESSES", "TIME_RANGE"],
                },
            ],
            "context_types": [
                {"type_name": "PV_ADDRESSES", "description": "PV address list"},
                {"type_name": "TIME_RANGE", "description": "Time range specification"},
                {"type_name": "ARCHIVER_DATA", "description": "Historical archiver data"},
            ],
            "templates": [],
        }

    execution_plan_editor.load_registry_data = mock_load_registry_data


def teardown_mock_registry():
    """Restore original registry loading."""
    global original_load_registry_data
    if original_load_registry_data:
        import execution_plan_editor

        execution_plan_editor.load_registry_data = original_load_registry_data


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

    def __init__(self, test_scenario="normal"):
        self.calls = []
        self.test_scenario = test_scenario

    async def __call__(self, event):
        self.calls.append(event)
        print(f"📞 CALL: {event['type']}")

        if event["type"] == "execute":
            code = event["data"].get("code", "")
            print(f"   JavaScript code length: {len(code)} chars")
            print(f"   First 100 chars: {code[:100]}...")

            # Simulate different user actions
            if self.test_scenario == "save":
                return {
                    "action": "save",
                    "plan": [
                        {
                            "context_key": "pv_search",
                            "capability": "PV_SEARCH",
                            "task_objective": "Find PV addresses",
                            "expected_output": "PV_ADDRESSES",
                            "parameters": None,
                            "inputs": [],
                        },
                        {
                            "context_key": "archiver_retrieval",
                            "capability": "ARCHIVER_DATA_RETRIEVAL",
                            "task_objective": "Retrieve archiver data",
                            "expected_output": "ARCHIVER_DATA",
                            "parameters": None,
                            "inputs": [{"PV_ADDRESSES": "pv_search"}],
                        },
                    ],
                }
            elif self.test_scenario == "editor_opened":
                return {"action": "editor_opened", "mode": "normal"}
            elif self.test_scenario == "approval_review":
                return {"action": "editor_opened", "mode": "approval_review"}
            elif self.test_scenario == "save_as_is":
                return {"action": "save_as_is"}
            elif self.test_scenario == "save_modified":
                return {
                    "action": "save_modified",
                    "plan_data": {
                        "steps": [
                            {
                                "context_key": "modified_step",
                                "capability": "PV_SEARCH",
                                "task_objective": "Modified task",
                                "expected_output": "PV_ADDRESSES",
                                "parameters": None,
                                "inputs": [],
                            }
                        ]
                    },
                }
            elif self.test_scenario == "error":
                return {"action": "error", "message": "Simulated error"}

        return None


def create_mock_user(user_id="test_user", email="testuser@example.com"):
    """Create a mock user object."""
    return {"id": user_id, "name": "Test User", "email": email, "valves": None}


def create_mock_registry_data():
    """Create mock registry data for testing."""
    registry_dir = Path(test_dir) / ".." / "registry_exports"
    registry_dir.mkdir(parents=True, exist_ok=True)

    registry_data = {
        "capabilities": [
            {
                "name": "PV_SEARCH",
                "description": "Search for PV addresses",
                "provides": ["PV_ADDRESSES"],
                "requires": [],
            },
            {
                "name": "ARCHIVER_DATA_RETRIEVAL",
                "description": "Retrieve archiver data",
                "provides": ["ARCHIVER_DATA"],
                "requires": ["PV_ADDRESSES", "TIME_RANGE"],
            },
        ],
        "context_types": [
            {"type_name": "PV_ADDRESSES", "description": "PV address list"},
            {"type_name": "TIME_RANGE", "description": "Time range specification"},
            {"type_name": "ARCHIVER_DATA", "description": "Historical archiver data"},
        ],
        "templates": [
            {
                "name": "Simple Search",
                "description": "Basic PV search template",
                "steps": [
                    {
                        "context_key": "pv_search",
                        "capability": "PV_SEARCH",
                        "task_objective": "Find PVs",
                        "expected_output": "PV_ADDRESSES",
                        "parameters": None,
                        "inputs": [],
                    }
                ],
            }
        ],
    }

    registry_file = registry_dir / "registry_export.json"
    with open(registry_file, "w") as f:
        json.dump(registry_data, f, indent=2)

    print(f"✅ Created mock registry data at: {registry_file}")


async def test_basic_editor_open():
    """Test basic editor opening."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Editor Opening")
    print("=" * 80)

    create_mock_registry_data()

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="editor_opened")
    user = create_mock_user()

    result = await action.action(
        body={}, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print(f"✅ Total events emitted: {len(emitter.events)}")
    print(f"✅ Total calls made: {len(caller.calls)}")


async def test_save_execution_plan():
    """Test saving an execution plan."""
    print("\n" + "=" * 80)
    print("TEST 2: Save Execution Plan")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="save")
    user = create_mock_user()

    result = await action.action(
        body={}, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")

    # Check if plan file was created
    user_plans_dir = action._get_user_plans_directory("testuser")
    if user_plans_dir.exists():
        plan_files = list(user_plans_dir.glob("execution_plan_*.json"))
        print(f"✅ Plan files created: {len(plan_files)}")
        if plan_files:
            with open(plan_files[0], "r") as f:
                plan_data = json.load(f)
                print(f"✅ Plan has {len(plan_data.get('steps', []))} steps")
    else:
        print("⚠️  No plan directory created")


async def test_plan_validation():
    """Test plan validation."""
    print("\n" + "=" * 80)
    print("TEST 3: Plan Validation")
    print("=" * 80)

    action = Action()

    # Valid plan
    valid_plan = [
        {
            "context_key": "step1",
            "capability": "PV_SEARCH",
            "task_objective": "Find PVs",
            "expected_output": "PV_ADDRESSES",
            "parameters": None,
            "inputs": [],
        }
    ]

    # Invalid plans
    invalid_plans = [
        ([], "Empty plan"),
        (
            [{"context_key": "step1", "capability": "UNKNOWN_CAP"}],
            "Unknown capability",
        ),
        (
            [
                {
                    "context_key": "step1",
                    "capability": "PV_SEARCH",
                    "task_objective": "",
                    "expected_output": "PV_ADDRESSES",
                }
            ],
            "Missing task objective",
        ),
    ]

    # Test valid plan
    result = action._validate_plan(valid_plan)
    if result["is_valid"]:
        print("✅ Valid plan passed validation")
    else:
        print(f"❌ Valid plan failed: {result['errors']}")

    # Test invalid plans
    for plan, description in invalid_plans:
        result = action._validate_plan(plan)
        if not result["is_valid"]:
            print(f"✅ Correctly rejected: {description}")
        else:
            print(f"❌ Incorrectly accepted: {description}")


async def test_approval_review_mode():
    """Test approval review mode."""
    print("\n" + "=" * 80)
    print("TEST 4: Approval Review Mode")
    print("=" * 80)

    # Create a pending plan
    execution_plans_dir = Path(test_dir) / "execution_plans"
    pending_plans_dir = execution_plans_dir / "pending_plans"
    pending_plans_dir.mkdir(parents=True, exist_ok=True)

    pending_plan = {
        "__metadata__": {
            "original_task": "Test task",
            "context_key": "test_context",
            "created_at": "2025-01-01T12:00:00",
        },
        "steps": [
            {
                "context_key": "pv_search",
                "capability": "PV_SEARCH",
                "task_objective": "Find PVs",
                "expected_output": "PV_ADDRESSES",
                "parameters": None,
                "inputs": [],
            }
        ],
    }

    pending_file = pending_plans_dir / "pending_execution_plan.json"
    with open(pending_file, "w") as f:
        json.dump(pending_plan, f, indent=2)

    print(f"✅ Created pending plan at: {pending_file}")

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="approval_review")
    user = create_mock_user()

    result = await action.action(
        body={}, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print("\n✅ Approval review mode tested")
    print(f"✅ Action completed. Result: {result}")


async def test_context_extraction():
    """Test agent context extraction from messages."""
    print("\n" + "=" * 80)
    print("TEST 5: Context Extraction from Messages")
    print("=" * 80)

    action = Action()

    # Mock messages with agent context
    messages = [
        {
            "role": "assistant",
            "content": "Here's the context",
            "info": {
                "als_assistant_agent_context": {
                    "total_context_items": 2,
                    "context_data": {
                        "PV_ADDRESSES": {
                            "pv_list_1": {
                                "type": "PV Addresses",
                                "description": "List of PVs",
                            }
                        },
                        "TIME_RANGE": {
                            "time_1": {
                                "type": "Time Range",
                                "description": "Time range",
                            }
                        },
                    },
                }
            },
        }
    ]

    context_summary = action.extract_context_summary_from_messages(messages)
    if context_summary:
        print("✅ Successfully extracted agent context")
        print(f"   Total items: {context_summary.get('total_context_items', 0)}")

        available_keys = action.extract_available_context_keys(context_summary)
        print(f"✅ Extracted {len(available_keys)} context keys")
        for ctx in available_keys:
            print(f" - {ctx['contextKey']}: {ctx['contextType']}")
    else:
        print("❌ Failed to extract agent context")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪" * 40)
    print("EXECUTION PLAN EDITOR TEST SUITE")
    print("🧪" * 40)
    print(f"📁 Using temporary test directory: {test_dir}")
    setup_mock_registry()
    try:
        await test_basic_editor_open()
        await test_save_execution_plan()
        await test_plan_validation()
        await test_approval_review_mode()
        await test_context_extraction()

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
        # Cleanup
        import shutil

        print(f"\n🧹 Cleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)
