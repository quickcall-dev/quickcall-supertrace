# Distribution & Packaging

How to build, test, and distribute QuickCall SuperTrace as a single installable package.

## Overview

QuickCall SuperTrace is distributed as a Python package that bundles the React frontend. Users can install and run it with a single command:

```bash
uvx quickcall-supertrace
```

## Build Process

### Prerequisites

- Python 3.10+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) package manager

### Build Steps

```bash
cd packages/server
./build.sh
```

The build script performs these steps:

```
1. Build frontend (npm run build)
   └── packages/web/dist/

2. Bundle into Python package
   └── packages/server/src/quickcall_supertrace/static/

3. Build Python wheel
   └── packages/server/dist/quickcall_supertrace-*.whl
```

### Manual Build

If you prefer to run steps manually:

```bash
# 1. Build frontend
cd packages/web
npm run build

# 2. Copy to Python package
cp -r dist ../server/src/quickcall_supertrace/static

# 3. Build wheel
cd ../server
uv build
```

## How It Works

### Package Structure

```
quickcall_supertrace/
├── main.py              # FastAPI app + static file serving
├── static/              # Bundled React frontend
│   ├── index.html
│   └── assets/
│       ├── index-*.js
│       └── index-*.css
├── db/                  # Database layer
├── routes/              # API endpoints
└── ...
```

### Static File Serving

The FastAPI server automatically serves the bundled frontend:

```python
# main.py
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"))

    @app.get("/")
    async def serve_frontend():
        return FileResponse(STATIC_DIR / "index.html")
```

When running, the server provides:
- `/` → React frontend (index.html)
- `/assets/*` → JS, CSS, fonts
- `/api/*` → REST API
- `/ws` → WebSocket

## Testing Locally

### Test with uvx (Recommended)

```bash
# From packages/server/
uvx --from ./dist/quickcall_supertrace-0.1.0-py3-none-any.whl quickcall-supertrace
```

### Test with pip install

```bash
# Create a test venv
python -m venv test-venv
source test-venv/bin/activate

# Install from wheel
pip install ./dist/quickcall_supertrace-0.1.0-py3-none-any.whl

# Run
quickcall-supertrace
```

### Verify It's Working

1. Open http://localhost:7845 in your browser
2. You should see the QuickCall SuperTrace UI
3. Check the API: `curl http://localhost:7845/api/health`

## Stopping the Server

### Foreground (default)

Press `Ctrl+C` in the terminal.

### Background Process

```bash
# Find the process
ps aux | grep quickcall_supertrace

# Kill by PID
kill <pid>

# Or kill all instances
pkill -f quickcall_supertrace
```

### Using a Specific Port

If port 7845 is in use:

```bash
# Find what's using the port
lsof -i :7845

# Kill it
kill <pid>

# Or use a different port
QUICKCALL_SUPERTRACE_PORT=8080 quickcall-supertrace
```

## Publishing to PyPI

### Setup (One-time)

1. Create account at https://pypi.org
2. Generate API token at https://pypi.org/manage/account/token/
3. Configure credentials:

```bash
# Using uv
uv config set pypi-token <your-token>

# Or create ~/.pypirc
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-<your-token>
EOF
```

### Publish

```bash
cd packages/server

# Build first
./build.sh

# Upload to PyPI
uv publish

# Or with twine
pip install twine
twine upload dist/*
```

### Version Bump

Update version in `pyproject.toml` before each release:

```toml
[project]
version = "0.2.0"  # Increment this
```

## User Installation

Once published, users can install with:

```bash
# Run without installing (recommended)
uvx quickcall-supertrace

# Or install globally
uv tool install quickcall-supertrace

# Or with pip
pip install quickcall-supertrace
```

## Troubleshooting

### Build Fails: npm not found

Install Node.js:
```bash
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Port Already in Use

```bash
# Use different port
QUICKCALL_SUPERTRACE_PORT=8080 quickcall-supertrace
```

### Frontend Not Loading

Check if static files are bundled:
```bash
unzip -l dist/quickcall_supertrace-*.whl | grep static
```

If missing, rebuild:
```bash
rm -rf src/quickcall_supertrace/static
./build.sh
```

### Database Location

Data is stored at `~/.quickcall-supertrace/data.db`. To reset:
```bash
rm -rf ~/.quickcall-supertrace
```

## CI/CD Automation

Example GitHub Actions workflow for automated releases:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - uses: astral-sh/setup-uv@v4

      - name: Build
        run: |
          cd packages/server
          chmod +x build.sh
          ./build.sh

      - name: Publish to PyPI
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_TOKEN }}
        run: |
          cd packages/server
          uv publish
```

## See Also

- [Installation](../getting-started/installation.md) - User installation guide
- [Configuration](../reference/configuration.md) - Environment variables
- [Architecture](../concepts/architecture.md) - System design
