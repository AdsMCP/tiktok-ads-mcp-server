"""TikTok Ads MCP Server implementation."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolsCapability,
    LoggingCapability,
)
from pydantic import BaseModel

from .tiktok_client import TikTokAdsClient
from .oauth_simple import SimpleTikTokOAuth, start_manual_oauth
from .tools import (
    CampaignTools,
    CreativeTools,
    PerformanceTools,
    AudienceTools,
    ReportingTools,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("tiktok-ads-mcp")


class TikTokMCPServer:
    """TikTok Ads MCP Server class."""
    
    def __init__(self):
        self.client: Optional[TikTokAdsClient] = None
        self.campaign_tools: Optional[CampaignTools] = None
        self.creative_tools: Optional[CreativeTools] = None
        self.performance_tools: Optional[PerformanceTools] = None
        self.audience_tools: Optional[AudienceTools] = None
        self.reporting_tools: Optional[ReportingTools] = None
        self.app_id: Optional[str] = None
        self.app_secret: Optional[str] = None
        self.is_authenticated: bool = False
        self.primary_advertiser_id: Optional[str] = None
        self.available_advertiser_ids: List[str] = []
        self.oauth_client: Optional[SimpleTikTokOAuth] = None
        
    async def initialize(self):
        """Initialize the TikTok Ads MCP Server with credentials check."""
        try:
            # Store app credentials for OAuth login
            self.app_id = os.getenv("TIKTOK_APP_ID")
            self.app_secret = os.getenv("TIKTOK_APP_SECRET")
            access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
            advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
            available_advertiser_ids = os.getenv("TIKTOK_AVAILABLE_ADVERTISER_IDS", "")
            available_advertiser_ids = [x.strip() for x in available_advertiser_ids.split(",") if x.strip()]
            if advertiser_id not in available_advertiser_ids:
                available_advertiser_ids.append(advertiser_id)
            
            if not self.app_id or not self.app_secret:
                raise ValueError(
                    "Missing TikTok API credentials. Provide TIKTOK_APP_ID and TIKTOK_APP_SECRET environment variables."
                )
            
            # Initialize OAuth client
            self.oauth_client = SimpleTikTokOAuth(self.app_id, self.app_secret)
            
            # If access token is provided, authenticate immediately (legacy mode)
            if access_token and advertiser_id:
                logger.info("Using direct token authentication...")
                await self._authenticate_with_tokens(access_token, advertiser_id, available_advertiser_ids)
            else:
                logger.info("OAuth credentials configured. Use the 'tiktok_ads_login' tool to authenticate.")
            
            logger.info("TikTok Ads MCP Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TikTok Ads MCP Server: {e}")
            raise
    
    async def _authenticate_with_tokens(self, access_token: str, advertiser_id: str, available_advertiser_ids: list[str]):
        """Authenticate using provided tokens."""
        # Initialize TikTok client
        self.client = TikTokAdsClient(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=access_token,
            advertiser_id=advertiser_id,
            available_advertiser_ids=available_advertiser_ids,
        )
        
        # Initialize tool modules
        self.campaign_tools = CampaignTools(self.client)
        self.creative_tools = CreativeTools(self.client)
        self.performance_tools = PerformanceTools(self.client)
        self.audience_tools = AudienceTools(self.client)
        self.reporting_tools = ReportingTools(self.client)
        
        self.is_authenticated = True
        self.primary_advertiser_id = advertiser_id
        self.available_advertiser_ids = available_advertiser_ids
        
    async def start_oauth_flow(self, force_reauth: bool = False) -> Dict[str, Any]:
        """Start OAuth flow (non-blocking)."""
        if not self.oauth_client:
            return {"success": False, "error": "OAuth client not initialized"}
        
        try:
            result, token_data = start_manual_oauth(self.app_id, self.app_secret, force_reauth=force_reauth)
            if token_data:
                await self._authenticate_with_tokens(
                    token_data['access_token'], 
                    token_data['primary_advertiser_id'],
                    token_data['advertiser_ids'],
                )
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Failed to start OAuth flow: {e}")
            return {"success": False, "data": {"error": str(e)}}
    
    async def complete_oauth(self, auth_code: str) -> Dict[str, Any]:
        """Complete OAuth flow with authorization code."""
        if not self.oauth_client:
            return {"success": False, "data": {"error": "OAuth client not initialized"}}
        
        try:
            token_data = await self.oauth_client.exchange_code_for_token(auth_code)
            
            if not token_data:
                return {"success": False, "data": {"error": "Failed to exchange authorization code for tokens"}}
            
            if "error_message" in token_data:
                return {"success": False, "data": {"error": token_data["error_message"]}}
            
            # Authenticate with the tokens
            await self._authenticate_with_tokens(
                token_data['access_token'], 
                token_data['primary_advertiser_id'],
                token_data['advertiser_ids'],
            )
            self.available_advertiser_ids = token_data['advertiser_ids']
            self.primary_advertiser_id = token_data['primary_advertiser_id']
            
            logger.info(f"OAuth completed successfully. Using advertiser ID: {token_data['primary_advertiser_id']}")
            
            return {
                "success": True,
                "data": {
                    "message": "Authentication completed successfully",
                    "primary_advertiser_id": token_data['primary_advertiser_id'],
                    "available_advertiser_ids": token_data['advertiser_ids']
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to complete OAuth: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status."""
        if self.is_authenticated:
            # check runtime 
            return {
                'success': True,
                'data': {
                    'status': 'authenticated',
                    "app_id": self.app_id,
                    "available_advertiser_ids": self.available_advertiser_ids,
                    "primary_advertiser_id": self.primary_advertiser_id,
                    "message": "Already Authenticated"
                }
            }
        else:
            oauth_client = SimpleTikTokOAuth(self.app_id, self.app_secret)
            saved_tokens = oauth_client.load_saved_tokens()
            if saved_tokens and saved_tokens.get('access_token'):
                await self._authenticate_with_tokens(
                    saved_tokens['access_token'], 
                    saved_tokens['primary_advertiser_id'],
                    saved_tokens['advertiser_ids'],
                )
                return {
                    'success': True,
                    'data': {
                        'status': 'authenticated',
                        'app_id': self.app_id,
                        'available_advertiser_ids': saved_tokens.get('advertiser_ids', []),
                        'primary_advertiser_id': saved_tokens.get('primary_advertiser_id'),
                        'message': 'Already authenticated with saved tokens',
                    }
                }
            else:
                return {
                    'success': True,
                    'data': {
                        'status': 'not_authenticated',
                        'app_id': self.app_id,
                        'message': 'No saved tokens found. Please use tiktok_ads_login tool to authenticate.'
                    }
                }
    
    async def switch_ad_account(self, advertiser_id: str) -> Dict[str, Any]:
        """Switch to a different advertiser account."""
        if not self.is_authenticated:
            return {"success": False, "error": "Not authenticated. Please login first."}
        
        warning_message = ""
        if advertiser_id not in self.available_advertiser_ids:
            warning_message = f"Warn: Advertiser ID {advertiser_id} maybe not available."
        
        try:
            # Get the current access token
            if self.client:
                access_token = self.client.access_token
                # Re-authenticate with the new advertiser ID using existing method
                await self._authenticate_with_tokens(access_token, advertiser_id, self.available_advertiser_ids)
                
                logger.info(f"Switched to advertiser account: {advertiser_id}")
                
                return {
                    "success": True,
                    "data": {
                        "message": f"switched to advertiser account {advertiser_id}. {warning_message}",
                        "current_advertiser_id": advertiser_id,
                        "available_advertiser_ids": self.available_advertiser_ids
                    }
                }
            else:
                return {"success": False, "error": "Client not initialized"}
                
        except Exception as e:
            logger.error(f"Failed to switch advertiser account: {e}")
            return {"success": False, "error": str(e)}


