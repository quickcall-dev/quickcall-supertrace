# Token Usage Tracking

How SuperTrace captures and displays Claude Code token consumption.

## Overview

Token usage is critical for:
- **Cost monitoring** - Understanding API spend
- **Context management** - Knowing when you're approaching limits
- **Performance optimization** - Identifying inefficient prompts

SuperTrace captures token usage from Claude Code sessions and displays it in real-time.

## How Token Usage is Captured

### Source: Transcript File

Claude Code writes all interactions to JSONL transcript files. Each assistant message includes usage metadata:

```json
{
  "type": "assistant",
  "message": {
    "content": [...],
    "usage": {
      "input_tokens": 1500,
      "output_tokens": 350,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 1200
    }
  }
}
```

### Capture Flow

```
1. Claude finishes responding → Stop hook triggered
2. Handler reads transcript JSONL file
3. Parses all entries, extracts usage from assistant messages
4. Aggregates totals across the session
5. Sends with event data to server
6. Frontend displays below each response
```

## Token Types

| Token Type | Description | Cost Impact |
|------------|-------------|-------------|
| `input_tokens` | Tokens in the prompt sent to Claude | Full price |
| `output_tokens` | Tokens in Claude's response | Full price |
| `cache_creation_input_tokens` | Tokens used to create cache | 25% extra |
| `cache_read_input_tokens` | Tokens read from cache | 90% discount |

### Cache Tokens Explained

Claude Code uses **prompt caching** to reduce costs and latency:
- First time a context is used → `cache_creation_input_tokens` (slight premium)
- Subsequent uses → `cache_read_input_tokens` (90% cheaper!)

This is why you'll often see large `cache_read` values - it means you're saving money.

## Display in SuperTrace

Token usage appears below each assistant response:

```
┌────────────────────────────────────────────────────────┐
│ [Assistant's response text...]                         │
│                                                        │
│ 10:32:45 AM   1.5K in / 350 out (1.2K cached)        │
└────────────────────────────────────────────────────────┘
```

### Reading the Display

- **X.XK in** - Input tokens (what you sent)
- **X.XK out** - Output tokens (Claude's response)
- **(X.XK cached)** - Tokens read from cache (green = savings!)

## Alternative: Status Line

Claude Code also provides real-time token usage via the **status line** feature:

```json
{
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 15000,
      "output_tokens": 3500,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 12000
    }
  }
}
```

This shows **cumulative session usage**, not per-message usage.

### Configure Status Line

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline-command.sh"
  }
}
```

Example script to show context window percentage:

```bash
#!/bin/bash
input=$(cat)

context_info=$(echo "$input" | jq '.context_window')
current_usage=$(echo "$context_info" | jq '.current_usage')

if [[ "$current_usage" != "null" ]]; then
    input_tokens=$(echo "$current_usage" | jq '.input_tokens // 0')
    cache_read=$(echo "$current_usage" | jq '.cache_read_input_tokens // 0')
    window_size=$(echo "$context_info" | jq '.context_window_size')

    total=$((input_tokens + cache_read))
    if [[ $window_size -gt 0 ]]; then
        pct=$((total * 100 / window_size))
        echo "Context: ${pct}%"
    fi
fi
```

## Third-Party Tools

For more detailed usage analysis, consider these tools:

### ccusage

CLI tool for analyzing Claude Code usage from local JSONL files:

```bash
# Install
npm install -g ccusage

# Analyze usage
ccusage --monthly
ccusage --session
ccusage --5hour  # Claude's billing windows
```

[GitHub: ryoppippi/ccusage](https://github.com/ryoppippi/ccusage)

### Claude-Code-Usage-Monitor

Real-time terminal monitoring with predictions:

- Token consumption tracking
- Burn rate analysis
- Intelligent predictions about session limits

[GitHub: Maciek-roboblog/Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor)

### Vibe Meter

macOS toolbar integration for token tracking:

[Article: Claude Code Token Usage on Mac Toolbar](https://preslav.me/2025/08/04/put-claude-code-token-usage-macos-toolbar/)

## Enterprise: Analytics API

For organizations, Anthropic provides a **Claude Code Analytics API**:

```
GET /v1/organizations/usage_report/claude_code
```

Features:
- Organization-wide usage reports
- Breakdown by Claude model
- Cost analysis
- Custom date ranges

Requires Admin API key (`sk-ant-admin...`).

[Anthropic: Claude Code Analytics API](https://docs.anthropic.com/en/api/claude-code-analytics-api)

## Cost Estimation

Approximate pricing (check [Anthropic pricing](https://www.anthropic.com/pricing) for current rates):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude Sonnet 4 | $3.00 | $15.00 |
| Claude Opus 4 | $15.00 | $75.00 |
| Claude Haiku | $0.25 | $1.25 |

**Cache discount:** 90% off input tokens when reading from cache.

## Tips for Reducing Token Usage

1. **Use smaller context** - Don't include entire files if not needed
2. **Leverage caching** - Repeated prompts benefit from cache
3. **Use Haiku for simple tasks** - 60x cheaper than Opus
4. **Clear conversation periodically** - `/clear` starts fresh
5. **Use `/compact`** - Summarizes long conversations

## Limitations

### What SuperTrace Captures

- Token usage at each `Stop` event
- Aggregated totals from transcript
- Per-response breakdown in UI

### What SuperTrace Doesn't Capture

- Real-time streaming token counts
- Cost in USD (calculated client-side)
- Usage across multiple Claude Code instances
- API-level usage (only CLI/IDE usage)

## References

- [Claude Code Costs Documentation](https://code.claude.com/docs/en/costs)
- [ccusage - Token Usage CLI](https://github.com/ryoppippi/ccusage)
- [Claude Code Analytics API](https://docs.anthropic.com/en/api/claude-code-analytics-api)
- [Anthropic Pricing](https://www.anthropic.com/pricing)
- [Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)

## See Also

- [Hook Events Reference](../reference/hook-events.md) - Token usage in transcript format
- [Architecture](../concepts/architecture.md) - Data flow overview
- [Configure Hooks](configure-hooks.md) - Hook setup
