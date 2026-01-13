"""Check empty user prompts in ai-demo-app session."""

import json
from pathlib import Path

FILE_PATH = Path("/Users/sagar/.claude/projects/-Users-sagar-work-all-things-quickcall-ai-demo-app/52bb21ef-8e9f-4b2e-afc0-ad46860c4f79.jsonl")


def main():
    if not FILE_PATH.exists():
        print(f"File not found: {FILE_PATH}")
        return

    prompt_idx = 0

    with open(FILE_PATH, 'r') as f:
        for i, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                if data.get('type') == 'user':
                    content = data.get('message', {}).get('content')

                    # Check if tool_result
                    is_tool_result = isinstance(content, list) and any(
                        isinstance(c, dict) and c.get('type') == 'tool_result'
                        for c in content
                    )

                    if not is_tool_result:
                        prompt_idx += 1

                        print(f"\n=== Prompt {prompt_idx} (line {i}) ===")
                        print(f"Content type: {type(content).__name__}")

                        if isinstance(content, str):
                            if len(content.strip()) < 20:
                                print(f"Content: {repr(content)}")
                            else:
                                print(f"Content (first 100): {content[:100]}")
                        elif isinstance(content, list):
                            print(f"Content blocks: {len(content)}")
                            for j, block in enumerate(content[:5]):
                                if isinstance(block, dict):
                                    block_type = block.get('type')
                                    print(f"  Block {j}: type={block_type}")
                                    if block_type == 'text':
                                        text = block.get('text', '')
                                        print(f"    text: {repr(text[:200]) if len(text) > 200 else repr(text)}")
                                else:
                                    print(f"  Block {j}: {type(block)}")
                        else:
                            print(f"Content: {content}")

                        # Print all top-level keys (might have answer info elsewhere)
                        print(f"Top-level keys: {list(data.keys())}")

                        # Check for specific fields that might contain user response
                        for key in ['answer', 'selectedOption', 'userResponse', 'toolUseResult',
                                   'questionResponse', 'permissionResponse', 'input']:
                            if key in data:
                                print(f"  {key}: {data[key]}")

            except json.JSONDecodeError as e:
                print(f"JSON error line {i}: {e}")
                continue


if __name__ == "__main__":
    main()