# Global server instance
tiktok_server = TikTokMCPServer()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available TikTok Ads tools."""
    tools = []
    
    # Authentication tools (always available)
    tools.extend([
        Tool(
            name="tiktok_ads_login",
            description="Start TikTok Ads OAuth authentication flow",
            inputSchema={
                "type": "object",
                "properties": {
                    "force_reauth": {
                        "type": "boolean",
                        "description": "Whether to force reauthentication even if tokens exist. Use when access_token is expired or when operations fail due to lack of permissions and require user re-authorization to complete specific actions."
                    }
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="tiktok_ads_complete_auth",
            description="Complete OAuth authentication with authorization code",
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_code": {
                        "type": "string",
                        "description": "Authorization code from OAuth redirect"
                    }
                },
                "required": ["auth_code"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="tiktok_ads_auth_status",
            description="Check current authentication status with TikTok Ads API",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="tiktok_ads_switch_ad_account",
            description="Switch to a different advertiser account, DO NOT try to switch advertiser account automatically, only if user ask to switch",
            inputSchema={
                "type": "object",
                "properties": {
                    "advertiser_id": {
                        "type": "string",
                        "description": "The advertiser ID to switch to"
                    }
                },
                "required": ["advertiser_id"],
                "additionalProperties": False
            }
        )
    ])
    
    # Campaign management tools
    tools.extend([
        Tool(
            name="tiktok_ads_get_campaigns",
            description="Retrieve all campaigns for the advertiser account",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["ENABLE", "DISABLE", "DELETE"],
                        "description": "Filter campaigns by status"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of campaigns to return"
                    }
                }
            }
        ),
        Tool(
            name="tiktok_ads_get_campaign_details",
            description="Get detailed information about a specific campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "The campaign ID to retrieve details for"
                    }
                },
                "required": ["campaign_id"]
            }
        ),
        Tool(
            name="tiktok_ads_get_adgroups",
            description="Retrieve ad groups for a campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to get ad groups for"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["ENABLE", "DISABLE", "DELETE"],
                        "description": "Filter ad groups by status"
                    }
                },
                "required": ["campaign_id"]
            }
        )
    ])
    
    # Performance analytics tools
    tools.extend([
        Tool(
            name="tiktok_ads_get_campaign_performance",
            description="Get performance metrics for campaigns",
            inputSchema={
                "type": "object",
                "properties": {
                    "campaign_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of campaign IDs to analyze"
                    },
                    "date_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "last_7_days", "last_14_days", "last_30_days"],
                        "description": "Date range for performance data"
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": """
## Metrics to include: 

