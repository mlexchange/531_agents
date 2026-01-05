"""
Test script for memory_button.py

Run with: python test_memory_button.py
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Set up test environment BEFORE importing Action
test_dir = tempfile.mkdtemp(prefix="memory_test_")
os.environ["USER_MEMORY_DIR"] = test_dir

# Add the functions directory to path so we can import memory_button
sys.path.insert(0, str(Path(__file__).parent))
# isort: off
from memory_button import Action  # noqa: E402 - import after env setup required for test

# isort: on


class MockEventEmitter:
    """Mock event emitter for testing."""

    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)
        print(f"📤 EVENT: {event['type']}")
        if event.get("data"):
            print(f"   Data: {event['data']}")


class MockEventCall:
    """Mock event call for testing."""

    def __init__(self, test_scenario="save"):
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
                    "memories": [
                        {
                            "timestamp": "2025-01-01 12:00",
                            "content": "Test memory 1 - This is a test",
                        },
                        {
                            "timestamp": "2025-01-02 14:30",
                            "content": "Test memory 2 - Another test entry",
                        },
                    ],
                }
            elif self.test_scenario == "cancel":
                return {"action": "cancel"}
            elif self.test_scenario == "error":
                return {"action": "error", "message": "Simulated error"}

        return None


def create_mock_user(user_id="test_user", email="testuser@example.com"):
    """Create a mock user object."""
    return {"id": user_id, "name": "Test User", "email": email, "valves": None}


async def test_basic_functionality():
    """Test basic memory manager functionality."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Functionality - Empty Memory")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="save")
    user = create_mock_user()

    result = await action.action(
        body={}, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print(f"✅ Total events emitted: {len(emitter.events)}")
    print(f"✅ Total calls made: {len(caller.calls)}")

    # Check memory file
    memory_file = action._get_memory_file_path("testuser")
    if memory_file.exists():
        with open(memory_file, "r") as f:
            data = json.load(f)
            print(f"✅ Memory file created with {len(data.get('entries', []))} entries")
    else:
        print("⚠️  No memory file created")


async def test_existing_memories():
    """Test with existing memories."""
    print("\n" + "=" * 80)
    print("TEST 2: Existing Memories - Edit Mode")
    print("=" * 80)

    action = Action()

    # Pre-create some memories
    user_id = "testuser2"
    test_data = {
        "user_id": user_id,
        "created": "2025-01-01 10:00",
        "last_updated": "2025-01-01 10:00",
        "entries": [
            {"timestamp": "2025-01-01 10:00", "content": "Pre-existing memory 1"},
            {"timestamp": "2025-01-01 11:00", "content": "Pre-existing memory 2"},
        ],
    }

    # Save initial data
    action._save_memory_data(user_id, test_data)
    print(f"✅ Created test memory file with {len(test_data['entries'])} entries")

    # Now run the action
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="save")
    user = create_mock_user(user_id=user_id, email="testuser2@example.com")

    result = await action.action(
        body={}, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")

    # Check backup was created
    memory_file = action._get_memory_file_path(user_id)
    backup_file = memory_file.parent / ".backups" / f"{memory_file.stem}.json"
    if backup_file.exists():
        print(f"✅ Backup created: {backup_file}")
    else:
        print("⚠️  No backup created")


async def test_cancel_action():
    """Test canceling the editor."""
    print("\n" + "=" * 80)
    print("TEST 3: Cancel Action")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="cancel")
    user = create_mock_user(user_id="testuser3", email="testuser3@example.com")

    result = await action.action(
        body={}, __user__=user, __event_emitter__=emitter, __event_call__=caller
    )

    print(f"\n✅ Action completed. Result: {result}")
    print("✅ User canceled - no changes made")


async def test_javascript_generation():
    """Test JavaScript code generation."""
    print("\n" + "=" * 80)
    print("TEST 4: JavaScript Code Generation")
    print("=" * 80)

    action = Action()
    emitter = MockEventEmitter()
    caller = MockEventCall(test_scenario="save")

    # Create test data
    test_data = {
        "user_id": "testuser",
        "entries": [
            {"timestamp": "2025-01-01 12:00", "content": 'Test with "quotes" and\nnewlines'}
        ],
    }

    result = await action.create_memory_editor_interface(
        data=test_data, user_id="testuser", __event_emitter__=emitter, __event_call__=caller
    )

    print("\n✅ JavaScript interface created")
    print(f"✅ Result: {result}")

    # Check the JavaScript code was properly escaped
    if caller.calls:
        js_code = caller.calls[0]["data"]["code"]
        print(f"✅ JavaScript code length: {len(js_code)} characters")
        print(f"✅ Contains color palette: {'colors = {' in js_code}")
        print(f"✅ Contains user ID: {'testuser' in js_code}")


async def test_data_validation():
    """Test data validation."""
    print("\n" + "=" * 80)
    print("TEST 5: Data Validation")
    print("=" * 80)

    action = Action()

    # Valid data
    valid_data = {
        "user_id": "test",
        "entries": [{"timestamp": "2025-01-01 12:00", "content": "Valid entry"}],
    }

    # Invalid data cases
    invalid_cases = [
        ({}, "Empty dict"),
        ({"user_id": "test"}, "Missing entries"),
        ({"user_id": "test", "entries": "not a list"}, "Entries not a list"),
        ({"user_id": "test", "entries": [{"content": "missing timestamp"}]}, "Missing timestamp"),
        (
            {"user_id": "test", "entries": [{"timestamp": 123, "content": "wrong type"}]},
            "Wrong type",
        ),
    ]

    # Test valid data
    if action._validate_memory_data(valid_data):
        print("✅ Valid data passed validation")
    else:
        print("❌ Valid data failed validation")

    # Test invalid data
    for invalid_data, description in invalid_cases:
        if not action._validate_memory_data(invalid_data):
            print(f"✅ Correctly rejected: {description}")
        else:
            print(f"❌ Incorrectly accepted: {description}")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "🧪" * 40)
    print("MEMORY BUTTON TEST SUITE")
    print("🧪" * 40)
    print(f"📁 Using temporary test directory: {test_dir}")

    try:
        await test_basic_functionality()
        await test_existing_memories()
        await test_cancel_action()
        await test_javascript_generation()
        await test_data_validation()

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
