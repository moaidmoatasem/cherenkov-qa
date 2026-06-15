# Publishing CHERENKOV MCP to the Official Registry

To publish the CHERENKOV MCP server to the official Model Context Protocol (MCP) registry, please follow these steps:

1. Ensure your latest changes are merged to `main` and all CI checks pass.
2. Build the MCP standalone server package:
   ```bash
   python -m build
   ```
3. Test the built package locally using the MCP CLI or directly in an MCP-compliant client (like Claude Desktop).
4. Tag a new release in GitHub (e.g., `v1.2.0`).
5. Upload the package to PyPI (if applicable) or publish the Docker container.
6. Open a PR to the [official MCP registry repository](https://github.com/modelcontextprotocol/registry) adding `cherenkov-mcp` to the `servers.json` file.
