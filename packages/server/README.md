<p align="center">
  <img src="https://quickcall.dev/assets/v1/qc-full-512px-white.png" alt="QuickCall" width="400">
</p>

<h3 align="center">SuperTrace - Monitor your AI coding sessions</h3>

<p align="center">
  <em>See what your AI assistant is doing. Track inputs, outputs, and tool calls in real-time.</em>
</p>

<p align="center">
  <a href="https://quickcall.dev"><img src="https://img.shields.io/badge/Web-quickcall.dev-000000?logo=googlechrome&logoColor=white" alt="Web"></a>
  <a href="https://discord.gg/DtnMxuE35v"><img src="https://img.shields.io/badge/Discord-Join%20Us-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://pypi.org/project/quickcall-supertrace/"><img src="https://img.shields.io/pypi/v/quickcall-supertrace?color=blue" alt="PyPI"></a>
</p>

<p align="center">
  <a href="#install">Install</a> |
  <a href="#features">Features</a> |
  <a href="#configuration">Configuration</a> |
  <a href="#docker">Docker</a> |
  <a href="#troubleshooting">Troubleshooting</a>
</p>

---

<p align="center">
  <img src="assets/demo-image.png" alt="SuperTrace Demo" width="800">
</p>

---

## Install

```bash
uvx quickcall-supertrace@latest
```

Open http://localhost:7845 in your browser.

> SuperTrace reads directly from Claude Code's JSONL transcript files at `~/.claude/projects/`. No hooks or configuration needed.

> **100% Local** - All data stays on your machine. Nothing is sent to any external servers.

### Alternative Methods

```bash
# Install globally
uv tool install quickcall-supertrace

# Upgrade to latest
uv tool upgrade quickcall-supertrace

# Or with pip
pip install quickcall-supertrace
quickcall-supertrace
```

## Features

- **Real-time monitoring** - Watch AI assistant inputs/outputs as they happen
- **Session timeline** - Browse all your coding sessions
- **Conversation view** - See user prompts, assistant responses, and tool calls
- **Full-text search** - Find anything across all sessions
- **Export** - Download sessions as JSON or Markdown
- **WebSocket updates** - Live updates without page refresh

## Configuration

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `QUICKCALL_SUPERTRACE_PORT` | 7845 | Server port |
| `QUICKCALL_SUPERTRACE_HOST` | 127.0.0.1 | Server host |

## Docker

```bash
docker compose up -d
```

## Troubleshooting

### Port Already in Use

```bash
QUICKCALL_SUPERTRACE_PORT=8080 uvx quickcall-supertrace@latest
```

### Reset Database

```bash
rm -rf ~/.quickcall-supertrace
```

### Stop the Server

```bash
# Foreground: Ctrl+C
# Background: pkill -f quickcall_supertrace
```

---

<p align="center">
  Built with care by <a href="https://quickcall.dev">QuickCall</a>
</p>
