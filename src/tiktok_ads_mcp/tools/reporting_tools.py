"""Reporting tools for TikTok Ads MCP server."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..tiktok_client import TikTokAdsClient


class ReportingTools:
    """Tools for generating and managing TikTok Ads reports."""
    
    def __init__(self, client: TikTokAdsClient):
        self.client = client
    
    async def generate_report(
        self,
        report_type: str,
        dimensions: List[str],
        metrics: List[str],
        date_range: Dict[str, str],
        filtering: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a custom performance report.
        
        Args:
            report_type: Type of report (BASIC, AUDIENCE, PLACEMENT, DPA)
            dimensions: Report dimensions (campaign_id, adgroup_id, ad_id, stat_time_day)
            metrics: Report metrics to include
            date_range: Dictionary with start_date and end_date
            filtering: Optional filters for the report
            
        Returns:
            Report generation result with task ID for async retrieval
        """
        try:
            start_date = date_range["start_date"]
            end_date = date_range["end_date"]
            
            # Validate date range
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                
                if start_dt > end_dt:
                    return {
                        "success": False,
                        "error": "Invalid date range",
                        "message": "Start date must be before end date"
                    }
                
                # Check if date range is not too far back (TikTok has data retention limits)
                days_back = (datetime.now() - start_dt).days
                if days_back > 365:
                    return {
                        "success": False,
                        "error": "Date range too far back",
                        "message": "Report data is only available for the last 365 days"
                    }
                    
            except ValueError:
                return {
                    "success": False,
                    "error": "Invalid date format",
                    "message": "Dates must be in YYYY-MM-DD format"
                }
            
            # Validate metrics
            available_metrics = [
                "impressions", "clicks", "conversion", "spend", "ctr", "cpm", "cpc", 
                "conversion_rate", "cost_per_conversion", "reach", "frequency",
                "video_play_actions", "video_watched_2s", "video_watched_6s",
                "profile_visits", "likes", "comments", "shares", "follows"
            ]
            
            invalid_metrics = [m for m in metrics if m not in available_metrics]
            if invalid_metrics:
                return {
                    "success": False,
                    "error": "Invalid metrics",
                    "invalid_metrics": invalid_metrics,
                    "available_metrics": available_metrics,
                    "message": f"Invalid metrics: {', '.join(invalid_metrics)}"
                }
            
            # Create report task
            result = await self.client.create_report_task(
                report_type=report_type,
                dimensions=dimensions,
                metrics=metrics,
                start_date=start_date,
                end_date=end_date,
                filtering=filtering,
            )
            
            task_data = result.get("data", {})
            task_id = task_data.get("task_id")
            
            return {
                "success": True,
                "task_id": task_id,
                "report_type": report_type,
                "dimensions": dimensions,
                "metrics": metrics,
                "date_range": f"{start_date} to {end_date}",
                "status": "QUEUED",
                "estimated_completion": "2-5 minutes",
                "message": f"Report generation started. Task ID: {task_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "report_type": report_type,
                "message": "Failed to generate report"
            }
    
    async def get_report_status(self, task_id: str) -> Dict[str, Any]:
        """Check the status of a report generation task.
        
        Args:
            task_id: Report task ID
            
        Returns:
            Report status and progress information
        """
        try:
            result = await self.client.get_report_task_status(task_id)
            
            task_data = result.get("data", {})
            status = task_data.get("status")
            
            status_info = {
                "task_id": task_id,
                "status": status,
                "progress": task_data.get("progress", 0),
                "created_at": task_data.get("created_at"),
                "updated_at": task_data.get("updated_at"),
            }
            
            if status == "SUCCESS":
                status_info.update({
                    "download_url": task_data.get("download_url"),
                    "file_size": task_data.get("file_size"),
                    "row_count": task_data.get("row_count"),
                    "expires_at": task_data.get("expires_at"),
                })
                message = f"Report completed successfully. {task_data.get('row_count', 0)} rows generated."
            elif status == "PROCESSING":
                estimated_time = max(1, 5 - task_data.get("progress", 0) // 20)
                status_info["estimated_completion_minutes"] = estimated_time
                message = f"Report is processing... {task_data.get('progress', 0)}% complete"
            elif status == "FAILED":
                status_info["error_message"] = task_data.get("error_message")
                message = f"Report generation failed: {task_data.get('error_message', 'Unknown error')}"
            else:
                message = f"Report status: {status}"
            
            return {
                "success": True,
                "status_info": status_info,
                "message": message
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id,
                "message": "Failed to check report status"
            }
    
    async def download_report(self, task_id: str) -> Dict[str, Any]:
        """Download a completed report.
        
        Args:
            task_id: Report task ID
            
        Returns:
            Report data or download information
        """
        try:
            # First check if report is ready
            status_result = await self.get_report_status(task_id)
            if not status_result["success"]:
                return status_result
            
            status = status_result["status_info"]["status"]
            if status != "SUCCESS":
                return {
                    "success": False,
                    "error": "Report not ready",
                    "current_status": status,
                    "task_id": task_id,
                    "message": f"Report is not ready for download. Current status: {status}"
                }
            
            # Download the report
            result = await self.client.download_report(task_id)
            
            report_data = result.get("data", {})
            
            return {
                "success": True,
                "task_id": task_id,
                "download_url": report_data.get("download_url"),
                "file_format": "CSV",
                "file_size": report_data.get("file_size"),
                "row_count": report_data.get("row_count"),
                "expires_at": report_data.get("expires_at"),
                "report_data": report_data.get("data", [])[:100],  # First 100 rows for preview
                "message": f"Report downloaded successfully. {report_data.get('row_count', 0)} rows available."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id,
                "message": "Failed to download report"
            }
    
    async def generate_quick_report(
        self,
        entity_type: str = "campaign",
        entity_ids: Optional[List[str]] = None,
        date_range: str = "last_7_days",
        include_breakdowns: bool = False,
    ) -> Dict[str, Any]:
        """Generate a quick performance report with standard metrics.
        
        Args:
            entity_type: Type of entity (campaign, adgroup, ad)
            entity_ids: List of entity IDs (if None, includes all)
            date_range: Predefined date range
            include_breakdowns: Whether to include demographic breakdowns
            
        Returns:
            Quick report data
        """
        try:
            # Convert date range to actual dates
            today = datetime.now()
            if date_range == "today":
                start_date = end_date = today.strftime("%Y-%m-%d")
            elif date_range == "yesterday":
                yesterday = today - timedelta(days=1)
                start_date = end_date = yesterday.strftime("%Y-%m-%d")
            elif date_range == "last_7_days":
                start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            elif date_range == "last_30_days":
                start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
                end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
                end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Standard dimensions and metrics
            if entity_type == "campaign":
                dimensions = ["campaign_id", "stat_time_day"]
            elif entity_type == "adgroup":
                dimensions = ["adgroup_id", "stat_time_day"]
            else:
                dimensions = ["ad_id", "stat_time_day"]
            
            if include_breakdowns:
                dimensions.extend(["age", "gender"])
            
            standard_metrics = [
                "impressions", "clicks", "conversions", "spend",
                "ctr", "cpm", "cpc", "conversion_rate"
            ]
            
            # Set up filtering if entity IDs provided
            filtering = {}
            if entity_ids:
                if entity_type == "campaign":
                    filtering["campaign_ids"] = entity_ids
                elif entity_type == "adgroup":
                    filtering["adgroup_ids"] = entity_ids
                elif entity_type == "ad":
                    filtering["ad_ids"] = entity_ids
            
            # Generate the report
            report_result = await self.generate_report(
                report_type="BASIC",
                dimensions=dimensions,
                metrics=standard_metrics,
                date_range={"start_date": start_date, "end_date": end_date},
                filtering=filtering if filtering else None,
            )
            
            if not report_result["success"]:
                return report_result
            
            task_id = report_result["task_id"]
            
            # Wait for report completion (with timeout)
            max_wait_time = 300  # 5 minutes
            wait_interval = 10   # 10 seconds
            waited_time = 0
            
            while waited_time < max_wait_time:
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
                
                status_result = await self.get_report_status(task_id)
                if not status_result["success"]:
                    return status_result
                
                status = status_result["status_info"]["status"]
                if status == "SUCCESS":
                    # Download and return the report
                    return await self.download_report(task_id)
                elif status == "FAILED":
                    return {
                        "success": False,
                        "error": "Report generation failed",
                        "task_id": task_id,
                        "message": status_result["status_info"].get("error_message", "Unknown error")
                    }
            
            # Timeout reached
            return {
                "success": False,
                "error": "Report generation timeout",
                "task_id": task_id,
                "message": "Report generation is taking longer than expected. Please check status manually."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "entity_type": entity_type,
                "message": "Failed to generate quick report"
            }
    
    async def get_available_metrics(self) -> Dict[str, Any]:
        """Get list of available metrics for reporting.
        
        Returns:
            Dictionary of available metrics organized by category
        """
        metrics_catalog = {
            "basic_metrics": {
                "impressions": "Number of times ads were displayed",
                "clicks": "Number of clicks on ads",
                "spend": "Total amount spent",
                "reach": "Number of unique users reached",
                "frequency": "Average number of times users saw ads"
            },
            "engagement_metrics": {
                "likes": "Number of likes on ads",
                "comments": "Number of comments on ads", 
                "shares": "Number of shares of ads",
                "follows": "Number of new followers from ads",
                "profile_visits": "Number of profile visits from ads"
            },
            "video_metrics": {
                "video_play_actions": "Number of video plays",
                "video_watched_2s": "Number of 2-second video views",
                "video_watched_6s": "Number of 6-second video views",
                "video_view_rate": "Percentage of impressions that resulted in video views"
            },
            "conversion_metrics": {
                "conversions": "Number of conversion events",
                "conversion_rate": "Conversion rate percentage",
                "cost_per_conversion": "Average cost per conversion",
                "roas": "Return on ad spend"
            },
            "calculated_metrics": {
                "ctr": "Click-through rate (clicks/impressions)",
                "cpm": "Cost per mille (cost per 1000 impressions)",
                "cpc": "Cost per click",
                "cpa": "Cost per acquisition"
            }
        }
        
        return {
            "success": True,
            "metrics_catalog": metrics_catalog,
            "total_metrics": sum(len(cat) for cat in metrics_catalog.values()),
            "message": "Retrieved complete metrics catalog"
        }