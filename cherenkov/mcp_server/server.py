import asyncio
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from cherenkov.core.settings import get_settings

# Initialize the MCP Server
mcp = FastMCP("CherenkovQA")

@mcp.tool()
async def verify_api(url: str, credential: str | None = None) -> Dict[str, Any]:
    """
    Verify a live API against its OpenAPI spec to find divergences.
    Returns a machine-readable JSON structure detailing the findings.
    """
    from cherenkov.cli.commands.verify import _verify_impl
    import io
    import contextlib
    
    settings = get_settings()
    
    headers = None
    if credential:
        cred_data = settings.CREDENTIALS.get(credential)
        if cred_data:
            if isinstance(cred_data, dict):
                headers = cred_data.get("headers", {})
            else:
                headers = {"Authorization": str(cred_data)}
                
    sink: dict = {}
    buffer = io.StringIO()
    
    # We must suppress stdout because the internal verify function prints progress
    with contextlib.redirect_stdout(buffer):
        _verify_impl(
            url=url,
            spec=None,
            llm=False,
            output=None,
            output_format="json",
            fail_on_divergence=False,
            coverage_report=False,
            health_score=False,
            rich_verdict=True,
            no_mutation_oracle=False,
            no_traffic_capture=False,
            fixture_dir=".cherenkov/fixtures",
            max_probes=40,
            identifiers=None,
            allow_mutations=False,
            doc_sink=sink,
            headers=headers,
        )
        
    if "doc" in sink:
        return sink["doc"]
    
    return {"error": "Verification failed to produce a document.", "output": buffer.getvalue()}


def run_mcp_server() -> None:
    """Entry point for running the MCP server."""
    mcp.run()

if __name__ == "__main__":
    run_mcp_server()
