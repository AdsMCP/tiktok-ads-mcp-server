"""TikTok Ads MCP Server implementation."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    LoggingCapability,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolsCapability,
)

from .oauth_simple import SimpleTikTokOAuth, start_manual_oauth
from .tiktok_client import TikTokAdsClient
from .tools import (
    AudienceTools,
    CampaignTools,
    CreativeTools,
    PerformanceTools,
    ReportingTools,
)
from .tools.registry import dispatch_tool, list_mcp_tools, serialize_tool_result


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("tiktok-ads-mcp")


class TikTokMCPServer:
    """Runtime state for the TikTok Ads MCP server."""

    def __init__(self):
        self.client: Optional[TikTokAdsClient] = None
        self.campaign_tools: Optional[CampaignTools] = None
        self.creative_tools: Optional[CreativeTools] = None
        self.performance_tools: Optional[PerformanceTools] = None
        self.audience_tools: Optional[AudienceTools] = None
        self.reporting_tools: Optional[ReportingTools] = None
        self.app_id: Optional[str] = None
        self.app_secret: Optional[str] = None
        self.is_authenticated = False
        self.primary_advertiser_id: Optional[str] = None
        self.available_advertiser_ids: List[str] = []
        self.oauth_client: Optional[SimpleTikTokOAuth] = None

    async def initialize(self):
        """Initialize the server from environment credentials."""
        try:
            self.app_id = os.getenv("TIKTOK_APP_ID")
            self.app_secret = os.getenv("TIKTOK_APP_SECRET")
            access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
            advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
            advertiser_ids_env = os.getenv("TIKTOK_AVAILABLE_ADVERTISER_IDS", "")
            available_advertiser_ids = [
                value.strip()
                for value in advertiser_ids_env.split(",")
                if value.strip()
            ]

            if advertiser_id and advertiser_id not in available_advertiser_ids:
                available_advertiser_ids.append(advertiser_id)

            if not self.app_id or not self.app_secret:
                raise ValueError(
                    "Missing TikTok API credentials. Provide TIKTOK_APP_ID and TIKTOK_APP_SECRET environment variables."
                )

            self.oauth_client = SimpleTikTokOAuth(self.app_id, self.app_secret)

            if access_token and advertiser_id:
                logger.info("Using direct token authentication...")
                await self._authenticate_with_tokens(
                    access_token,
                    advertiser_id,
                    available_advertiser_ids,
                )
            else:
                logger.info(
                    "OAuth credentials configured. Use the 'tiktok_ads_login' tool to authenticate."
                )

            logger.info("TikTok Ads MCP Server initialized successfully")
        except Exception as exc:
            logger.error("Failed to initialize TikTok Ads MCP Server: %s", exc)
            raise

    async def _authenticate_with_tokens(
        self,
        access_token: str,
        advertiser_id: str,
        available_advertiser_ids: List[str],
    ):
        """Authenticate using an existing access token and advertiser ID."""
        self.client = TikTokAdsClient(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=access_token,
            advertiser_id=advertiser_id,
            available_advertiser_ids=available_advertiser_ids,
        )

        self.campaign_tools = CampaignTools(self.client)
        self.creative_tools = CreativeTools(self.client)
        self.performance_tools = PerformanceTools(self.client)
        self.audience_tools = AudienceTools(self.client)
        self.reporting_tools = ReportingTools(self.client)

        self.is_authenticated = True
        self.primary_advertiser_id = advertiser_id
        self.available_advertiser_ids = available_advertiser_ids

    async def start_oauth_flow(self, force_reauth: bool = False) -> Dict[str, Any]:
        """Start the manual OAuth flow."""
        if not self.oauth_client:
            return {"success": False, "error": "OAuth client not initialized"}

        try:
            result, token_data = start_manual_oauth(
                self.app_id,
                self.app_secret,
                force_reauth=force_reauth,
            )
            if token_data:
                await self._authenticate_with_tokens(
                    token_data["access_token"],
                    token_data["primary_advertiser_id"],
                    token_data["advertiser_ids"],
                )
            return {"success": True, "data": result}
        except Exception as exc:
            logger.error("Failed to start OAuth flow: %s", exc)
            return {"success": False, "data": {"error": str(exc)}}

    async def complete_oauth(self, auth_code: str) -> Dict[str, Any]:
        """Complete OAuth with an authorization code."""
        if not self.oauth_client:
            return {"success": False, "data": {"error": "OAuth client not initialized"}}

        try:
            token_data = await self.oauth_client.exchange_code_for_token(auth_code)
            if not token_data:
                return {
                    "success": False,
                    "data": {"error": "Failed to exchange authorization code for tokens"},
                }

            if "error_message" in token_data:
                return {"success": False, "data": {"error": token_data["error_message"]}}

            await self._authenticate_with_tokens(
                token_data["access_token"],
                token_data["primary_advertiser_id"],
                token_data["advertiser_ids"],
            )

            logger.info(
                "OAuth completed successfully. Using advertiser ID: %s",
                token_data["primary_advertiser_id"],
            )

            return {
                "success": True,
                "data": {
                    "message": "Authentication completed successfully",
                    "primary_advertiser_id": token_data["primary_advertiser_id"],
                    "available_advertiser_ids": token_data["advertiser_ids"],
                },
            }
        except Exception as exc:
            logger.error("Failed to complete OAuth: %s", exc)
            return {"success": False, "error": str(exc)}

    async def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status."""
        if self.is_authenticated:
            return {
                "success": True,
                "data": {
                    "status": "authenticated",
                    "app_id": self.app_id,
                    "available_advertiser_ids": self.available_advertiser_ids,
                    "primary_advertiser_id": self.primary_advertiser_id,
                    "message": "Already authenticated",
                },
            }

        if not self.app_id or not self.app_secret:
            return {
                "success": True,
                "data": {
                    "status": "not_configured",
                    "app_id": self.app_id,
                    "message": "TikTok API credentials are not configured. Set TIKTOK_APP_ID and TIKTOK_APP_SECRET before authenticating.",
                },
            }

        oauth_client = SimpleTikTokOAuth(self.app_id, self.app_secret)
        saved_tokens = oauth_client.load_saved_tokens()
        if saved_tokens and saved_tokens.get("access_token"):
            await self._authenticate_with_tokens(
                saved_tokens["access_token"],
                saved_tokens["primary_advertiser_id"],
                saved_tokens["advertiser_ids"],
            )
            return {
                "success": True,
                "data": {
                    "status": "authenticated",
                    "app_id": self.app_id,
                    "available_advertiser_ids": saved_tokens.get("advertiser_ids", []),
                    "primary_advertiser_id": saved_tokens.get("primary_advertiser_id"),
                    "message": "Already authenticated with saved tokens",
                },
            }

        return {
            "success": True,
            "data": {
                "status": "not_authenticated",
                "app_id": self.app_id,
                "message": "No saved tokens found. Please use tiktok_ads_login to authenticate.",
            },
        }

    async def switch_ad_account(self, advertiser_id: str) -> Dict[str, Any]:
        """Switch to a different advertiser account."""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated. Please login first."}

        warning_message = ""
        if advertiser_id not in self.available_advertiser_ids:
            warning_message = f"Warn: Advertiser ID {advertiser_id} may not be available."

        try:
            if not self.client:
                return {"success": False, "error": "Client not initialized"}

            await self._authenticate_with_tokens(
                self.client.access_token,
                advertiser_id,
                self.available_advertiser_ids,
            )

            logger.info("Switched to advertiser account: %s", advertiser_id)
            return {
                "success": True,
                "data": {
                    "message": f"Switched to advertiser account {advertiser_id}. {warning_message}".strip(),
                    "current_advertiser_id": advertiser_id,
                    "available_advertiser_ids": self.available_advertiser_ids,
                },
            }
        except Exception as exc:
            logger.error("Failed to switch advertiser account: %s", exc)
            return {"success": False, "error": str(exc)}


tiktok_server = TikTokMCPServer()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available TikTok Ads tools."""
    return list_mcp_tools()


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle TikTok Ads tool calls."""
    try:
        result = await dispatch_tool(tiktok_server, name, arguments)
        return [TextContent(type="text", text=serialize_tool_result(result))]
    except Exception as exc:
        logger.error("Error executing tool %s: %s", name, exc)
        return [TextContent(type="text", text=f"Error executing {name}: {exc}")]


async def main():
    """Main entry point for the TikTok Ads MCP server."""
    try:
        await tiktok_server.initialize()
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="tiktok-ads-mcp",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(listChanged=True),
                        logging=LoggingCapability(),
                    ),
                ),
            )
    except Exception as exc:
        logger.error("Server failed to start: %s", exc)
        raise


if __name__ == "__main__":
    asyncio.run(main())
