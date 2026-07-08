"""Notion export via a self-hosted MCP server (stdio).

Launches ``@notionhq/notion-mcp-server`` as a subprocess, connects with a Python
MCP client, discovers the create-page tool, and creates a page for an approved
plan. Token auth is passed via environment (works headless, unlike the hosted
OAuth-only server).
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


class NotionExportError(RuntimeError):
    """Raised when the Notion export fails."""


def find_create_page_tool(tool_names: list[str]) -> str | None:
    """Pick the tool that creates a page from the server's tool list."""
    lowered = {name.lower(): name for name in tool_names}
    # Exact/known names first (OpenAPI-derived server uses 'API-post-page').
    for candidate in ("api-post-page", "post-page", "create-page", "create_page"):
        for low, original in lowered.items():
            if candidate in low:
                return original
    # Fallback: any tool mentioning both 'page' and a create-ish verb.
    for low, original in lowered.items():
        if "page" in low and any(v in low for v in ("post", "create", "add")):
            return original
    return None


def extract_page_url(payload: Any) -> str | None:
    """Find a Notion page URL in a (possibly nested) tool result payload."""
    if isinstance(payload, dict):
        if isinstance(payload.get("url"), str):
            return payload["url"]
        for value in payload.values():
            found = extract_page_url(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = extract_page_url(item)
            if found:
                return found
    return None


def _result_to_payload(result: Any) -> Any:
    """Parse a CallToolResult's text content into a Python object."""
    texts = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            texts.append(text)
    blob = "\n".join(texts)
    if not blob:
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return blob


class NotionExporter:
    """Creates Notion pages by talking to the Notion MCP server over stdio."""

    def __init__(
        self,
        token: str,
        parent_page_id: str,
        *,
        version: str = "2022-06-28",
        command: str = "npx",
        args: list[str] | None = None,
    ):
        self._token = token
        self._parent_page_id = parent_page_id
        self._version = version
        self._command = command
        self._args = args or ["-y", "@notionhq/notion-mcp-server"]

    @classmethod
    def from_settings(cls) -> NotionExporter:
        s = get_settings()
        if not s.notion_configured:
            raise NotionExportError(
                "Notion export not configured: set NOTION_TOKEN and "
                "NOTION_PARENT_PAGE_ID."
            )
        return cls(
            token=s.NOTION_TOKEN,  # type: ignore[arg-type]
            parent_page_id=s.NOTION_PARENT_PAGE_ID,  # type: ignore[arg-type]
            version=s.NOTION_VERSION,
            command=s.NOTION_MCP_COMMAND,
            args=s.notion_mcp_args,
        )

    def _server_params(self) -> StdioServerParameters:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": self._version,
        }
        env = {
            **os.environ,
            "NOTION_TOKEN": self._token,
            "OPENAPI_MCP_HEADERS": json.dumps(headers),
        }
        return StdioServerParameters(
            command=self._command, args=self._args, env=env
        )

    def _create_page_arguments(
        self, title: str, blocks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {
            "parent": {"page_id": self._parent_page_id},
            "properties": {
                "title": {"title": [{"text": {"content": title[:1900]}}]}
            },
            # Notion caps children at 100 blocks per create call.
            "children": blocks[:100],
        }

    async def create_page(self, title: str, blocks: list[dict[str, Any]]) -> str:
        """Create a Notion page and return its URL."""
        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = [t.name for t in tools.tools]
                tool_name = find_create_page_tool(names)
                if not tool_name:
                    raise NotionExportError(
                        f"No create-page tool found. Available: {names}"
                    )
                log.info("notion_create_page", tool=tool_name)
                result = await session.call_tool(
                    tool_name, self._create_page_arguments(title, blocks)
                )
                if getattr(result, "isError", False):
                    payload = _result_to_payload(result)
                    raise NotionExportError(f"Notion tool error: {payload}")

                url = extract_page_url(_result_to_payload(result))
                if not url:
                    raise NotionExportError("Notion did not return a page URL.")
                return url
