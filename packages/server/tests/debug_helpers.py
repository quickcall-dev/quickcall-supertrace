"""
Debug helpers for investigating data issues.

Provides reusable utilities for inspecting sessions, prompts, tokens,
and database state. Use these instead of writing one-off scripts.

Usage:
    from tests.debug_helpers import DebugHelper

    # Quick inspection of current session
    dh = DebugHelper()
    dh.inspect_session("session-id-here")

    # Or use CLI:
    python -m tests.debug_helpers --session <session-id> --prompts 62-67
"""

import asyncio
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Database path
DB_PATH = Path.home() / ".quickcall-supertrace" / "data.db"

# Default session JSONL directory
JSONL_BASE = Path.home() / ".claude" / "projects"


@dataclass
class PromptInfo:
    """Info about a user prompt."""
    index: int
    db_id: int
    uuid: str
    line_number: int
    timestamp: str
    text: str
    is_tool_result: bool


@dataclass
class TokenSummary:
    """Token usage summary."""
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_create: int
    total_context: int


class DebugHelper:
    """Helper class for debugging data issues."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Session inspection
    # =========================================================================

    def list_sessions(self, limit: int = 10) -> list[dict]:
        """List recent sessions with message counts."""
        conn = self._get_conn()
        cursor = conn.execute('''
            SELECT
                session_id,
                COUNT(*) as msg_count,
                SUM(CASE WHEN msg_type = 'user' AND is_tool_result = 0 THEN 1 ELSE 0 END) as prompt_count,
                SUM(CASE WHEN msg_type = 'assistant' THEN input_tokens + cache_read_tokens + cache_create_tokens ELSE 0 END) as total_context,
                SUM(CASE WHEN msg_type = 'assistant' THEN output_tokens ELSE 0 END) as total_output,
                MIN(timestamp) as first_ts,
                MAX(timestamp) as last_ts
            FROM messages
            GROUP BY session_id
            ORDER BY last_ts DESC
            LIMIT ?
        ''', (limit,))

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row['session_id'],
                'messages': row['msg_count'],
                'prompts': row['prompt_count'],
                'total_context': row['total_context'] or 0,
                'total_output': row['total_output'] or 0,
                'first': row['first_ts'],
                'last': row['last_ts'],
            })
        conn.close()
        return sessions

    def inspect_session(self, session_id: str) -> dict:
        """Get detailed info about a session."""
        conn = self._get_conn()

        # Basic counts
        cursor = conn.execute('''
            SELECT
                msg_type,
                COUNT(*) as count,
                SUM(input_tokens) as input_tok,
                SUM(output_tokens) as output_tok,
                SUM(cache_read_tokens) as cache_read,
                SUM(cache_create_tokens) as cache_create,
                SUM(tool_use_count) as tools
            FROM messages
            WHERE session_id = ?
            GROUP BY msg_type
        ''', (session_id,))

        by_type = {}
        for row in cursor.fetchall():
            by_type[row['msg_type']] = {
                'count': row['count'],
                'input_tokens': row['input_tok'] or 0,
                'output_tokens': row['output_tok'] or 0,
                'cache_read': row['cache_read'] or 0,
                'cache_create': row['cache_create'] or 0,
                'tools': row['tools'] or 0,
            }

        # User prompts (non-tool-result)
        cursor = conn.execute('''
            SELECT COUNT(*) FROM messages
            WHERE session_id = ? AND msg_type = 'user' AND is_tool_result = 0
        ''', (session_id,))
        prompt_count = cursor.fetchone()[0]

        # Check for duplicates
        cursor = conn.execute('''
            SELECT line_number, COUNT(*) as cnt
            FROM messages
            WHERE session_id = ?
            GROUP BY line_number
            HAVING cnt > 1
        ''', (session_id,))
        duplicates = cursor.fetchall()

        conn.close()

        return {
            'session_id': session_id,
            'by_type': by_type,
            'user_prompts': prompt_count,
            'duplicate_lines': len(duplicates),
            'duplicate_sample': [{'line': d['line_number'], 'count': d['cnt']} for d in duplicates[:5]],
        }

    # =========================================================================
    # Prompt inspection
    # =========================================================================

    def get_prompts(
        self,
        session_id: str,
        start: int = 1,
        end: int = 10
    ) -> list[PromptInfo]:
        """Get user prompts by index range (1-indexed)."""
        conn = self._get_conn()

        cursor = conn.execute('''
            SELECT id, uuid, line_number, timestamp, prompt_text, is_tool_result
            FROM messages
            WHERE session_id = ? AND msg_type = 'user' AND is_tool_result = 0
            ORDER BY timestamp ASC
        ''', (session_id,))

        prompts = []
        for i, row in enumerate(cursor.fetchall(), 1):
            if start <= i <= end:
                prompts.append(PromptInfo(
                    index=i,
                    db_id=row['id'],
                    uuid=row['uuid'],
                    line_number=row['line_number'],
                    timestamp=row['timestamp'],
                    text=(row['prompt_text'] or '')[:100],
                    is_tool_result=bool(row['is_tool_result']),
                ))

        conn.close()
        return prompts

    def compare_prompt_sources(
        self,
        session_id: str,
        prompt_indices: list[int]
    ) -> list[dict]:
        """Compare prompt data between DB and JSONL."""
        # Get from DB
        db_prompts = {p.index: p for p in self.get_prompts(session_id, 1, 1000)}

        # Find JSONL file
        jsonl_file = self._find_jsonl_file(session_id)
        if not jsonl_file:
            return [{'error': f'JSONL file not found for session {session_id}'}]

        # Get from JSONL
        jsonl_prompts = self._parse_jsonl_prompts(jsonl_file)

        results = []
        for idx in prompt_indices:
            result = {'index': idx}

            if idx in db_prompts:
                p = db_prompts[idx]
                result['db'] = {
                    'uuid': p.uuid[:12],
                    'line': p.line_number,
                    'text': p.text[:50],
                }
            else:
                result['db'] = None

            if idx <= len(jsonl_prompts):
                p = jsonl_prompts[idx - 1]
                result['jsonl'] = {
                    'uuid': p['uuid'][:12],
                    'line': p['line'],
                    'text': p['text'][:50],
                }
            else:
                result['jsonl'] = None

            result['match'] = (
                result['db'] is not None and
                result['jsonl'] is not None and
                result['db']['uuid'] == result['jsonl']['uuid']
            )

            results.append(result)

        return results

    # =========================================================================
    # Token inspection
    # =========================================================================

    def get_token_summary(self, session_id: str) -> TokenSummary:
        """Get token usage summary for a session."""
        conn = self._get_conn()

        cursor = conn.execute('''
            SELECT
                SUM(input_tokens) as input_tok,
                SUM(output_tokens) as output_tok,
                SUM(cache_read_tokens) as cache_read,
                SUM(cache_create_tokens) as cache_create
            FROM messages
            WHERE session_id = ? AND msg_type = 'assistant'
        ''', (session_id,))

        row = cursor.fetchone()
        conn.close()

        input_tok = row['input_tok'] or 0
        cache_read = row['cache_read'] or 0
        cache_create = row['cache_create'] or 0

        return TokenSummary(
            input_tokens=input_tok,
            output_tokens=row['output_tok'] or 0,
            cache_read=cache_read,
            cache_create=cache_create,
            total_context=input_tok + cache_read + cache_create,
        )

    def get_tokens_by_prompt(
        self,
        session_id: str,
        prompt_index: int
    ) -> dict:
        """Get token breakdown for a specific prompt's turn."""
        # This requires grouping assistant messages by preceding user prompt
        # For now, return a simplified version
        conn = self._get_conn()

        # Get all messages ordered by timestamp
        cursor = conn.execute('''
            SELECT msg_type, input_tokens, output_tokens,
                   cache_read_tokens, cache_create_tokens, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,))

        messages = cursor.fetchall()
        conn.close()

        # Group by prompt
        current_prompt = 0
        prompt_tokens = defaultdict(lambda: {
            'input': 0, 'output': 0, 'cache_read': 0, 'cache_create': 0
        })

        for msg in messages:
            if msg['msg_type'] == 'user':
                # Would need to check is_tool_result here
                current_prompt += 1
            elif msg['msg_type'] == 'assistant' and current_prompt > 0:
                prompt_tokens[current_prompt]['input'] += msg['input_tokens'] or 0
                prompt_tokens[current_prompt]['output'] += msg['output_tokens'] or 0
                prompt_tokens[current_prompt]['cache_read'] += msg['cache_read_tokens'] or 0
                prompt_tokens[current_prompt]['cache_create'] += msg['cache_create_tokens'] or 0

        return dict(prompt_tokens.get(prompt_index, {}))

    # =========================================================================
    # Tool inspection
    # =========================================================================

    def get_tool_summary(self, session_id: str) -> dict:
        """Get tool usage summary for a session."""
        conn = self._get_conn()

        cursor = conn.execute('''
            SELECT tool_names, tool_use_count
            FROM messages
            WHERE session_id = ? AND msg_type = 'assistant' AND tool_use_count > 0
        ''', (session_id,))

        tool_counts = defaultdict(int)
        total_tools = 0

        for row in cursor.fetchall():
            total_tools += row['tool_use_count'] or 0
            if row['tool_names']:
                tools = json.loads(row['tool_names'])
                for t in tools:
                    tool_counts[t] += 1

        conn.close()

        return {
            'total_tools': total_tools,
            'by_tool': dict(sorted(tool_counts.items(), key=lambda x: -x[1])),
        }

    # =========================================================================
    # JSONL extraction
    # =========================================================================

    def extract_examples(
        self,
        session_id: Optional[str] = None,
        file_path: Optional[Path] = None
    ) -> dict:
        """
        Extract condensed examples of each message type from a JSONL file.

        Returns dict with keys: user_prompt, tool_result_success, tool_result_error,
        assistant_text, assistant_tool, system, queue_operation
        """
        if file_path is None:
            if session_id:
                file_path = self._find_jsonl_file(session_id)
            else:
                # Find most recent
                files = sorted(
                    JSONL_BASE.rglob("*.jsonl"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                file_path = files[0] if files else None

        if not file_path or not file_path.exists():
            return {'error': 'No JSONL file found'}

        examples = {
            'user_prompt': None,
            'tool_result_success': None,
            'tool_result_error': None,
            'assistant_text': None,
            'assistant_tool': None,
            'system': None,
            'queue_operation': None,
        }

        with open(file_path) as f:
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    self._classify_and_store(msg, examples)
                    if all(examples.values()):
                        break
                except json.JSONDecodeError:
                    continue

        return examples

    def _classify_and_store(self, msg: dict, examples: dict):
        """Classify message and store if we don't have that type yet."""
        msg_type = msg.get('type')

        if msg_type == 'user':
            content = msg.get('message', {}).get('content')
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'tool_result':
                        if c.get('is_error'):
                            if not examples['tool_result_error']:
                                examples['tool_result_error'] = msg
                        else:
                            if not examples['tool_result_success']:
                                result_content = c.get('content', '')
                                # Skip if content is too complex
                                if isinstance(result_content, str) and len(result_content) < 200:
                                    examples['tool_result_success'] = msg
                        return
            # Regular user prompt
            if not examples['user_prompt']:
                if isinstance(content, str) and len(content) < 100 and not content.startswith('<'):
                    examples['user_prompt'] = msg

        elif msg_type == 'assistant':
            content = msg.get('message', {}).get('content', [])
            has_tool = any(c.get('type') == 'tool_use' for c in content if isinstance(c, dict))
            if has_tool and not examples['assistant_tool']:
                examples['assistant_tool'] = msg
            elif not has_tool and not examples['assistant_text']:
                examples['assistant_text'] = msg

        elif msg_type == 'system' and not examples['system']:
            examples['system'] = msg

        elif msg_type == 'queue-operation' and not examples['queue_operation']:
            examples['queue_operation'] = msg

    def condense_message(self, msg: dict, truncate_uuid: int = 8) -> dict:
        """
        Condense a message for display, truncating UUIDs and long content.

        Useful for documentation and debugging output.
        """
        if not msg:
            return None

        def trunc_uuid(u):
            if u and len(u) > truncate_uuid:
                return u[:truncate_uuid] + '...'
            return u

        result = {
            'type': msg.get('type'),
            'uuid': trunc_uuid(msg.get('uuid')),
        }

        if msg.get('parentUuid'):
            result['parentUuid'] = trunc_uuid(msg.get('parentUuid'))

        msg_type = msg.get('type')

        if msg_type == 'user':
            message = msg.get('message', {})
            content = message.get('content')

            if isinstance(content, str):
                result['message'] = {
                    'role': 'user',
                    'content': content[:80] + ('...' if len(content) > 80 else '')
                }
            elif isinstance(content, list):
                condensed_content = []
                for c in content[:2]:  # Only first 2 blocks
                    if isinstance(c, dict):
                        if c.get('type') == 'tool_result':
                            condensed_content.append({
                                'type': 'tool_result',
                                'tool_use_id': trunc_uuid(c.get('tool_use_id')),
                                'content': (c.get('content', '')[:60] + '...'
                                           if len(c.get('content', '')) > 60 else c.get('content', '')),
                                **({'is_error': True} if c.get('is_error') else {})
                            })
                        elif c.get('type') == 'text':
                            text = c.get('text', '')
                            condensed_content.append({
                                'type': 'text',
                                'text': text[:60] + ('...' if len(text) > 60 else '')
                            })
                result['message'] = {'role': 'user', 'content': condensed_content}

        elif msg_type == 'assistant':
            message = msg.get('message', {})
            content = message.get('content', [])

            condensed_content = []
            for c in content[:3]:  # Only first 3 blocks
                if isinstance(c, dict):
                    if c.get('type') == 'text':
                        text = c.get('text', '')
                        condensed_content.append({
                            'type': 'text',
                            'text': text[:60] + ('...' if len(text) > 60 else '')
                        })
                    elif c.get('type') == 'tool_use':
                        tool_input = c.get('input', {})
                        condensed_input = {}
                        for k, v in list(tool_input.items())[:2]:
                            if isinstance(v, str) and len(v) > 50:
                                v = v[:50] + '...'
                            condensed_input[k] = v
                        condensed_content.append({
                            'type': 'tool_use',
                            'id': trunc_uuid(c.get('id')),
                            'name': c.get('name'),
                            'input': condensed_input
                        })

            result['message'] = {
                'model': message.get('model'),
                'id': trunc_uuid(message.get('id')),
                'role': 'assistant',
                'content': condensed_content,
                'stop_reason': message.get('stop_reason'),
                'usage': message.get('usage', {})
            }

        elif msg_type == 'system':
            result['subtype'] = msg.get('subtype')
            content = msg.get('content', '')
            result['content'] = content[:60] + ('...' if len(content) > 60 else '')
            result['level'] = msg.get('level')

        elif msg_type == 'queue-operation':
            result['operation'] = msg.get('operation')
            result['sessionId'] = trunc_uuid(msg.get('sessionId'))
            content = msg.get('content', '')
            result['content'] = content[:80] + ('...' if len(content) > 80 else '')

        return result

    def print_examples(self, session_id: Optional[str] = None):
        """Print condensed examples of each message type."""
        examples = self.extract_examples(session_id)

        if 'error' in examples:
            print(f"Error: {examples['error']}")
            return

        for name, msg in examples.items():
            print(f"\n{'='*60}")
            print(f"{name.upper()}")
            print(f"{'='*60}")
            if msg:
                condensed = self.condense_message(msg)
                print(json.dumps(condensed, indent=2))
            else:
                print("(no example found)")

    # =========================================================================
    # JSONL helpers
    # =========================================================================

    def _find_jsonl_file(self, session_id: str) -> Optional[Path]:
        """Find JSONL file for a session."""
        for jsonl in JSONL_BASE.rglob(f"*{session_id}*.jsonl"):
            return jsonl
        # Also check for exact match (session ID is the filename)
        for jsonl in JSONL_BASE.rglob(f"{session_id}.jsonl"):
            return jsonl
        return None

    def _parse_jsonl_prompts(self, file_path: Path) -> list[dict]:
        """Parse user prompts from JSONL file."""
        prompts = []

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())

                    if data.get('type') != 'user':
                        continue

                    content = data.get('message', {}).get('content')
                    is_tool_result = isinstance(content, list) and any(
                        isinstance(c, dict) and c.get('type') == 'tool_result'
                        for c in content
                    )

                    if is_tool_result:
                        continue

                    # Extract text
                    text = ''
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '')
                                break

                    prompts.append({
                        'uuid': data.get('uuid', ''),
                        'line': line_num,
                        'timestamp': data.get('timestamp', ''),
                        'text': text,
                    })

                except json.JSONDecodeError:
                    continue

        return prompts

    # =========================================================================
    # Duplicate detection
    # =========================================================================

    def find_duplicates(self, session_id: str) -> dict:
        """Find duplicate messages in a session."""
        conn = self._get_conn()

        # By line number
        cursor = conn.execute('''
            SELECT line_number, COUNT(*) as cnt
            FROM messages
            WHERE session_id = ?
            GROUP BY line_number
            HAVING cnt > 1
            ORDER BY cnt DESC
            LIMIT 10
        ''', (session_id,))
        by_line = [{'line': r['line_number'], 'count': r['cnt']} for r in cursor.fetchall()]

        # By content (same timestamp + text)
        cursor = conn.execute('''
            SELECT timestamp, prompt_text, COUNT(*) as cnt
            FROM messages
            WHERE session_id = ? AND msg_type = 'user' AND prompt_text IS NOT NULL
            GROUP BY timestamp, prompt_text
            HAVING cnt > 1
            LIMIT 10
        ''', (session_id,))
        by_content = [
            {'timestamp': r['timestamp'], 'text': (r['prompt_text'] or '')[:30], 'count': r['cnt']}
            for r in cursor.fetchall()
        ]

        conn.close()

        return {
            'by_line': by_line,
            'by_content': by_content,
        }

    # =========================================================================
    # Transcript file inspection
    # =========================================================================

    def get_transcript_status(self, session_id: str) -> dict:
        """Get transcript file tracking status for a session."""
        conn = self._get_conn()

        cursor = conn.execute('''
            SELECT file_path, file_mtime, file_size,
                   last_line_number, last_byte_offset, first_message_uuid, status
            FROM transcript_files
            WHERE session_id = ?
        ''', (session_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {'error': 'No transcript file tracked for this session'}

        return {
            'file_path': row['file_path'],
            'file_mtime': row['file_mtime'],
            'file_size': row['file_size'],
            'last_line': row['last_line_number'],
            'last_offset': row['last_byte_offset'],
            'first_uuid': row['first_message_uuid'],
            'status': row['status'],
        }

    # =========================================================================
    # Pretty printing
    # =========================================================================

    def print_sessions(self, limit: int = 10):
        """Print list of sessions."""
        sessions = self.list_sessions(limit)
        print(f"\n{'='*70}")
        print(f"{'Session ID':<38} {'Msgs':<8} {'Prompts':<8} {'Context':<12}")
        print(f"{'='*70}")
        for s in sessions:
            print(f"{s['session_id']:<38} {s['messages']:<8} {s['prompts']:<8} {s['total_context']:>10,}")

    def print_session_info(self, session_id: str):
        """Print detailed session info."""
        info = self.inspect_session(session_id)
        print(f"\n{'='*60}")
        print(f"SESSION: {session_id}")
        print(f"{'='*60}")
        print(f"\nUser prompts: {info['user_prompts']}")
        print(f"Duplicate lines: {info['duplicate_lines']}")

        if info['by_type']:
            print(f"\nBy message type:")
            for mtype, stats in info['by_type'].items():
                print(f"  {mtype}: {stats['count']} messages")
                if mtype == 'assistant':
                    ctx = stats['input_tokens'] + stats['cache_read'] + stats['cache_create']
                    print(f"    context: {ctx:,}, output: {stats['output_tokens']:,}, tools: {stats['tools']}")

    def print_prompts(self, session_id: str, start: int = 1, end: int = 10):
        """Print prompts in a range."""
        prompts = self.get_prompts(session_id, start, end)
        print(f"\n{'='*70}")
        print(f"PROMPTS {start}-{end} for session {session_id[:12]}...")
        print(f"{'='*70}")
        print(f"{'#':<4} {'UUID':<14} {'Line':<6} {'Text':<50}")
        print(f"{'-'*70}")
        for p in prompts:
            print(f"{p.index:<4} {p.uuid[:12]:<14} {p.line_number:<6} {p.text[:48]}")


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Debug helper for SuperTrace')
    parser.add_argument('--session', '-s', help='Session ID to inspect')
    parser.add_argument('--list', '-l', action='store_true', help='List recent sessions')
    parser.add_argument('--prompts', '-p', help='Prompt range to show (e.g., 62-67)')
    parser.add_argument('--tokens', '-t', action='store_true', help='Show token summary')
    parser.add_argument('--tools', action='store_true', help='Show tool summary')
    parser.add_argument('--duplicates', '-d', action='store_true', help='Find duplicates')
    parser.add_argument('--transcript', action='store_true', help='Show transcript file status')
    parser.add_argument('--examples', '-e', action='store_true', help='Extract example messages')
    parser.add_argument('--jsonl', help='Path to specific JSONL file')

    args = parser.parse_args()

    dh = DebugHelper()

    if args.list:
        dh.print_sessions()
        return

    if not args.session:
        # Get most recent session
        sessions = dh.list_sessions(1)
        if sessions:
            args.session = sessions[0]['session_id']
            print(f"Using most recent session: {args.session}")
        else:
            print("No sessions found. Run ingestion first.")
            return

    if args.prompts:
        if '-' in args.prompts:
            start, end = map(int, args.prompts.split('-'))
        else:
            start = end = int(args.prompts)
        dh.print_prompts(args.session, start, end)
    elif args.tokens:
        summary = dh.get_token_summary(args.session)
        print(f"\nToken Summary:")
        print(f"  Input tokens:  {summary.input_tokens:,}")
        print(f"  Output tokens: {summary.output_tokens:,}")
        print(f"  Cache read:    {summary.cache_read:,}")
        print(f"  Cache create:  {summary.cache_create:,}")
        print(f"  Total context: {summary.total_context:,}")
    elif args.tools:
        summary = dh.get_tool_summary(args.session)
        print(f"\nTool Summary:")
        print(f"  Total tool uses: {summary['total_tools']}")
        print(f"\n  By tool:")
        for tool, count in summary['by_tool'].items():
            print(f"    {tool}: {count}")
    elif args.duplicates:
        dups = dh.find_duplicates(args.session)
        print(f"\nDuplicates by line: {len(dups['by_line'])}")
        for d in dups['by_line'][:5]:
            print(f"  Line {d['line']}: {d['count']} entries")
        print(f"\nDuplicates by content: {len(dups['by_content'])}")
        for d in dups['by_content'][:5]:
            print(f"  '{d['text']}...': {d['count']} entries")
    elif args.transcript:
        status = dh.get_transcript_status(args.session)
        print(f"\nTranscript Status:")
        for k, v in status.items():
            print(f"  {k}: {v}")
    elif args.examples:
        file_path = Path(args.jsonl) if args.jsonl else None
        dh.print_examples(args.session if not file_path else None)
    else:
        dh.print_session_info(args.session)


if __name__ == '__main__':
    main()
