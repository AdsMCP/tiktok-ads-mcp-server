"""Performance analytics tools for TikTok Ads MCP server."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..tiktok_client import TikTokAdsClient


class PerformanceTools:
    """Tools for retrieving TikTok Ads performance data and analytics."""
    
    def __init__(self, client: TikTokAdsClient):
        self.client = client
    
    def _get_date_range(self, date_range: str) -> tuple[str, str]:
        """Convert date range string to start and end dates.
        
        Args:
            date_range: Date range string (today, yesterday, last_7_days, etc.)
            
        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        today = datetime.now()
        
        if date_range == "today":
            start_date = end_date = today.strftime("%Y-%m-%d")
        elif date_range == "yesterday":
            yesterday = today - timedelta(days=1)
            start_date = end_date = yesterday.strftime("%Y-%m-%d")
        elif date_range == "last_7_days":
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_range == "last_14_days":
            start_date = (today - timedelta(days=14)).strftime("%Y-%m-%d")
            end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_range == "last_30_days":
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            # Default to last 7 days
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        return start_date, end_date
    

    async def get_campaign_performance(
        self,
        campaign_ids: List[str],
        date_range: str = "last_7_days",
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get performance metrics for campaigns.
        
        Args:
            campaign_ids: List of campaign IDs to analyze
            date_range: Date range for performance data
            metrics: Specific metrics to include (optional)
            
        Returns:
            Campaign performance data
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            dimensions = [
                "campaign_id"
            ]
            
            # Default metrics if not specified
            common_metrics = ["campaign_name"]
            if not metrics:
                metrics = [
                    "impressions", "clicks", "conversion", "spend",
                    "ctr", "cpm", "cpc", "conversion_rate_v2"
                ]
            else:
                rewrite_metrics = {
                    "conversions": "conversion"
                }
                metrics = [rewrite_metrics.get(m, m) for m in metrics]
            
            result = await self.client.get_performance_data(
                level="AUCTION_CAMPAIGN",
                entity_ids=campaign_ids,
                metrics=common_metrics+metrics,
                dimensions=dimensions,
                start_date=start_date,
                end_date=end_date,
            )
            
            performance_data = [item.get("metrics", {}) for item in  result.get("data", {}).get("list", [])]
            total_metrics = result.get("data", {}).get("total_metrics", {})
            
            
            return {
                "success": True,
                "date_range": f"{start_date} to {end_date}",
                "campaigns": performance_data,
                "totals": total_metrics,
                "campaign_count": len(performance_data),
                "message": f"Retrieved performance data for {len(performance_data)} campaigns"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "campaign_ids": campaign_ids,
                "date_range": date_range,
                "message": "Failed to retrieve campaign performance data"
            }
    
    async def get_adgroup_performance(
        self,
        adgroup_ids: List[str],
        date_range: str = "last_7_days",
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get performance metrics for ad groups.
        
        Args:
            adgroup_ids: List of ad group IDs to analyze
            date_range: Date range for performance data
            breakdowns: Data breakdowns (age, gender, country, placement)
            
        Returns:
            Ad group performance data
        """
        try:
            start_date, end_date = self._get_date_range(date_range)
            dimensions = [
                "adgroup_id"
            ]
            # Standard metrics for ad group analysis
            common_metrics = ["campaign_id", "campaign_name", "adgroup_name"]
            if not metrics:
                metrics = [
                    "impressions", "clicks", "conversion", "spend",
                    "ctr", "cpm", "cpc", "conversion_rate_v2"
                ]
            else:
                rewrite_metrics = {
                    "conversions": "conversion"
                }
                metrics = [rewrite_metrics.get(m, m) for m in metrics]
            result = await self.client.get_performance_data(
                level="AUCTION_ADGROUP",
                entity_ids=adgroup_ids,
                metrics=common_metrics+metrics,
                start_date=start_date,
                end_date=end_date,
                dimensions=dimensions,
            )
            
            performance_data = [item.get("metrics", {}) for item in  result.get("data", {}).get("list", [])]
            total_metrics = result.get("data", {}).get("total_metrics", {})
            
            
            return {
                "success": True,
                "date_range": f"{start_date} to {end_date}",
                "adgroups": performance_data,
                "totals": total_metrics,
                "adgroup_count": len(performance_data),
                "message": f"Retrieved performance data for {len(performance_data)} ad groups"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "adgroup_ids": adgroup_ids,
                "date_range": date_range,
                "message": "Failed to retrieve ad group performance data"
            }