### attribute metrics:
Attribute metrics, such as ad group names and promotion types, are basic attributes of your campaigns, ad groups, or ads. Attribute metrics are valid only when an ID type of dimension is used.

Field	Type	Description	Detail
advertiser_name	string	Advertiser account name	Supported at Advertiser, Campaign, Ad Group, and Ad level.
advertiser_id	string	Advertiser account ID	Supported at Advertiser, Campaign, Ad Group, and Ad level.
campaign_name	string	Campaign name	Supported at Campaign, Ad Group and Ad level.
campaign_id	string	Campaign ID	Supported at Ad Group and Ad level.
objective_type	string	Advertising objective	Supported at Campaign, Ad Group and Ad level.
split_test	string	Split test status	Supported at Campaign, Ad Group and Ad level.
campaign_budget	string	Campaign budget	Supported at Campaign, Ad Group and Ad level.
campaign_dedicate_type	string	Campaign type	iOS14 Dedicated Campaign or regular campaign. Supported at Campaign, Ad Group and Ad level.
app_promotion_type	string	App promotion type	"Supported at Campaign, Ad Group and Ad level. Enum values: APP_INSTALL, APP_RETARGETING.
APP_INSTALL and APP_RETARGETING will be returned when objective_type is APP_PROMOTION. Otherwise, UNSET will be returned."
adgroup_name	string	Ad group name	Supported at Ad Group and Ad level.
adgroup_id	string	Ad group ID	Supported at Ad level.
placement_type	string	Placement type	Supported at Ad Group and Ad level.
promotion_type	string	Promotion type	It can be app, website, or others. Supported at Ad Group and Ad levels in both synchronous and asynchronous reports.
opt_status	string	Automated creative optimization	Supported at Ad Group and Ad level.
adgroup_download_url	string	Download URL/Website URL	Supported at Ad Group, and Ad level.
profile_image	string	Profile image	Supported at Ad Group and Ad level.
dpa_target_audience_type	string	Target audience type for DPA	The Audience that DPA products target. Supported at Ad Group or Ad levels in both synchronous and asynchronous reports.
budget	string	Ad group budget	Supported at Ad Group and Ad level.
smart_target	string	Optimization goal	Supported at Ad Group and Ad level.
pricing_categoryTo be deprecated	string	Billing Event	"Supported at Ad Group and Ad level.
If you want to retrieve the billing event of your ads, use the new metric billing_event."
billing_event	string	Billing Event	"Supported at Ad Group and Ad level.
Example: ""Clicks"", ""Impression""."
bid_strategy	string	Bid strategy	Supported at Ad Group and Ad level.
bid	string	Bid	Supported at Ad Group and Ad level.
bid_secondary_goal	string	Bid for secondary goal	Supported at Ad Group and Ad level.
aeo_type	string	App Event Optimization Type	Supported at Ad Group and Ad level. (Already supported at Ad Group level, and will be supported at Ad level)
ad_name	string	Ad name	Supported at Ad level.
ad_id	string	Ad ID	Supported at Ad level.
ad_text	string	Ad title	Supported at Ad level.
call_to_action	string	Call to action	Supported at Ad level.
ad_profile_image	string	Profile image (Ad level)	Supported at Ad level.
ad_url	string	URL (Ad level)	Supported at Ad level.
tt_app_id	string	TikTok App ID	TikTok App ID, the App ID you used when creating an Ad Group. Supported at Ad Group and Ad level. Returned if the promotion type of one Ad Group is App.
tt_app_name	string	TikTok App Name	The name of your TikTok App. Supported at Ad Group and Ad level. Returned if the promotion type of one Ad Group is App.
mobile_app_id	string	Mobile App ID	Mobile App ID.Examples are, App Store: https://apps.apple.com/us/app/angry-birds/id343200656; Google Play：https://play.google.com/store/apps/details?id=com.rovio.angrybirds.Supported at Ad Group and Ad level. Returned if the promotion type of one Ad Group is App.
image_mode	string	Format	Supported at Ad level.
currency	string	currency	The currency code, e. g. USD. Note that if you want to use currency as metrics, then the dimensions field in your request must include adgroup_id/ad_id/campaign_id/advertiser_id.
is_aco	boolean	Whether the ad is an automated ad or a Smart Creative ad. Set to True for an automated ad or Smart Creative ad.	Supported at AUCTION_ADGROUP level.
is_smart_creative	boolean	Whether the ad is a Smart Creative ad.	Supported at AUCTION_AD level.

