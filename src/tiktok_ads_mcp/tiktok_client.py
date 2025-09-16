"""TikTok Ads API client implementation."""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode
from six import string_types
from six.moves.urllib.parse import urlencode, urlunparse  # noqa

import httpx
from pydantic import BaseModel


class TikTokAdsClient:
    """TikTok Ads API client for making authenticated requests."""
    
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
    
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        access_token: str,
        advertiser_id: str,
        available_advertiser_ids: list,
    ):
        """Initialize TikTok Ads client.
        
        Args:
            app_id: TikTok app ID
            app_secret: TikTok app secret
            access_token: Access token for API requests
            advertiser_id: Advertiser account ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
        self.advertiser_id = advertiser_id
        self.available_advertiser_ids = available_advertiser_ids
        self.client = httpx.AsyncClient(timeout=30.0)
        
        if not all([app_id, app_secret, access_token, advertiser_id]):
            raise ValueError("All TikTok API credentials are required")
    
    def _generate_signature(self, params: Dict[str, Any], path: str) -> str:
        """Generate request signature for TikTok API."""
        # Sort parameters by key
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        
        # Create signature string
        sig_string = path + "?" + query_string
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.app_secret.encode(),
            sig_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to TikTok Ads API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            files: Files for upload
            
        Returns:
            API response data
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        # Common parameters
        common_params = {
            "advertiser_id": self.advertiser_id,
            "advertiser_ids": [self.advertiser_id],
        }
        headers = {
            "Access-Token": self.access_token,
        }
        
        # Merge with provided params
        if params:
            common_params.update(params)
        query_string = urlencode({k: v if isinstance(v, string_types) else json.dumps(v) for k, v in common_params.items()})
        try:
            if method.upper() == "GET":
                response = await self.client.get(url + "?" + query_string, headers=headers)
            elif method.upper() == "POST":
                if files:
                    # Multipart form upload
                    response = await self.client.post(
                        url,
                        params=common_params,
                        files=files,
                        data=data or {},
                        headers=headers,
                    )
                else:
                    # JSON POST
                    response = await self.client.post(
                        url,
                        params=common_params,
                        json=data or {},
                        headers=headers,
                    )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            # Check TikTok API response status
            if result.get("code") != 0:
                raise Exception(f"TikTok API Error: {result.get('message', 'Unknown error')}")
            
            return result
            
        except httpx.HTTPError as e:
            raise Exception(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse API response: {e}")
    
    async def get_campaigns(
        self,
        status: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Get campaigns for the advertiser."""
        params = {
            "page": page,
            "page_size": limit,
        }
        if status:
            params["filtering"] = json.dumps({"primary_status": status})
        
        return await self._make_request("GET", "campaign/get/", params=params)
    
    async def get_campaign_details(self, campaign_id: str) -> Dict[str, Any]:
        """Get details for a specific campaign."""
        params = {
            "filtering": json.dumps({"campaign_ids": [campaign_id]})
        }
        return await self._make_request("GET", "campaign/get/", params=params)
    
    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new campaign."""
        return await self._make_request("POST", "campaign/create/", data=campaign_data)
    
    async def get_adgroups(
        self,
        campaign_id: str,
        status: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Get ad groups for a campaign."""
        filtering = {"campaign_ids": [campaign_id]}
        if status:
            filtering["primary_status"] = status
        
        params = {
            "filtering": json.dumps(filtering),
            "page": page,
            "page_size": limit,
        }
        return await self._make_request("GET", "adgroup/get/", params=params)
    
    async def create_adgroup(self, adgroup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new ad group."""
        return await self._make_request("POST", "adgroup/create/", data=adgroup_data)
    
    async def get_performance_data(
        self,
        level: str,
        entity_ids: List[str],
        metrics: List[str],
        start_date: str,
        end_date: str,
        dimensions: [List[str]],
        breakdowns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get performance data for campaigns, ad groups, or ads.
        
        Args:
            level: Data level - 'AUCTION_CAMPAIGN', 'AUCTION_ADGROUP', or 'AUCTION_AD'
            entity_ids: List of campaign/adgroup/ad IDs
            metrics: List of metrics to retrieve
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            breakdowns: Optional data breakdowns
        """
        params = {
            "report_type": "BASIC",
            "data_level": level,
            "start_date": start_date,
            "end_date": end_date,
            "metrics": metrics,
            "dimensions": dimensions,
            "enable_total_metrics": True,
        }
        
        # Set filtering based on level
        if level == "AUCTION_CAMPAIGN":
            params["filtering"] = [
                {
                    "field_name": "campaign_ids",
                    "filter_type": "IN",
                    "filter_value": json.dumps(entity_ids)
                }
            ]
        elif level == "AUCTION_ADGROUP":
            params["filtering"] = [
                {
                    "field_name": "adgroup_ids",
                    "filter_type": "IN",
                    "filter_value": json.dumps(entity_ids)
                }
            ]
        elif level == "AUCTION_AD":
            params["filtering"] = [
                {
                    "field_name": "ad_ids",
                    "filter_type": "IN",
                    "filter_value": json.dumps(entity_ids)
                }
            ]
        
        return await self._make_request("GET", "report/integrated/get/", params=params)
    
    async def get_ad_creatives(self, limit: int = 10, page: int = 1) -> Dict[str, Any]:
        """Get ad creatives for the advertiser."""
        params = {
            "page": page,
            "page_size": limit,
        }
        return await self._make_request("GET", "creative/get/", params=params)
    
    async def upload_image(
        self,
        image_path: str,
        upload_type: str = "UPLOAD_BY_FILE",
    ) -> Dict[str, Any]:
        """Upload an image file for ad creatives."""
        with open(image_path, "rb") as f:
            files = {"image_file": f}
            data = {"upload_type": upload_type}
            return await self._make_request("POST", "file/image/ad/upload/", data=data, files=files)
    
    async def get_custom_audiences(self, limit: int = 10, page: int = 1) -> Dict[str, Any]:
        """Get custom audiences for the advertiser."""
        params = {
            "page": page,
            "page_size": limit,
        }
        return await self._make_request("GET", "dmp/custom_audience/list/", params=params)
    
    async def get_targeting_options(
        self,
        option_type: str,
        country_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get targeting options for campaigns."""
        params = {"type": option_type}
        if country_code:
            params["country_code"] = country_code
        
        return await self._make_request("GET", "tools/target_recommend/", params=params)
    
    async def create_report_task(
        self,
        report_type: str,
        dimensions: List[str],
        metrics: List[str],
        start_date: str,
        end_date: str,
        filtering: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an asynchronous report generation task."""
        data = {
            "report_type": report_type,
            "data_level": "AUCTION_CAMPAIGN",  # Default to campaign level
            "dimensions": dimensions,
            "metrics": metrics,
            "start_date": start_date,
            "end_date": end_date,
        }
        
        if filtering:
            data["filtering"] = filtering
        
        return await self._make_request("POST", "report/task/create/", data=data)
    
    async def get_report_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check the status of a report generation task."""
        params = {"task_id": task_id}
        return await self._make_request("GET", "report/task/check/", params=params)
    
    async def download_report(self, task_id: str) -> Dict[str, Any]:
        """Download a completed report."""
        params = {"task_id": task_id}
        return await self._make_request("GET", "report/task/download/", params=params)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()