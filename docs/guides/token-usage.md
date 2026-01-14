# Token Usage Tracking

How SuperTrace captures and displays token consumption and costs.

## Overview

Token tracking helps with:
- **Cost monitoring** - Understanding API spend
- **Context management** - Knowing when approaching limits
- **Performance optimization** - Identifying inefficient prompts

## How Tokens Are Captured

### Source: JSONL Transcript Files

Claude Code writes token usage to JSONL files. Each assistant message includes:

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
1. Claude Code writes to JSONL file
2. SuperTrace poller detects file change
3. Parser extracts token counts from assistant messages
4. Importer stores in database
5. Metrics system aggregates per-session
6. Frontend displays in analytics panel
```

## Token Types

| Token Type | Description | Cost Impact |
|------------|-------------|-------------|
| `input_tokens` | Tokens in prompt sent to Claude | Full price |
| `output_tokens` | Tokens in Claude's response | Full price |
| `cache_creation_input_tokens` | Tokens used to create cache | 25% extra |
| `cache_read_input_tokens` | Tokens read from cache | 90% discount |

### Cache Tokens

Claude Code uses **prompt caching** to reduce costs:
- First use of context → `cache_creation` (slight premium)
- Subsequent uses → `cache_read` (90% cheaper)

Large `cache_read` values indicate cost savings.

## Display in SuperTrace

### Analytics Panel

The collapsed mini-bar shows:
```
Cost: $0.45  |  Files: 12  |  Net: +347
```

Expanded view shows detailed breakdown:
- Input tokens
- Output tokens
- Cache read tokens
- Estimated cost

### Per-Response Display

Each assistant response shows token usage below:
```
┌────────────────────────────────────────────┐
│ [Assistant's response text...]              │
│                                            │
│ 10:32 AM  1.5K in / 350 out (1.2K cached) │
└────────────────────────────────────────────┘
```

**Reading the display:**
- **X.XK in** - Input tokens sent
- **X.XK out** - Output tokens received
- **(X.XK cached)** - Tokens from cache (savings)

## Cost Estimation

SuperTrace estimates costs using current Claude pricing:

| Cost Type | Rate (per 1M tokens) |
|-----------|---------------------|
| Input | $3.00 |
| Output | $15.00 |
| Cache read | $0.30 (90% off) |
| Cache write | $3.75 (25% extra) |

Check [Anthropic pricing](https://www.anthropic.com/pricing) for current rates.

## Metrics API

Get token metrics via API:

```bash
curl "http://localhost:3456/api/metrics/session/{id}"
```

Response includes:
```json
{
  "by_category": {
    "tokens": {
      "estimated_cost": {"value": 0.45},
      "input_tokens": {"value": 15000},
      "output_tokens": {"value": 3500},
      "cache_read_tokens": {"value": 12000}
    }
  }
}
```

### Time-Filtered Metrics

Get metrics for last N hours:

```bash
curl "http://localhost:3456/api/metrics/session/{id}?hours_back=2"
```

## Tips for Reducing Token Usage

1. **Use smaller context** - Include only necessary files
2. **Leverage caching** - Repeated contexts benefit from cache
3. **Use Haiku for simple tasks** - Much cheaper than Sonnet/Opus
4. **Clear conversation** - `/clear` starts fresh
5. **Use `/compact`** - Summarizes long conversations

## Third-Party Tools

For additional usage analysis:

### ccusage

CLI tool for analyzing Claude Code usage:

```bash
npm install -g ccusage
ccusage --monthly
ccusage --session
```

[GitHub: ryoppippi/ccusage](https://github.com/ryoppippi/ccusage)

### Enterprise Analytics

For organizations, Anthropic provides analytics API:

```
GET /v1/organizations/usage_report/claude_code
```

Requires Admin API key. See [Anthropic docs](https://docs.anthropic.com/en/api/claude-code-analytics-api).

## Limitations

**What SuperTrace captures:**
- Token counts per assistant response
- Aggregated session totals
- Cost estimates

**What SuperTrace doesn't capture:**
- Real-time streaming counts
- Cross-instance usage
- API-level usage (only CLI/IDE)

## See Also

- [Architecture](../concepts/architecture.md) - Data flow overview
- [API Reference](../reference/api.md) - Metrics endpoint
