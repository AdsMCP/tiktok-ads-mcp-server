"""Central registry for TikTok Ads MCP tool schemas and dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from typing import Any, Awaitable, Callable, Dict, List, Optional

from mcp.types import Tool


ToolHandler = Callable[[Any, Dict[str, Any]], Awaitable[Any]]


STATUS_ENUM = [
    "STATUS_ALL",
    "STATUS_NOT_DELETE",
    "STATUS_NOT_DELIVERY",
    "STATUS_DELIVERY_OK",
    "STATUS_DISABLE",
    "STATUS_DELETE",
]

DATE_RANGE_ENUM = [
    "today",
    "yesterday",
    "last_7_days",
    "last_14_days",
    "last_30_days",
    "last_90_days",
]
AD_STATUS_ENUM = STATUS_ENUM + ["STATUS_TIME_DONE", "STATUS_RF_CLOSED", "STATUS_FROZEN"]
AUDIENCE_DIMENSION_ENUM = [
    "age",
    "gender",
    "age_gender",
    "platform",
    "country_code",
    "language",
    "interest_category",
    "placement",
]
ID_DIMENSION_ENUM = ["campaign_id", "adgroup_id", "ad_id"]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: ToolHandler
    requires_auth: bool = True

    def to_mcp_tool(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema,
        )


def object_schema(
    properties: Dict[str, Any],
    required: List[str] | None = None,
    additional_properties: bool = False,
) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional_properties,
    }
    if required:
        schema["required"] = required
    return schema


async def login(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.start_oauth_flow(force_reauth=arguments.get("force_reauth", False))


async def complete_auth(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.complete_oauth(arguments.get("auth_code"))


async def auth_status(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.get_auth_status()


async def switch_ad_account(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.switch_ad_account(arguments.get("advertiser_id"))


async def get_campaigns(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.campaign_tools.get_campaigns(**arguments)


async def get_campaign_details(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.campaign_tools.get_campaign_details(**arguments)


async def get_adgroups(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.campaign_tools.get_adgroups(**arguments)


async def get_adgroup_details(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.campaign_tools.get_adgroup_details(**arguments)


async def get_ads(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.campaign_tools.get_ads(**arguments)


async def get_ad_details(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.campaign_tools.get_ad_details(**arguments)


async def get_campaign_performance(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.performance_tools.get_campaign_performance(**arguments)


async def get_adgroup_performance(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.performance_tools.get_adgroup_performance(**arguments)


async def get_ad_performance(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.performance_tools.get_ad_performance(**arguments)


def get_date_range(date_range: str) -> tuple[str, str]:
    today = datetime.now()
    if date_range == "today":
        start_date = end_date = today
    elif date_range == "yesterday":
        start_date = end_date = today - timedelta(days=1)
    else:
        days = {
            "last_7_days": 7,
            "last_14_days": 14,
            "last_30_days": 30,
            "last_90_days": 90,
        }.get(date_range, 7)
        start_date = today - timedelta(days=days)
        end_date = today - timedelta(days=1)

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def get_nested_value(source: Dict[str, Any], key: str) -> Any:
    return source.get(key) or source.get("metrics", {}).get(key) or source.get("dimensions", {}).get(key)


def to_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace("%", ""))
        except ValueError:
            return 0.0
    return 0.0


def normalize_performance_candidate(
    row: Dict[str, Any],
    id_key: str,
    level: str,
    name_by_id: Dict[str, str],
    parent_campaign_id: Optional[str] = None,
) -> Dict[str, Any]:
    entity_id = str(get_nested_value(row, id_key) or "")
    spend = to_number(get_nested_value(row, "spend"))
    clicks = to_number(get_nested_value(row, "clicks"))
    conversions = to_number(get_nested_value(row, "conversion"))
    cpc = to_number(get_nested_value(row, "cpc"))
    ctr = to_number(get_nested_value(row, "ctr"))
    cpm = to_number(get_nested_value(row, "cpm"))
    cost_per_conversion = to_number(get_nested_value(row, "cost_per_conversion"))
    conversion_rate = to_number(get_nested_value(row, "conversion_rate_v2"))
    return {
        "id": entity_id,
        "name": name_by_id.get(entity_id),
        "level": level,
        "parent_campaign_id": parent_campaign_id,
        "spend": spend,
        "clicks": clicks,
        "impressions": to_number(get_nested_value(row, "impressions")),
        "ctr": ctr,
        "cpc": cpc,
        "cpm": cpm,
        "conversions": conversions,
        "cost_per_conversion": cost_per_conversion or None,
        "conversion_rate": conversion_rate,
        "likely_issue": "Needs more data",
        "confidence": "Low",
        "next_action": "Continue only with a capped budget and verify lower-funnel events before drawing a conclusion.",
        "should_keep_spending": "needs_more_data",
        "evidence": [
            f"Spend: {spend}",
            f"Clicks: {clicks}",
            f"Conversions: {conversions}",
        ],
    }


def classify_wasted_spend_candidate(
    candidate: Dict[str, Any],
    min_spend: float,
    min_clicks: float,
    high_ctr: float,
    high_cpc: float,
) -> Dict[str, Any]:
    if candidate["spend"] >= min_spend and candidate["clicks"] >= min_clicks and candidate["conversions"] == 0:
        candidate.update(
            {
                "likely_issue": "Wasted spend with no conversion signal",
                "confidence": "High",
                "next_action": "Do not increase budget. Verify purchase or lead tracking, then inspect landing page match, offer, and checkout friction.",
                "should_keep_spending": "pause_or_reduce",
            }
        )
        candidate["evidence"].append(f"Spend >= {min_spend} and clicks >= {min_clicks}")
    elif candidate["clicks"] >= min_clicks and candidate["conversions"] == 0:
        candidate.update(
            {
                "likely_issue": "Enough clicks but no conversion signal",
                "confidence": "Medium",
                "next_action": "Keep only a small fixed test budget until tracking and funnel events are verified.",
                "should_keep_spending": "keep_small_retest_budget",
            }
        )
        candidate["evidence"].append(f"Clicks >= {min_clicks}")
    elif candidate["spend"] >= min_spend and candidate["conversions"] == 0:
        candidate.update(
            {
                "likely_issue": "Spend without conversion signal",
                "confidence": "Medium",
                "next_action": "Review traffic cost, click quality, tracking, and landing page before spending more.",
                "should_keep_spending": "keep_small_retest_budget",
            }
        )
        candidate["evidence"].append(f"Spend >= {min_spend}")
    elif candidate["ctr"] >= high_ctr and candidate["clicks"] >= max(50, min_clicks * 0.5) and candidate["conversions"] == 0:
        candidate.update(
            {
                "likely_issue": "High CTR but no conversion signal",
                "confidence": "Medium",
                "next_action": "Check whether the creative attracts curiosity clicks and compare the ad hook with the landing page first screen.",
                "should_keep_spending": "keep_small_retest_budget",
            }
        )
        candidate["evidence"].append(f"CTR >= {high_ctr}")
    elif candidate["cpc"] >= high_cpc and candidate["conversions"] == 0:
        candidate.update(
            {
                "likely_issue": "Expensive traffic with no conversion signal",
                "confidence": "Low",
                "next_action": "Check audience, bid strategy, creative relevance, and landing page promise before spending more.",
                "should_keep_spending": "needs_more_data",
            }
        )
        candidate["evidence"].append(f"CPC >= {high_cpc}")
    return candidate


def candidate_sort_score(candidate: Dict[str, Any]) -> float:
    confidence_score = {"High": 10000, "Medium": 5000, "Low": 0}.get(candidate.get("confidence"), 0)
    return confidence_score + candidate.get("spend", 0) + candidate.get("clicks", 0) * max(candidate.get("cpc", 0), 0.01)


async def get_audience_breakdown(server: Any, arguments: Dict[str, Any]) -> Any:
    start_date, end_date = get_date_range(arguments.get("date_range", "last_7_days"))
    return await server.client.get_audience_breakdown(
        audience_dimension=arguments["audience_dimension"],
        id_dimension=arguments["id_dimension"],
        entity_ids=arguments["entity_ids"],
        include_time=arguments.get("include_time", False),
        metrics=arguments.get("metrics"),
        start_date=start_date,
        end_date=end_date,
    )


async def get_location_info(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.client.get_location_info(location_ids=arguments["location_ids"])


async def get_pixel_event_stats(server: Any, arguments: Dict[str, Any]) -> Any:
    start_date, end_date = get_date_range(arguments.get("date_range", "last_7_days"))
    return await server.client.get_pixel_event_stats(
        pixel_ids=arguments["pixel_ids"],
        start_date=start_date,
        end_date=end_date,
    )


async def get_pixel_list(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.client.get_pixel_list(**arguments)


async def wasted_spend_audit(server: Any, arguments: Dict[str, Any]) -> Any:
    date_range = arguments.get("date_range", "last_7_days")
    campaign_limit = arguments.get("campaign_limit", 50)
    min_spend = float(arguments.get("min_spend", 300))
    min_clicks = float(arguments.get("min_clicks", 100))
    high_ctr = float(arguments.get("high_ctr", 2))
    high_cpc = float(arguments.get("high_cpc", 5))
    include_adgroup_breakdown = arguments.get("include_adgroup_breakdown", True)
    max_adgroup_campaigns = int(arguments.get("max_adgroup_campaigns", 3))
    start_date, end_date = get_date_range(date_range)

    campaign_result = await server.client.get_campaigns(
        status="STATUS_NOT_DELETE",
        limit=campaign_limit,
    )
    campaigns = campaign_result.get("data", {}).get("list", [])
    campaign_name_by_id = {
        str(campaign.get("campaign_id") or campaign.get("id")): campaign.get("campaign_name") or campaign.get("name")
        for campaign in campaigns
        if campaign.get("campaign_id") or campaign.get("id")
    }
    campaign_ids = list(campaign_name_by_id)

    if not campaign_ids:
        return {
            "success": True,
            "data": {
                "audit_type": "tiktok_ads_wasted_spend_audit",
                "date_range": date_range,
                "message": "No non-deleted campaigns were found.",
                "wasted_spend_candidates": [],
                "adgroup_breakdown": [],
            },
        }

    metrics = [
        "spend",
        "impressions",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "conversion",
        "cost_per_conversion",
        "conversion_rate_v2",
    ]
    campaign_performance = await server.client.get_performance_data(
        level="AUCTION_CAMPAIGN",
        entity_ids=campaign_ids,
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
        dimensions=["campaign_id"],
    )
    campaign_rows = campaign_performance.get("data", {}).get("list", [])
    campaign_candidates = [
        classify_wasted_spend_candidate(
            normalize_performance_candidate(row, "campaign_id", "campaign", campaign_name_by_id),
            min_spend,
            min_clicks,
            high_ctr,
            high_cpc,
        )
        for row in campaign_rows
    ]
    campaign_candidates = [
        candidate
        for candidate in campaign_candidates
        if candidate["id"] and candidate["conversions"] == 0 and (candidate["spend"] > 0 or candidate["clicks"] > 0)
    ]
    campaign_candidates.sort(key=candidate_sort_score, reverse=True)

    adgroup_breakdown = []
    if include_adgroup_breakdown:
        risky_campaigns = [
            candidate
            for candidate in campaign_candidates
            if candidate["should_keep_spending"] in {"pause_or_reduce", "keep_small_retest_budget"}
        ][:max_adgroup_campaigns]
        for campaign in risky_campaigns:
            adgroup_result = await server.client.get_adgroups(
                campaign_id=campaign["id"],
                status="STATUS_NOT_DELETE",
                limit=50,
            )
            adgroups = adgroup_result.get("data", {}).get("list", [])
            adgroup_name_by_id = {
                str(adgroup.get("adgroup_id") or adgroup.get("id")): adgroup.get("adgroup_name") or adgroup.get("name")
                for adgroup in adgroups
                if adgroup.get("adgroup_id") or adgroup.get("id")
            }
            adgroup_ids = list(adgroup_name_by_id)
            if not adgroup_ids:
                continue

            adgroup_performance = await server.client.get_performance_data(
                level="AUCTION_ADGROUP",
                entity_ids=adgroup_ids,
                metrics=metrics,
                start_date=start_date,
                end_date=end_date,
                dimensions=["adgroup_id"],
            )
            adgroup_rows = adgroup_performance.get("data", {}).get("list", [])
            for row in adgroup_rows:
                candidate = classify_wasted_spend_candidate(
                    normalize_performance_candidate(
                        row,
                        "adgroup_id",
                        "adgroup",
                        adgroup_name_by_id,
                        parent_campaign_id=campaign["id"],
                    ),
                    min_spend,
                    min_clicks,
                    high_ctr,
                    high_cpc,
                )
                if candidate["id"] and candidate["conversions"] == 0 and (candidate["spend"] > 0 or candidate["clicks"] > 0):
                    adgroup_breakdown.append(candidate)

    adgroup_breakdown.sort(key=candidate_sort_score, reverse=True)
    high_confidence_count = len([c for c in campaign_candidates if c["confidence"] == "High"])
    total_risk_spend = sum(
        c["spend"] for c in campaign_candidates if c["confidence"] in {"High", "Medium"}
    )

    return {
        "success": True,
        "data": {
            "audit_type": "tiktok_ads_wasted_spend_audit",
            "date_range": date_range,
            "start_date": start_date,
            "end_date": end_date,
            "campaigns_scanned": len(campaign_ids),
            "high_confidence_count": high_confidence_count,
            "total_risk_spend": round(total_risk_spend, 2),
            "wasted_spend_candidates": campaign_candidates[:20],
            "adgroup_breakdown": adgroup_breakdown[:30],
            "next_steps": [
                "Pause or reduce budget for high-confidence candidates until tracking and landing page quality are checked.",
                "Use ad group breakdown to find whether the issue is isolated or campaign-wide.",
                "Use pixel tools to compare event activity against ad platform conversion metrics.",
            ],
        },
    }


async def get_custom_audiences(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.audience_tools.get_custom_audiences(**arguments)


async def get_advertiser_info(server: Any, arguments: Dict[str, Any]) -> Any:
    return await server.client.get_advertiser_info(**arguments)


TOOL_DEFINITIONS: List[ToolDefinition] = [
    ToolDefinition(
        name="tiktok_ads_login",
        description="Start TikTok Ads OAuth authentication flow",
        input_schema=object_schema(
            {
                "force_reauth": {
                    "type": "boolean",
                    "description": "Force reauthentication even if saved tokens exist.",
                }
            }
        ),
        handler=login,
        requires_auth=False,
    ),
    ToolDefinition(
        name="tiktok_ads_complete_auth",
        description="Complete OAuth authentication with an authorization code",
        input_schema=object_schema(
            {
                "auth_code": {
                    "type": "string",
                    "description": "Authorization code from the OAuth redirect URL.",
                }
            },
            required=["auth_code"],
        ),
        handler=complete_auth,
        requires_auth=False,
    ),
    ToolDefinition(
        name="tiktok_ads_auth_status",
        description="Check current TikTok Ads API authentication status",
        input_schema=object_schema({}),
        handler=auth_status,
        requires_auth=False,
    ),
    ToolDefinition(
        name="tiktok_ads_switch_ad_account",
        description="Switch to a different advertiser account only when the user asks.",
        input_schema=object_schema(
            {
                "advertiser_id": {
                    "type": "string",
                    "description": "Advertiser ID to switch to.",
                }
            },
            required=["advertiser_id"],
        ),
        handler=switch_ad_account,
        requires_auth=False,
    ),
    ToolDefinition(
        name="tiktok_ads_get_campaigns",
        description="Retrieve campaigns for the current advertiser account",
        input_schema=object_schema(
            {
                "status": {
                    "type": "string",
                    "enum": STATUS_ENUM,
                    "description": "Optional primary status filter.",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of campaigns to return.",
                },
            }
        ),
        handler=get_campaigns,
    ),
    ToolDefinition(
        name="tiktok_ads_get_campaign_details",
        description="Get detailed information for a specific campaign",
        input_schema=object_schema(
            {
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID to retrieve.",
                }
            },
            required=["campaign_id"],
        ),
        handler=get_campaign_details,
    ),
    ToolDefinition(
        name="tiktok_ads_get_adgroups",
        description="Retrieve ad groups for a campaign",
        input_schema=object_schema(
            {
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "status": {
                    "type": "string",
                    "enum": STATUS_ENUM,
                    "description": "Optional primary status filter.",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of ad groups to return.",
                },
            },
            required=["campaign_id"],
        ),
        handler=get_adgroups,
    ),
    ToolDefinition(
        name="tiktok_ads_get_adgroup_details",
        description="Get detailed information for a specific ad group",
        input_schema=object_schema(
            {
                "adgroup_id": {
                    "type": "string",
                    "description": "Ad group ID to retrieve.",
                }
            },
            required=["adgroup_id"],
        ),
        handler=get_adgroup_details,
    ),
    ToolDefinition(
        name="tiktok_ads_get_ads",
        description="Retrieve ads with optional campaign, ad group, ad ID, or status filters",
        input_schema=object_schema(
            {
                "campaign_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional campaign IDs to filter by.",
                },
                "adgroup_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional ad group IDs to filter by.",
                },
                "ad_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional ad IDs to filter by.",
                },
                "status": {
                    "type": "string",
                    "enum": AD_STATUS_ENUM,
                    "description": "Optional primary status filter.",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of ads to return.",
                },
            }
        ),
        handler=get_ads,
    ),
    ToolDefinition(
        name="tiktok_ads_get_ad_details",
        description="Get detailed information for a specific ad",
        input_schema=object_schema(
            {
                "ad_id": {
                    "type": "string",
                    "description": "Ad ID to retrieve.",
                }
            },
            required=["ad_id"],
        ),
        handler=get_ad_details,
    ),
    ToolDefinition(
        name="tiktok_ads_get_campaign_performance",
        description="Get performance metrics for campaigns",
        input_schema=object_schema(
            {
                "campaign_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Campaign IDs to analyze.",
                },
                "date_range": {
                    "type": "string",
                    "enum": DATE_RANGE_ENUM,
                    "description": "Date range for performance data.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional TikTok report metrics. Defaults to core spend, delivery, click, and conversion metrics.",
                },
            },
            required=["campaign_ids", "date_range"],
        ),
        handler=get_campaign_performance,
    ),
    ToolDefinition(
        name="tiktok_ads_get_adgroup_performance",
        description="Get performance metrics for ad groups",
        input_schema=object_schema(
            {
                "adgroup_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ad group IDs to analyze.",
                },
                "date_range": {
                    "type": "string",
                    "enum": DATE_RANGE_ENUM,
                    "description": "Date range for performance data.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional TikTok report metrics.",
                },
            },
            required=["adgroup_ids", "date_range"],
        ),
        handler=get_adgroup_performance,
    ),
    ToolDefinition(
        name="tiktok_ads_get_ad_performance",
        description="Get performance metrics for ads",
        input_schema=object_schema(
            {
                "ad_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ad IDs to analyze.",
                },
                "date_range": {
                    "type": "string",
                    "enum": DATE_RANGE_ENUM,
                    "description": "Date range for performance data.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional TikTok report metrics.",
                },
            },
            required=["ad_ids", "date_range"],
        ),
        handler=get_ad_performance,
    ),
    ToolDefinition(
        name="tiktok_ads_get_audience_breakdown",
        description="Get audience demographic breakdown for campaigns, ad groups, or ads",
        input_schema=object_schema(
            {
                "id_dimension": {
                    "type": "string",
                    "enum": ID_DIMENSION_ENUM,
                    "description": "Entity ID type. Must match the IDs in entity_ids.",
                },
                "entity_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "description": "Campaign, ad group, or ad IDs to analyze.",
                },
                "audience_dimension": {
                    "type": "string",
                    "enum": AUDIENCE_DIMENSION_ENUM,
                    "description": "Audience dimension to break down by.",
                },
                "date_range": {
                    "type": "string",
                    "enum": DATE_RANGE_ENUM,
                    "default": "last_7_days",
                    "description": "Date range for performance data.",
                },
                "include_time": {
                    "type": "boolean",
                    "description": "Include daily breakdown with stat_time_day.",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional metrics. Defaults to spend, impressions, clicks, and ctr.",
                },
            },
            required=["id_dimension", "entity_ids", "audience_dimension"],
        ),
        handler=get_audience_breakdown,
    ),
    ToolDefinition(
        name="tiktok_ads_wasted_spend_audit",
        description="Run a read-only rule-based audit for spend and clicks with no conversion signal",
        input_schema=object_schema(
            {
                "date_range": {
                    "type": "string",
                    "enum": DATE_RANGE_ENUM,
                    "default": "last_7_days",
                    "description": "Date range for the audit.",
                },
                "campaign_limit": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of non-deleted campaigns to scan.",
                },
                "min_spend": {
                    "type": "number",
                    "default": 300,
                    "description": "Spend threshold for high-confidence candidates.",
                },
                "min_clicks": {
                    "type": "number",
                    "default": 100,
                    "description": "Click threshold for high-confidence candidates.",
                },
                "high_ctr": {
                    "type": "number",
                    "default": 2,
                    "description": "CTR threshold for curiosity-click cases.",
                },
                "high_cpc": {
                    "type": "number",
                    "default": 5,
                    "description": "CPC threshold for expensive no-conversion traffic.",
                },
                "include_adgroup_breakdown": {
                    "type": "boolean",
                    "default": True,
                    "description": "Drill into ad groups for top risky campaigns.",
                },
                "max_adgroup_campaigns": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Maximum risky campaigns to inspect at ad group level.",
                },
            }
        ),
        handler=wasted_spend_audit,
    ),
    ToolDefinition(
        name="tiktok_ads_get_custom_audiences",
        description="List custom audiences for the current advertiser",
        input_schema=object_schema(
            {
                "limit": {"type": "integer", "default": 10},
            }
        ),
        handler=get_custom_audiences,
    ),
    ToolDefinition(
        name="tiktok_ads_get_advertiser_info",
        description="Get account-level advertiser information such as currency, timezone, status, industry, country, and creation time.",
        input_schema=object_schema(
            {
                "advertiser_id": {
                    "type": "string",
                    "description": "Optional advertiser ID. Defaults to the current authenticated or switched advertiser.",
                },
            }
        ),
        handler=get_advertiser_info,
    ),
    ToolDefinition(
        name="tiktok_ads_get_location_info",
        description="Resolve TikTok targeting location IDs into readable location metadata",
        input_schema=object_schema(
            {
                "location_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 20,
                    "description": "Location targeting IDs to resolve.",
                }
            },
            required=["location_ids"],
        ),
        handler=get_location_info,
    ),
    ToolDefinition(
        name="tiktok_ads_get_pixel_list",
        description="List TikTok pixels for the current advertiser",
        input_schema=object_schema(
            {
                "code": {"type": "string", "description": "Optional pixel code filter."},
                "pixel_id": {"type": "string", "description": "Optional pixel ID filter."},
                "name": {"type": "string", "description": "Optional pixel name fuzzy search."},
                "order_by": {
                    "type": "string",
                    "enum": ["EARLIEST_CREATE", "LATEST_CREATE"],
                    "description": "Optional sorting method.",
                },
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
            }
        ),
        handler=get_pixel_list,
    ),
    ToolDefinition(
        name="tiktok_ads_get_pixel_event_stats",
        description="Get TikTok pixel event statistics for a date range",
        input_schema=object_schema(
            {
                "pixel_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 10,
                    "description": "Pixel IDs to query.",
                },
                "date_range": {
                    "type": "string",
                    "enum": DATE_RANGE_ENUM,
                    "default": "last_7_days",
                    "description": "Date range for pixel event stats.",
                },
            },
            required=["pixel_ids"],
        ),
        handler=get_pixel_event_stats,
    ),
]

TOOLS_BY_NAME = {tool.name: tool for tool in TOOL_DEFINITIONS}


def list_mcp_tools() -> List[Tool]:
    return [definition.to_mcp_tool() for definition in TOOL_DEFINITIONS]


async def dispatch_tool(server: Any, name: str, arguments: Dict[str, Any]) -> Any:
    definition = TOOLS_BY_NAME.get(name)
    if not definition:
        return {"success": False, "error": f"Unknown tool '{name}'"}

    if definition.requires_auth and (not server.client or not server.is_authenticated):
        return {
            "success": False,
            "error": "Not authenticated with TikTok Ads API. Please use tiktok_ads_login first.",
        }

    return await definition.handler(server, arguments or {})


def serialize_tool_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2, default=str)
