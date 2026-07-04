"""PyInstaller entry point for the bundled SATC executable.

One frozen executable, two modes:

  * Default (double-click, or ``SATC``): launch the local GUI app — pick a free
    port, open the browser, serve the human GUI. Unchanged behaviour.
  * ``SATC --mcp`` (how a Claude/Cowork agent spawns it over stdio): launch the
    MCP server so the agent can read clients and run withholding with NO Python
    install. The server is SAFE BY DEFAULT (read + compute only); it cannot
    change client data unless ``SATC_MCP_ALLOW_WRITES=1`` is set.

Both modes share the same local store (~/.satc/data, or SATC_DATA_DIR), so what
the agent reads is the app's data, and anything you commit in the app is what the
agent sees. Point an agent at it with, e.g.::

    { "mcpServers": { "satc": { "command": "C:/path/to/SATC.exe", "args": ["--mcp"] } } }
"""

import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("--mcp", "mcp"):
        from satc.api.mcp_server import main as run_mcp
        run_mcp()
    else:
        from satc.app.server import main as run_app
        run_app()


if __name__ == "__main__":
    main()
