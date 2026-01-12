# SuperTrace Documentation

Documentation for SuperTrace - a monitoring and observability tool for AI coding assistant sessions.

## Documentation Structure

This documentation follows the [Diátaxis framework](https://diataxis.fr/), organizing content into four categories based on user needs:

| Folder | Type | Purpose |
|--------|------|---------|
| `getting-started/` | Tutorials | Step-by-step guides for new users |
| `guides/` | How-to | Task-oriented instructions for specific goals |
| `reference/` | Reference | Technical specifications and API details |
| `concepts/` | Explanation | Background knowledge and architecture |

## Quick Links

### Getting Started
- [Installation](getting-started/installation.md) - Set up SuperTrace
- [Quick Start](getting-started/quickstart.md) - Get running in 5 minutes

### How-to Guides
- [Configure Hooks](guides/configure-hooks.md) - Set up Claude Code hooks
- [Export Sessions](guides/export-sessions.md) - Export data to JSON/Markdown
- [Token Usage Tracking](guides/token-usage.md) - Monitor token consumption and costs
- [Optimize File Suggestions](guides/file-suggestion.md) - Speed up `@` file autocomplete

### Reference
- [API Reference](reference/api.md) - REST API endpoints
- [Hook Events](reference/hook-events.md) - Available hook types and data
- [Configuration](reference/configuration.md) - Environment variables

### Concepts
- [Architecture](concepts/architecture.md) - System design overview
- [How Hooks Work](concepts/how-hooks-work.md) - Understanding the capture mechanism

## Contributing to Docs

When adding documentation:

1. **Choose the right category** - Is it a tutorial, how-to, reference, or explanation?
2. **One topic per page** - Keep documents focused
3. **Use clear headings** - Enable scanning and navigation
4. **Include examples** - Show, don't just tell
5. **Link related docs** - Help users navigate

See [CONTRIBUTING.md](../CONTRIBUTING.md) for more details.
