#!/usr/bin/env bash
#
# SuperTrace Context Tracker Hook for Claude Code
#
# This hook captures context window usage data from Claude Code sessions
# and sends it to the SuperTrace backend for real-time tracking.
#
# Hook Event: PostToolUse (fires after each tool call)
#
# Installation:
#   Option 1 (Plugin): Copy supertrace-plugin/ to ~/.claude/plugins/supertrace/
#   Option 2 (Manual): Add hook config to ~/.claude/settings.json
#
# Environment:
#   SUPERTRACE_URL      - SuperTrace backend URL (default: http://localhost:7845)
#   SUPERTRACE_DEBUG    - Enable debug logging (set to "true")
#   SUPERTRACE_TIMEOUT  - Request timeout in seconds (default: 2)
#

set -euo pipefail

# Configuration with defaults
SUPERTRACE_URL="${SUPERTRACE_URL:-http://localhost:7845}"
SUPERTRACE_DEBUG="${SUPERTRACE_DEBUG:-false}"
SUPERTRACE_TIMEOUT="${SUPERTRACE_TIMEOUT:-2}"

# Debug logging function
debug() {
    if [ "$SUPERTRACE_DEBUG" = "true" ]; then
        echo "[SuperTrace Debug] $*" >&2
    fi
}

# Log errors but don't fail - hooks must be non-blocking
log_error() {
    echo "[SuperTrace Error] $*" >&2
}

# Read stdin (Claude Code passes JSON input)
input=$(cat 2>/dev/null || echo "{}")

debug "Received hook input"

# Extract session_id from hook input
session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null || true)

if [ -z "$session_id" ]; then
    debug "No session_id found in hook input, skipping"
    exit 0
fi

debug "Session ID: $session_id"

# Get transcript path from hook input
transcript_path=$(echo "$input" | jq -r '.transcript_path // empty' 2>/dev/null || true)

if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
    debug "No valid transcript_path found, skipping"
    exit 0
fi

debug "Transcript path: $transcript_path"

# Parse the latest API response from transcript to get token usage
# The transcript is JSONL format with API responses containing usage data
# Look for the most recent entry with usage data

# Get the last line with usage data from transcript
latest_usage=$(tail -100 "$transcript_path" 2>/dev/null | \
    grep -o '"usage":{[^}]*}' 2>/dev/null | \
    tail -1 || true)

if [ -z "$latest_usage" ]; then
    debug "No usage data found in recent transcript entries"
    exit 0
fi

debug "Found usage data: $latest_usage"

# Extract token counts from usage data
# Format: "usage":{"input_tokens":1234,"output_tokens":567,"cache_creation_input_tokens":0,"cache_read_input_tokens":890}
input_tokens=$(echo "{$latest_usage}" | jq -r '.usage.input_tokens // 0' 2>/dev/null || echo "0")
output_tokens=$(echo "{$latest_usage}" | jq -r '.usage.output_tokens // 0' 2>/dev/null || echo "0")
cache_read_tokens=$(echo "{$latest_usage}" | jq -r '.usage.cache_read_input_tokens // 0' 2>/dev/null || echo "0")
cache_creation_tokens=$(echo "{$latest_usage}" | jq -r '.usage.cache_creation_input_tokens // 0' 2>/dev/null || echo "0")

# Calculate totals
total_input_tokens=$((input_tokens + cache_read_tokens + cache_creation_tokens))
total_output_tokens=$output_tokens
total_tokens=$((total_input_tokens + total_output_tokens))

debug "Input tokens: $total_input_tokens, Output tokens: $total_output_tokens"

# Estimate context window size (default to 200k for Claude)
# This could be enhanced to detect model type from transcript
context_window_size=200000

# Calculate percentages
used_percentage=$(echo "scale=2; ($total_tokens * 100) / $context_window_size" | bc 2>/dev/null || echo "0")
remaining_percentage=$(echo "scale=2; 100 - $used_percentage" | bc 2>/dev/null || echo "100")

debug "Used: ${used_percentage}%, Remaining: ${remaining_percentage}%"

# Build the payload for SuperTrace API
payload=$(jq -n \
    --argjson used_percentage "$used_percentage" \
    --argjson remaining_percentage "$remaining_percentage" \
    --argjson context_window_size "$context_window_size" \
    --argjson total_input_tokens "$total_input_tokens" \
    --argjson total_output_tokens "$total_output_tokens" \
    --argjson cache_read_tokens "$cache_read_tokens" \
    --argjson cache_creation_tokens "$cache_creation_tokens" \
    '{
        used_percentage: $used_percentage,
        remaining_percentage: $remaining_percentage,
        context_window_size: $context_window_size,
        total_input_tokens: $total_input_tokens,
        total_output_tokens: $total_output_tokens,
        cache_read_tokens: $cache_read_tokens,
        cache_creation_tokens: $cache_creation_tokens
    }' 2>/dev/null || true)

if [ -z "$payload" ]; then
    log_error "Failed to build payload"
    exit 0
fi

debug "Payload: $payload"

# POST to SuperTrace API with timeout
# Use || true to ensure hook never blocks Claude Code
api_url="${SUPERTRACE_URL}/api/sessions/${session_id}/context"

debug "POSTing to: $api_url"

response=$(curl -s -X POST "$api_url" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    --connect-timeout "$SUPERTRACE_TIMEOUT" \
    --max-time "$SUPERTRACE_TIMEOUT" \
    2>/dev/null || true)

if [ -n "$response" ]; then
    debug "Response: $response"
fi

# Always exit successfully - hooks must be non-blocking
exit 0