### Core metrics
Core metrics provide fundamental insights into your advertising performance, covering essential aspects such as cost and impressions.

Field	Type	Description	Detail
spend	string	Cost	Sum of your total ad spend.
billed_cost	string	Net cost	"Sum of your total ad spend, excluding ad credit or coupons used. Note:This metric is only supported in synchronous basic reports. This metric might delay up to 11 hours, with records only available from September 1, 2023."
cash_spend	string	Cost Charged by Cash	The estimated amount of money you've spent on your campaign, ad group, or ad during its schedule charged by cash. (This metric can be required at the advertiser level only and lifetime, hourly breakdown is not supported.) Please note that there may be a delay from 24h to 48h between when you were charged and when you can see it through the API.
voucher_spend	string	Cost Charged by Voucher	The estimated amount of money you've spent on your campaign, ad group, or ad during its schedule charged by voucher. (This metric can be required at the advertiser level only and lifetime, hourly breakdown is not supported.) Please note that there may be a delay from 24h to 48h between when you were charged and when you can see it through the API.
cpc	string	CPC (destination)	Average cost of each click to a specified destination.
cpm	string	CPM	Average amount you spent per 1,000 impressions.
impressions	string	Impressions	Number of times your ads were shown.
gross_impressions	string	Gross Impressions (Includes Invalid Impressions)	Number of times your ads were shown, including invalid impressions.
clicks	string	Clicks (destination)	Number of clicks from your ads to a specified destination.
ctr	string	CTR (destination)	Percentage of impressions that resulted in a destination click out of all impressions.
reach	string	Reach	Number of unique users who saw your ads at least once.
cost_per_1000_reached	string	Cost per 1,000 people reached	Average cost to reach 1,000 unique users.
frequency	string	Frequency	The average number of times each user saw your ad over a given time period.
conversion	string	Conversions	Number of times your ad resulted in the optimization event you selected.
cost_per_conversion	string	Cost per conversion	Average amount spent on a conversion.
conversion_rate	string	Conversion rate (CVR, clicks)	"Percentage of results you received out of all destination clicks on your ads. Note: Starting late October, 2023, the calculation logic for this metric will be updated to be impression-based (the same as conversion_rate_v2). To ensure a smooth API integration and avoid disruptions caused by the change in calculation logic, we recommend you switch to using the impression-based metric conversion_rate_v2 as soon as possible."
conversion_rate_v2	string	Conversion rate (CVR)	Percentage of results you received out of all impressions on your ads.
real_time_conversion	string	Conversions by conversion time	Number of times your ad resulted in the optimization event you selected.
real_time_cost_per_conversion	string	Cost per conversion by conversion time	Average amount spent on a conversion.
real_time_conversion_rate	string	Real-time conversion rate (CVR, clicks)	"Percentage of conversions you received out of all destination clicks on your ads. Note: Starting late October, 2023, the calculation logic for this metric will be updated to be impression-based (the same as real_time_conversion_rate_v2). To ensure a smooth API integration and avoid disruptions caused by the change in calculation logic, we recommend you switch to using the impression-based metric real_time_conversion_rate_v2 as soon as possible."
real_time_conversion_rate_v2	string	Conversion rate (CVR) by conversion time	Percentage of conversions you received out of all impressions on your ads.
result	string	Results	Number of times your ad resulted in an intended outcome based on your campaign objective and optimization goal.
cost_per_result	string	Cost per result	Average cost per each result from your ads.
result_rate	string	Result rate	Percentage of results that happened out of all impressions on your ads.
real_time_result	string	Real-time results	Number of times your ad resulted in an intended outcome based on your campaign objective and optimization goal.
real_time_cost_per_result	string	Real-time cost per result	Average cost per each result from your ads.
real_time_result_rate	string	Real-time result rate	Percentage of results that happened out of all impressions on your ads.
secondary_goal_result	string	Deep funnel result	Number of times your ad resulted in an intended outcome based on the deep funnel event you selected.
cost_per_secondary_goal_result	string	Cost per deep funnel result	Average cost per each deep funnel result from your ads.
secondary_goal_result_rate	string	Deep funnel result rate	Percentage of deep funnel results out of total impressions on your ads.
"""
                    }
                },
                "required": ["campaign_ids", "date_range"]
            }
        ),
        Tool(
            name="tiktok_ads_get_adgroup_performance",
            description="Get performance metrics for ad groups",
            inputSchema={
                "type": "object",
                "properties": {
                    "adgroup_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ad group IDs to analyze"
                    },
                    "date_range": {
                        "type": "string",
                        "enum": ["today", "yesterday", "last_7_days", "last_14_days", "last_30_days"],
                        "description": "Date range for performance data"
                    },
                    "breakdowns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Data breakdowns: age, gender, country, placement"
                    }
                },
                "required": ["adgroup_ids", "date_range"]
            }
        )
    ])
    
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for TikTok Ads operations."""
    try:
        result = None
        
        # Authentication tools (always available)
        if name == "tiktok_ads_login":
            force_reauth = arguments.get("force_reauth")
            result =  await tiktok_server.start_oauth_flow(force_reauth=force_reauth)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "tiktok_ads_complete_auth":
            auth_code = arguments.get("auth_code")
            result = await tiktok_server.complete_oauth(auth_code)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "tiktok_ads_auth_status":
            result =  await tiktok_server.get_auth_status()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "tiktok_ads_switch_ad_account":
            advertiser_id = arguments.get("advertiser_id")
            result = await tiktok_server.switch_ad_account(advertiser_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Check if authenticated for other tools
        if not tiktok_server.client or not tiktok_server.is_authenticated:
            return [TextContent(
                type="text",
                text="Error: Not authenticated with TikTok Ads API. Please use the 'tiktok_ads_login' tool first." + str(tiktok_server.client) + str(tiktok_server.is_authenticated)
            )]
        
        # Campaign management tools
        if name == "tiktok_ads_get_campaigns":
            result = await tiktok_server.campaign_tools.get_campaigns(**arguments)
        elif name == "tiktok_ads_get_campaign_details":
            result = await tiktok_server.campaign_tools.get_campaign_details(**arguments)
        elif name == "tiktok_ads_create_campaign":
            result = await tiktok_server.campaign_tools.create_campaign(**arguments)
        elif name == "tiktok_ads_get_adgroups":
            result = await tiktok_server.campaign_tools.get_adgroups(**arguments)
        elif name == "tiktok_ads_create_adgroup":
            result = await tiktok_server.campaign_tools.create_adgroup(**arguments)
            
        # Performance tools
        elif name == "tiktok_ads_get_campaign_performance":
            result = await tiktok_server.performance_tools.get_campaign_performance(**arguments)
        elif name == "tiktok_ads_get_adgroup_performance":
            result = await tiktok_server.performance_tools.get_adgroup_performance(**arguments)
            
        # Creative tools
        elif name == "tiktok_ads_get_ad_creatives":
            result = await tiktok_server.creative_tools.get_ad_creatives(**arguments)
        elif name == "tiktok_ads_upload_image":
            result = await tiktok_server.creative_tools.upload_image(**arguments)
            
        # Audience tools
        elif name == "tiktok_ads_get_custom_audiences":
            result = await tiktok_server.audience_tools.get_custom_audiences(**arguments)
        elif name == "tiktok_ads_get_targeting_options":
            result = await tiktok_server.audience_tools.get_targeting_options(**arguments)
            
        # Reporting tools
        elif name == "tiktok_ads_generate_report":
            result = await tiktok_server.reporting_tools.generate_report(**arguments)
            
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]
        
        return [TextContent(
            type="text",
            text=str(result)
        )]
        
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main():
    """Main entry point for the TikTok Ads MCP server."""
    try:
        # Initialize the server
        await tiktok_server.initialize()
        
        # Run the MCP server
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="tiktok-ads-mcp",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(listChanged=True),
                        logging=LoggingCapability()
                    )
                )
            )
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())