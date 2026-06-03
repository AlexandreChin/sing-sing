"""
data.gouv.fr MCP client.

Connects to the official data.gouv.fr MCP server (https://github.com/datagouv/datagouv-mcp)
via the hosted endpoint at https://mcp.data.gouv.fr/mcp (no API key required).

Available MCP tools proxied here:
  - search_datasets        Search datasets by keywords
  - get_dataset_info       Full metadata for a dataset
  - list_dataset_resources List files/resources in a dataset
  - get_resource_info      Metadata for a specific resource
  - query_resource_data    Query tabular data via the Tabular API
  - search_dataservices    Search registered third-party APIs
  - get_dataservice_info   Metadata for a dataservice
  - get_metrics            Visit/download stats for a dataset or resource

Set DATAGOUV_MCP_URL in .env to override the default hosted endpoint.
"""

import json
import os

import httpx


_DEFAULT_MCP_URL = "https://mcp.data.gouv.fr/mcp"


def _mcp_url() -> str:
    return os.environ.get("DATAGOUV_MCP_URL", _DEFAULT_MCP_URL)


async def _call(tool: str, arguments: dict) -> dict:
    """Send a JSON-RPC 2.0 tools/call request to the MCP server."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            _mcp_url(),
            json=payload,
            headers={
                "Content-Type": "application/json",
                # MCP server uses SSE transport — must accept both
                "Accept": "application/json, text/event-stream",
            },
        )
        response.raise_for_status()

    # Response is SSE: parse the first `data:` line
    body: dict = {}
    for line in response.text.splitlines():
        if line.startswith("data:"):
            body = json.loads(line[len("data:"):].strip())
            break

    if body.get("result", {}).get("isError"):
        content = body["result"].get("content", [])
        msg = "\n".join(b["text"] for b in content if b.get("type") == "text")
        raise RuntimeError(f"MCP tool error ({tool}): {msg}")

    if "error" in body:
        raise RuntimeError(f"MCP error from {tool}: {body['error']}")

    # Extract text content blocks and parse as JSON
    content = body.get("result", {}).get("content", [])
    text = "\n".join(block["text"] for block in content if block.get("type") == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


async def search_datasets(query: str, page: int = 1, page_size: int = 10) -> dict:
    """Search data.gouv.fr datasets by keywords."""
    return await _call("search_datasets", {"query": query, "page": page, "page_size": page_size})


async def get_dataset_info(dataset_id: str) -> dict:
    """Get full metadata for a dataset by its ID or slug."""
    return await _call("get_dataset_info", {"dataset": dataset_id})


async def list_dataset_resources(dataset_id: str) -> dict:
    """List all files/resources attached to a dataset."""
    return await _call("list_dataset_resources", {"dataset": dataset_id})


async def get_resource_info(dataset_id: str, resource_id: str) -> dict:
    """Get metadata for a specific resource within a dataset."""
    return await _call("get_resource_info", {"dataset": dataset_id, "resource": resource_id})


async def query_resource_data(
    dataset_id: str,
    resource_id: str,
    *,
    limit: int = 20,
    filters: dict | None = None,
) -> dict:
    """Query tabular data from a resource via the Tabular API."""
    args: dict = {"dataset": dataset_id, "resource": resource_id, "limit": limit}
    if filters:
        args["filters"] = filters
    return await _call("query_resource_data", args)


async def search_dataservices(query: str, page_size: int = 10) -> dict:
    """Search registered third-party APIs/dataservices on data.gouv.fr."""
    return await _call("search_dataservices", {"q": query, "page_size": page_size})


async def get_dataservice_info(dataservice_id: str) -> dict:
    """Get metadata for a specific dataservice."""
    return await _call("get_dataservice_info", {"dataservice": dataservice_id})


async def get_metrics(dataset_id: str, resource_id: str | None = None) -> dict:
    """Get visit and download statistics for a dataset or resource."""
    args: dict = {"dataset": dataset_id}
    if resource_id:
        args["resource"] = resource_id
    return await _call("get_metrics", args)
