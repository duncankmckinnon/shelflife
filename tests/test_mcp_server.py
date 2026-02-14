import pytest
from shelflife.mcp.client import ShelflifeClient
from shelflife.mcp.server import create_mcp_server


def test_mcp_server_has_all_tools(client):
    sl = ShelflifeClient(client)
    mcp = create_mcp_server(sl)
    assert mcp.name == "shelflife"
