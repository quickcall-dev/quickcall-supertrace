# Optimize File Suggestions

How to dramatically speed up Claude Code's `@` file autocomplete in large codebases.

## The Problem

Claude Code's default file suggestion uses fast filesystem traversal, which works well for small to medium projects. However, in large monorepos (like TikTok's codebase), file search can take **8+ seconds per character typed**.

## The Solution

Claude Code allows you to configure a custom command for `@` file path autocomplete using tools like ripgrep and fzf. This can reduce search time from **~8 seconds to <200ms**.

> "Today I did an exploration and reduced the file search time in the TikTok codebase from nearly 8s to less than 200ms. Mentioning any file in Claude is practically instantaneous now."

## Prerequisites

Install the required tools:

```bash
# macOS
brew install ripgrep fzf jq

# Ubuntu/Debian
sudo apt install ripgrep fzf jq

# Windows (with scoop)
scoop install ripgrep fzf jq
```

## Configuration

### 1. Create the Script

Create `~/.claude/file-suggestion.sh`:

```bash
#!/bin/bash
# Custom file suggestion script for Claude Code
# Uses ripgrep + fzf for fast fuzzy matching
#
# Performance: Reduces file search from ~8s to <200ms in large codebases
#
# Requirements: ripgrep (rg), fzf, jq
#   brew install ripgrep fzf jq

# Parse JSON input from stdin to get the query
QUERY=$(cat | jq -r '.query // ""')

# Use project directory from environment, fallback to current directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# Change to project directory so rg outputs relative paths
cd "$PROJECT_DIR" || exit 1

# Use ripgrep to list files (respects .gitignore, follows symlinks, includes hidden)
# Then pipe through fzf for fuzzy matching
# Limit to 20 results for performance
rg --files --follow --hidden 2>/dev/null | fzf --filter="$QUERY" | head -20
```

### 2. Make it Executable

```bash
chmod +x ~/.claude/file-suggestion.sh
```

### 3. Configure Claude Code

Add to your `~/.claude/settings.json`:

```json
{
  "fileSuggestion": {
    "type": "command",
    "command": "~/.claude/file-suggestion.sh"
  }
}
```

### 4. Restart Claude Code

The new configuration will take effect after restarting.

## How It Works

1. **Claude Code** sends JSON to stdin: `{"query": "user_typed_text"}`
2. **jq** extracts the query string
3. **ripgrep** lists all files (fast, respects `.gitignore`)
4. **fzf** performs fuzzy matching on the query
5. **head** limits results to prevent UI overload

### Why ripgrep + fzf?

| Tool | Purpose | Speed |
|------|---------|-------|
| **ripgrep** | List files recursively | ~10x faster than `find` |
| **fzf** | Fuzzy matching | Highly optimized for interactive filtering |

ripgrep automatically:
- Respects `.gitignore` rules
- Follows symlinks (`--follow`)
- Includes hidden files (`--hidden`)
- Outputs relative paths

## Advanced Configuration

### Include Gitignored Paths

If you need to include specific gitignored directories:

```bash
#!/bin/bash
QUERY=$(cat | jq -r '.query // ""')
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 1

{
  # Main search - respects .gitignore
  rg --files --follow --hidden 2>/dev/null

  # Include specific gitignored directories
  [ -d ".notes" ] && rg --files --follow --hidden --no-ignore-vcs .notes 2>/dev/null
  [ -d "vendor" ] && rg --files --follow --hidden --no-ignore-vcs vendor 2>/dev/null
} | sort -u | fzf --filter="$QUERY" | head -20
```

### Pre-built Index (Maximum Performance)

For the ultimate performance, use a pre-built file index:

```bash
#!/bin/bash
# Update index periodically (e.g., via cron or on git pull)
INDEX_FILE="${CLAUDE_PROJECT_DIR:-.}/.file-index"

# If index exists and is recent (less than 5 minutes old), use it
if [ -f "$INDEX_FILE" ] && [ $(($(date +%s) - $(stat -f %m "$INDEX_FILE"))) -lt 300 ]; then
  QUERY=$(cat | jq -r '.query // ""')
  fzf --filter="$QUERY" < "$INDEX_FILE" | head -20
else
  # Fall back to ripgrep
  QUERY=$(cat | jq -r '.query // ""')
  cd "${CLAUDE_PROJECT_DIR:-.}" || exit 1
  rg --files --follow --hidden 2>/dev/null | fzf --filter="$QUERY" | head -20
fi
```

Build the index periodically:
```bash
cd /path/to/project && rg --files --follow --hidden > .file-index
```

### Simpler Alternative

A minimal version if you don't need all features:

```bash
#!/bin/bash
query=$(cat | jq -r '.query')
cd "$CLAUDE_PROJECT_DIR"
rg --files --hidden | fzf --filter="$query" | head -20
```

## Troubleshooting

### Script Not Running

1. Check the script is executable: `ls -la ~/.claude/file-suggestion.sh`
2. Test manually: `echo '{"query":"test"}' | ~/.claude/file-suggestion.sh`
3. Check Claude Code logs for errors

### Claude Code Exits Silently

If Claude Code exits with code 0 and no error when ripgrep/fzf aren't installed, install the dependencies:
```bash
brew install ripgrep fzf jq
```

### Slow Results

1. Ensure you're not searching directories with millions of files
2. Add slow directories to `.gitignore`
3. Use the pre-built index approach for very large repos

### Wrong Directory

The script uses `$CLAUDE_PROJECT_DIR` environment variable. Verify it's set correctly by Claude Code.

## Performance Comparison

| Codebase Size | Default Search | With ripgrep+fzf |
|---------------|----------------|------------------|
| Small (<1K files) | ~100ms | ~50ms |
| Medium (<10K files) | ~500ms | ~100ms |
| Large (<100K files) | ~3s | ~150ms |
| Very Large (>100K files) | ~8s+ | ~200ms |

## References

- [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings)
- [ripgrep GitHub](https://github.com/BurntSushi/ripgrep)
- [fzf GitHub](https://github.com/junegunn/fzf)
- [Feature Request: Improve @ file search](https://github.com/anthropics/claude-code/issues/8530)
- [Rafael Thayto's Guide](https://x.com/thayto_dev/status/2009401734213554494)

## See Also

- [Configuration Reference](../reference/configuration.md)
- [Claude Code Settings](https://code.claude.com/docs/en/settings)
