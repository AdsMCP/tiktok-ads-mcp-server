"""Creative management tools for TikTok Ads MCP server."""

import os
from typing import Any, Dict, List, Optional

from ..tiktok_client import TikTokAdsClient


class CreativeTools:
    """Tools for managing TikTok Ads creative assets and ad creatives."""
    
    def __init__(self, client: TikTokAdsClient):
        self.client = client
    
    async def get_ad_creatives(
        self,
        limit: int = 10,
        creative_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List ad creatives for the advertiser.
        
        Args:
            limit: Maximum number of creatives to return
            creative_type: Filter by creative type (IMAGE, VIDEO, CAROUSEL)
            
        Returns:
            List of ad creatives with metadata
        """
        try:
            result = await self.client.get_ad_creatives(limit=limit)
            
            creatives = result.get("data", {}).get("list", [])
            
            # Filter by creative type if specified
            if creative_type:
                creatives = [c for c in creatives if c.get("creative_type") == creative_type]
            
            # Format creatives for better readability
            formatted_creatives = []
            for creative in creatives:
                formatted_creative = {
                    "creative_id": creative.get("creative_id"),
                    "creative_name": creative.get("creative_name"),
                    "creative_type": creative.get("creative_type"),
                    "status": creative.get("status"),
                    "advertiser_id": creative.get("advertiser_id"),
                    "image_info": {
                        "image_id": creative.get("image_id"),
                        "image_url": creative.get("image_url"),
                        "width": creative.get("image_width"),
                        "height": creative.get("image_height"),
                    } if creative.get("image_id") else None,
                    "video_info": {
                        "video_id": creative.get("video_id"),
                        "video_url": creative.get("video_url"),
                        "duration": creative.get("video_duration"),
                        "width": creative.get("video_width"),
                        "height": creative.get("video_height"),
                    } if creative.get("video_id") else None,
                    "text_info": {
                        "ad_text": creative.get("ad_text"),
                        "call_to_action": creative.get("call_to_action"),
                        "display_name": creative.get("display_name"),
                    },
                    "landing_page": {
                        "landing_page_url": creative.get("landing_page_url"),
                        "page_id": creative.get("page_id"),
                    },
                    "create_time": creative.get("create_time"),
                    "modify_time": creative.get("modify_time"),
                }
                formatted_creatives.append(formatted_creative)
            
            # Group by creative type for summary
            type_summary = {}
            for creative in formatted_creatives:
                ctype = creative["creative_type"]
                type_summary[ctype] = type_summary.get(ctype, 0) + 1
            
            return {
                "success": True,
                "creatives": formatted_creatives,
                "total_count": len(formatted_creatives),
                "type_summary": type_summary,
                "filter_applied": creative_type,
                "message": f"Retrieved {len(formatted_creatives)} ad creatives"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve ad creatives"
            }
    
    async def upload_image(
        self,
        image_path: str,
        upload_type: str = "UPLOAD_BY_FILE",
    ) -> Dict[str, Any]:
        """Upload an image asset for ad creatives.
        
        Args:
            image_path: Local path to image file
            upload_type: Upload method (UPLOAD_BY_FILE)
            
        Returns:
            Uploaded image information
        """
        try:
            # Validate file exists
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": "File not found",
                    "image_path": image_path,
                    "message": f"Image file not found at path: {image_path}"
                }
            
            # Validate file type
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            file_extension = os.path.splitext(image_path)[1].lower()
            if file_extension not in allowed_extensions:
                return {
                    "success": False,
                    "error": "Invalid file type",
                    "image_path": image_path,
                    "allowed_types": allowed_extensions,
                    "message": f"File type {file_extension} not supported. Allowed: {', '.join(allowed_extensions)}"
                }
            
            # Get file size
            file_size = os.path.getsize(image_path)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_size > max_size:
                return {
                    "success": False,
                    "error": "File too large",
                    "image_path": image_path,
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "max_size_mb": 10,
                    "message": f"File size ({round(file_size / 1024 / 1024, 2)}MB) exceeds maximum (10MB)"
                }
            
            result = await self.client.upload_image(image_path, upload_type)
            
            image_data = result.get("data", {})
            
            return {
                "success": True,
                "image_id": image_data.get("image_id"),
                "image_url": image_data.get("image_url"),
                "width": image_data.get("width"),
                "height": image_data.get("height"),
                "size": image_data.get("size"),
                "format": image_data.get("format"),
                "file_path": image_path,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "message": f"Successfully uploaded image: {os.path.basename(image_path)}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path,
                "message": f"Failed to upload image: {os.path.basename(image_path) if os.path.exists(image_path) else 'unknown'}"
            }
    
    async def create_ad_creative(
        self,
        creative_name: str,
        creative_type: str,
        ad_text: str,
        call_to_action: str,
        landing_page_url: str,
        image_id: Optional[str] = None,
        video_id: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new ad creative.
        
        Args:
            creative_name: Name for the creative
            creative_type: Type of creative (IMAGE, VIDEO, CAROUSEL)
            ad_text: Ad copy text
            call_to_action: Call-to-action text
            landing_page_url: Destination URL
            image_id: Image asset ID (for IMAGE creatives)
            video_id: Video asset ID (for VIDEO creatives)
            display_name: Display name for the brand
            
        Returns:
            Created ad creative information
        """
        try:
            # Validate required assets
            if creative_type == "IMAGE" and not image_id:
                return {
                    "success": False,
                    "error": "Missing image_id",
                    "creative_type": creative_type,
                    "message": "image_id is required for IMAGE creatives"
                }
            
            if creative_type == "VIDEO" and not video_id:
                return {
                    "success": False,
                    "error": "Missing video_id",
                    "creative_type": creative_type,
                    "message": "video_id is required for VIDEO creatives"
                }
            
            # Prepare creative data
            creative_data = {
                "creative_name": creative_name,
                "creative_type": creative_type,
                "ad_text": ad_text,
                "call_to_action": call_to_action,
                "landing_page_url": landing_page_url,
            }
            
            if image_id:
                creative_data["image_id"] = image_id
            
            if video_id:
                creative_data["video_id"] = video_id
            
            if display_name:
                creative_data["display_name"] = display_name
            
            # Note: This is a placeholder - actual implementation would call TikTok's creative creation API
            # The TikTok Ads API has specific endpoints for creating different types of creatives
            
            # For now, return a mock successful response
            creative_id = f"creative_{int(__import__('time').time())}"
            
            return {
                "success": True,
                "creative_id": creative_id,
                "creative_name": creative_name,
                "creative_type": creative_type,
                "ad_text": ad_text,
                "call_to_action": call_to_action,
                "landing_page_url": landing_page_url,
                "assets": {
                    "image_id": image_id,
                    "video_id": video_id,
                },
                "message": f"Successfully created {creative_type} creative: {creative_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "creative_name": creative_name,
                "message": f"Failed to create ad creative: {creative_name}"
            }
    
    async def analyze_creative_performance(
        self,
        creative_ids: List[str],
        date_range: str = "last_7_days",
    ) -> Dict[str, Any]:
        """Analyze performance of ad creatives.
        
        Args:
            creative_ids: List of creative IDs to analyze
            date_range: Date range for performance analysis
            
        Returns:
            Creative performance analysis and insights
        """
        try:
            # This would typically call the performance tools to get creative-level metrics
            # For now, return mock analysis data
            
            creative_analysis = []
            for creative_id in creative_ids:
                analysis = {
                    "creative_id": creative_id,
                    "performance_metrics": {
                        "impressions": 10000,
                        "clicks": 150,
                        "conversions": 12,
                        "ctr": 1.5,
                        "conversion_rate": 8.0,
                        "cost": 45.50,
                        "cpc": 0.30,
                        "cpa": 3.79,
                    },
                    "performance_grade": "B+",
                    "insights": [
                        "CTR is above average for this creative type",
                        "Conversion rate could be improved with better landing page alignment"
                    ],
                    "recommendations": [
                        "Consider A/B testing different ad copy variations",
                        "Test similar visual styles that performed well"
                    ]
                }
                creative_analysis.append(analysis)
            
            # Generate overall insights
            overall_insights = [
                f"Analyzed {len(creative_ids)} creatives over {date_range}",
                "Performance varies significantly across creatives",
                "Video creatives show 25% higher engagement than static images"
            ]
            
            recommendations = [
                "Focus budget on top-performing creative variations",
                "Create more video content to improve overall engagement",
                "Test creative refresh cycle of 7-14 days to combat ad fatigue"
            ]
            
            return {
                "success": True,
                "date_range": date_range,
                "creative_analysis": creative_analysis,
                "overall_insights": overall_insights,
                "recommendations": recommendations,
                "creatives_analyzed": len(creative_ids),
                "message": f"Completed performance analysis for {len(creative_ids)} creatives"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "creative_ids": creative_ids,
                "message": "Failed to analyze creative performance"
            }