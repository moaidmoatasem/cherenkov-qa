"""
cherenkov/mcp/__init__.py
MCP server package — exposes cherenkov surfaces over Model Context Protocol.
schema_version = 'mcp/v1'

Trust: MCP peers are untrusted. All inputs are validated with Pydantic before
reaching any queue or gate. Writes go through the existing HitlQueue atomic
SQL gatekeeper — same code path as the terminal CLI.

Refs: issue #133 (X4), docs/vision/08_DELIVERY_PLAN.md §3 X4,
      docs/vision/10_HORIZON_2.md §Bet 2.
"""
