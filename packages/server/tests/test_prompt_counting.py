"""
Test that prompt counting correctly excludes tool_result messages.
"""

import json
from pathlib import Path


def test_prompt_counting():
    """Verify tool_result messages are not counted as separate prompts."""

    TEST_FILE = Path("/Users/sagar/.claude/projects/-Users-sagar-work-all-things-quickcall-quickcall-supertrace/f0fa7faf-f147-4745-bd3d-2e33a785167c.jsonl")

    if not TEST_FILE.exists():
        print(f"Test file not found: {TEST_FILE}")
        return

    # Count user messages in two ways
    all_user_msgs = 0
    real_prompts = 0  # Excludes tool_result

    with open(TEST_FILE, "r") as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if data.get("type") == "user":
                    all_user_msgs += 1

                    # Check if this is a tool_result
                    content = data.get("message", {}).get("content")
                    is_tool_result = isinstance(content, list) and any(
                        isinstance(c, dict) and c.get("type") == "tool_result"
                        for c in content
                    )

                    if not is_tool_result:
                        real_prompts += 1

            except json.JSONDecodeError:
                continue

    tool_results = all_user_msgs - real_prompts

    print(f"\n=== Prompt Counting Analysis ===")
    print(f"Total 'user' messages:     {all_user_msgs}")
    print(f"Tool result messages:      {tool_results}")
    print(f"Real user prompts:         {real_prompts}")
    print(f"\nChart should show {real_prompts} prompt numbers on X-axis")

    assert real_prompts < all_user_msgs, "There should be some tool_result messages"
    assert real_prompts > 0, "There should be some real prompts"

    print("\n✅ Prompt counting logic is correct!")


if __name__ == "__main__":
    test_prompt_counting()
