"""Check token usage values in JSONL - analyze by turn."""

import json
from pathlib import Path

FILE_PATH = Path("/Users/sagar/.claude/projects/-Users-sagar-work-all-things-quickcall-quickcall-supertrace/f0fa7faf-f147-4745-bd3d-2e33a785167c.jsonl")


def main():
    if not FILE_PATH.exists():
        print(f"File not found: {FILE_PATH}")
        return

    print("=== Token Usage Analysis by Turn ===\n")

    # Load all entries
    entries = []
    with open(FILE_PATH, 'r') as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue

    # Analyze by turn (user prompt -> assistant responses)
    turn = 0
    i = 0
    while i < len(entries):
        entry = entries[i]

        if entry.get('type') == 'user':
            content = entry.get('message', {}).get('content')
            # Skip tool results
            is_tool_result = isinstance(content, list) and any(
                isinstance(c, dict) and c.get('type') == 'tool_result'
                for c in content
            )
            if not is_tool_result:
                turn += 1
                if turn <= 5:  # First 5 turns
                    print(f"=== Turn {turn} ===")

                    # Collect all assistant responses until next user prompt
                    j = i + 1
                    assistant_count = 0
                    total_output = 0
                    last_input = 0

                    while j < len(entries):
                        e = entries[j]
                        if e.get('type') == 'user':
                            c = e.get('message', {}).get('content')
                            is_tr = isinstance(c, list) and any(
                                isinstance(x, dict) and x.get('type') == 'tool_result'
                                for x in c
                            )
                            if not is_tr:
                                break  # Next user turn
                        if e.get('type') == 'assistant':
                            assistant_count += 1
                            usage = e.get('message', {}).get('usage', {})
                            out = usage.get('output_tokens', 0)
                            total_output += out
                            last_input = (
                                usage.get('input_tokens', 0) +
                                usage.get('cache_read_input_tokens', 0) +
                                usage.get('cache_creation_input_tokens', 0)
                            )
                            print(f"  Assistant #{assistant_count}: out={out}, input_total={last_input}")
                        j += 1

                    print(f"  TURN TOTALS: {assistant_count} assistant msgs, output_sum={total_output}, last_input={last_input}")
                    print()
        i += 1

    print(f"Total turns: {turn}")


if __name__ == "__main__":
    main()
