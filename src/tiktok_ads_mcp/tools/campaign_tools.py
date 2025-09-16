"""Campaign management tools for TikTok Ads MCP server."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..tiktok_client import TikTokAdsClient


class CampaignTools:
    """Tools for managing TikTok Ads campaigns and ad groups."""
    
    def __init__(self, client: TikTokAdsClient):
        self.client = client
    
    async def get_campaigns(
        self,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get campaigns for the advertiser account.
        
        Args:
            status: Filter campaigns by status (ENABLE, DISABLE, DELETE)
            limit: Maximum number of campaigns to return
            
        Returns:
            Campaign data and metadata
        """
        try:
            result = await self.client.get_campaigns(status=status, limit=limit)
            
            campaigns = result.get("data", {}).get("list", [])
            
            # Format response for better readability
            formatted_campaigns = []
            for campaign in campaigns:
                formatted_campaign = {
                    "campaign_id": campaign.get("campaign_id"),
                    "campaign_name": campaign.get("campaign_name"),
                    "objective_type": campaign.get("objective_type"),
                    "status": campaign.get("primary_status"),
                    "budget": campaign.get("budget"),
                    "budget_mode": campaign.get("budget_mode"),
                    "create_time": campaign.get("create_time"),
                    "modify_time": campaign.get("modify_time"),
                }
                formatted_campaigns.append(formatted_campaign)
            
            return {
                "success": True,
                "data": {
                    "campaigns": formatted_campaigns,
                    "total_count": result.get("data", {}).get("page_info", {}).get("total_number", 0),
                    "message": f"Retrieved {len(formatted_campaigns)} campaigns"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": {
                    "error": str(e),
                    "message": "Failed to retrieve campaigns"
                }
            }
    
    async def get_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific campaign.
        
        Args:
            campaign_id: The campaign ID to retrieve details for
            
        Returns:
            Detailed campaign information
        """
        try:
            result = await self.client.get_campaign_details(campaign_id)
            
            campaigns = result.get("data", {}).get("list", [])
            if not campaigns:
                return {
                    "success": False,
                    "data": {
                        "error": "Campaign not found",
                        "campaign_id": campaign_id
                    }
                }
            
            campaign = campaigns[0]
            
            # Format detailed campaign info
            campaign_details = {
                "campaign_id": campaign.get("campaign_id"),
                "campaign_name": campaign.get("campaign_name"),
                "advertiser_id": campaign.get("advertiser_id"),
                "objective_type": campaign.get("objective_type"),
                "status": {
                    "primary_status": campaign.get("primary_status"),
                    "secondary_status": campaign.get("secondary_status"),
                },
                "budget_info": {
                    "budget": campaign.get("budget"),
                    "budget_mode": campaign.get("budget_mode"),
                    "spent_budget": campaign.get("spent_budget", 0),
                },
                "schedule": {
                    "schedule_type": campaign.get("schedule_type"),
                    "schedule_start_time": campaign.get("schedule_start_time"),
                    "schedule_end_time": campaign.get("schedule_end_time"),
                },
                "special_industries": campaign.get("special_industries", []),
                "create_time": campaign.get("create_time"),
                "modify_time": campaign.get("modify_time"),
            }
            
            return {
                "success": True,
                "data": {
                    "campaign": campaign_details,
                    "message": f"Retrieved details for campaign {campaign_id}"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "campaign_id": campaign_id,
                "message": "Failed to retrieve campaign details"
            }
    
    async def create_campaign(
        self,
        name: str,
        objective: str,
        budget: float,
        special_industries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new advertising campaign.
        
        Args:
            name: Campaign name
            objective: Campaign objective (REACH, TRAFFIC, APP_INSTALL, etc.)
            budget: Daily budget in advertiser currency
            special_industries: Special industry categories if applicable
            
        Returns:
            Created campaign information
        """
        try:
            # Prepare campaign data
            campaign_data = {
                "campaign_name": name,
                "objective_type": objective,
                "budget_mode": "BUDGET_MODE_DAY",
                "budget": budget,
                "schedule_type": "SCHEDULE_FROM_NOW",
            }
            
            if special_industries:
                campaign_data["special_industries"] = special_industries
            
            result = await self.client.create_campaign(campaign_data)
            
            campaign_id = result.get("data", {}).get("campaign_id")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "campaign_name": name,
                "objective": objective,
                "budget": budget,
                "message": f"Successfully created campaign '{name}' with ID: {campaign_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create campaign '{name}'"
            }
    
    async def get_adgroups(
        self,
        campaign_id: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get ad groups for a campaign.
        
        Args:
            campaign_id: Campaign ID to get ad groups for
            status: Filter ad groups by status (ENABLE, DISABLE, DELETE)
            limit: Maximum number of ad groups to return
            
        Returns:
            Ad group data and metadata
        """
        try:
            result = await self.client.get_adgroups(
                campaign_id=campaign_id,
                status=status,
                limit=limit
            )
            
            adgroups = result.get("data", {}).get("list", [])
            
            # Format ad groups for better readability
            formatted_adgroups = []
            for adgroup in adgroups:
                formatted_adgroup = {
                    "adgroup_id": adgroup.get("adgroup_id"),
                    "adgroup_name": adgroup.get("adgroup_name"),
                    "campaign_id": adgroup.get("campaign_id"),
                    "status": adgroup.get("primary_status"),
                    "placement_type": adgroup.get("placement_type"),
                    "budget": adgroup.get("budget"),
                    "bid_type": adgroup.get("bid_type"),
                    "optimization_goal": adgroup.get("optimization_goal"),
                    "create_time": adgroup.get("create_time"),
                    "modify_time": adgroup.get("modify_time"),
                }
                formatted_adgroups.append(formatted_adgroup)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "adgroups": formatted_adgroups,
                "total_count": result.get("data", {}).get("page_info", {}).get("total_number", 0),
                "message": f"Retrieved {len(formatted_adgroups)} ad groups for campaign {campaign_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "campaign_id": campaign_id,
                "message": "Failed to retrieve ad groups"
            }
    
    async def create_adgroup(
        self,
        campaign_id: str,
        name: str,
        placement_type: str,
        budget: float,
        bid_type: str = "BID_TYPE_NO_BID",
    ) -> Dict[str, Any]:
        """Create a new ad group within a campaign.
        
        Args:
            campaign_id: Parent campaign ID
            name: Ad group name
            placement_type: Ad placement strategy (PLACEMENT_TYPE_AUTOMATIC, PLACEMENT_TYPE_NORMAL)
            budget: Daily budget for ad group
            bid_type: Bidding strategy (BID_TYPE_NO_BID, BID_TYPE_CUSTOM)
            
        Returns:
            Created ad group information
        """
        try:
            # Prepare ad group data
            adgroup_data = {
                "campaign_id": campaign_id,
                "adgroup_name": name,
                "placement_type": placement_type,
                "budget_mode": "BUDGET_MODE_DAY",
                "budget": budget,
                "bid_type": bid_type,
                "optimization_goal": "CLICK",  # Default optimization goal
                "schedule_type": "SCHEDULE_FROM_NOW",
            }
            
            result = await self.client.create_adgroup(adgroup_data)
            
            adgroup_id = result.get("data", {}).get("adgroup_id")
            
            return {
                "success": True,
                "adgroup_id": adgroup_id,
                "adgroup_name": name,
                "campaign_id": campaign_id,
                "placement_type": placement_type,
                "budget": budget,
                "message": f"Successfully created ad group '{name}' with ID: {adgroup_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "campaign_id": campaign_id,
                "message": f"Failed to create ad group '{name}'"
            }