# LSP And MCP

DocFit is a Python 3.11+ project managed with `uv`.

## Underlying Language Server

`pyrightconfig.json` is checked in so Pyright-compatible tools resolve the
`src/` package layout, tests, and the repo `.venv`.

Recommended local tool:

```bash
uv add --dev basedpyright
uv run basedpyright
```

If dependency installation is not desired for a task, keep the config file and
use the editor or agent's existing Pyright-compatible server.

## Agent-Facing Serena MCP

Serena setup is intentionally documented instead of checked in because Codex
currently uses a user-level `~/.codex/config.toml` MCP entry, and editing that
global state is outside this repo.

Current Serena docs describe these setup paths:

```bash
serena setup codex
```

Manual Codex config equivalent:

```toml
[mcp_servers.serena]
startup_timeout_sec = 15
command = "serena"
args = ["start-mcp-server", "--project-from-cwd", "--context=codex"]
```

Claude Code per-project setup:

```bash
claude mcp add serena -- serena start-mcp-server --context claude-code --project "$(pwd)"
```

After setup, verify with the client MCP tool list and activate this repository
as the Serena project when needed.

Source checked during init: https://oraios.github.io/serena/02-usage/030_clients.html
