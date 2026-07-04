"""Campaign management tools for TikTok Ads MCP server."""

from typing import Any, Dict, List, Optional

from ..tiktok_client import TikTokAdsClient


class CampaignTools:
    """Tools for managing TikTok Ads campaigns and ad groups."""
    
    def __init__(self, client: TikTokAdsClient):
        self.client = client

    @staticmethod
    def _list_response(
        entity_type: str,
        items: List[Dict[str, Any]],
        total_count: int,
        message: str,
        **extra: Any,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "data": {
                "entity_type": entity_type,
                "items": items,
                "total_count": total_count,
                "message": message,
                **extra,
            },
        }

    @staticmethod
    def _detail_response(
        entity_type: str,
        item_id_key: str,
        item_id: str,
        item: Optional[Dict[str, Any]],
        message: str,
    ) -> Dict[str, Any]:
        if item is None:
            return {
                "success": False,
                "data": {
                    "entity_type": entity_type,
                    item_id_key: item_id,
                    "item": None,
                    "not_found": True,
                    "error": f"{entity_type.replace('_', ' ').title()} not found",
                },
            }

        return {
            "success": True,
            "data": {
                "entity_type": entity_type,
                item_id_key: item_id,
                "item": item,
                "message": message,
            },
        }

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

            return self._list_response(
                entity_type="campaign",
                items=campaigns,
                total_count=result.get("data", {}).get("page_info", {}).get("total_number", 0),
                message=f"Retrieved {len(campaigns)} campaigns",
            )
            
        except Exception as e:
            return {
                "success": False,
                "data": {
                    "entity_type": "campaign",
                    "error": str(e),
                    "message": "Failed to retrieve campaigns",
                },
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
            campaign = campaigns[0] if campaigns else None

            return self._detail_response(
                entity_type="campaign",
                item_id_key="campaign_id",
                item_id=campaign_id,
                item=campaign,
                message=f"Retrieved details for campaign {campaign_id}",
            )
            
        except Exception as e:
            return {
                "success": False,
                "data": {
                    "entity_type": "campaign",
                    "campaign_id": campaign_id,
                    "error": str(e),
                    "message": "Failed to retrieve campaign details",
                },
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

            return self._list_response(
                entity_type="adgroup",
                items=adgroups,
                total_count=result.get("data", {}).get("page_info", {}).get("total_number", 0),
                message=f"Retrieved {len(adgroups)} ad groups for campaign {campaign_id}",
                campaign_id=campaign_id,
            )
            
        except Exception as e:
            return {
                "success": False,
                "data": {
                    "entity_type": "adgroup",
                    "campaign_id": campaign_id,
                    "error": str(e),
                    "message": "Failed to retrieve ad groups",
                },
            }

    async def get_adgroup_details(self, adgroup_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific ad group."""
        try:
            result = await self.client.get_adgroup_details(adgroup_id)
            adgroups = result.get("data", {}).get("list", [])
            adgroup = adgroups[0] if adgroups else None
            return self._detail_response(
                entity_type="adgroup",
                item_id_key="adgroup_id",
                item_id=adgroup_id,
                item=adgroup,
                message=f"Retrieved details for ad group {adgroup_id}",
            )

        except Exception as e:
            return {
                "success": False,
                "data": {
                    "entity_type": "adgroup",
                    "adgroup_id": adgroup_id,
                    "error": str(e),
                    "message": "Failed to retrieve ad group details",
                },
            }

    async def get_ads(
        self,
        campaign_ids: Optional[List[str]] = None,
        adgroup_ids: Optional[List[str]] = None,
        ad_ids: Optional[List[str]] = None,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Get ads with optional campaign, ad group, ad ID, or status filters."""
        try:
            result = await self.client.get_ads(
                campaign_ids=campaign_ids,
                adgroup_ids=adgroup_ids,
                ad_ids=ad_ids,
                status=status,
                limit=limit,
            )
            ads = result.get("data", {}).get("list", [])
            return self._list_response(
                entity_type="ad",
                items=ads,
                total_count=result.get("data", {}).get("page_info", {}).get("total_number", 0),
                message=f"Retrieved {len(ads)} ads",
                applied_filters={
                    "campaign_ids": campaign_ids or [],
                    "adgroup_ids": adgroup_ids or [],
                    "ad_ids": ad_ids or [],
                    "status": status,
                },
            )
        except Exception as e:
            return {
                "success": False,
                "data": {
                    "entity_type": "ad",
                    "error": str(e),
                    "message": "Failed to retrieve ads",
                },
            }

    async def get_ad_details(self, ad_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific ad."""
        try:
            result = await self.client.get_ad_details(ad_id)
            ads = result.get("data", {}).get("list", [])
            ad = ads[0] if ads else None
            return self._detail_response(
                entity_type="ad",
                item_id_key="ad_id",
                item_id=ad_id,
                item=ad,
                message=f"Retrieved details for ad {ad_id}",
            )
        except Exception as e:
            return {
                "success": False,
                "data": {
                    "entity_type": "ad",
                    "ad_id": ad_id,
                    "error": str(e),
                    "message": "Failed to retrieve ad details",
                },
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
