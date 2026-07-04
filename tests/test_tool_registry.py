from tiktok_ads_mcp.tools.registry import TOOL_DEFINITIONS, TOOLS_BY_NAME, list_mcp_tools
from tiktok_ads_mcp.server import TikTokMCPServer
from tiktok_ads_mcp.tiktok_client import TikTokAdsClient
from tiktok_ads_mcp.tools.registry import dispatch_tool


def test_tool_registry_names_are_unique():
    names = [tool.name for tool in TOOL_DEFINITIONS]

    assert len(names) == len(set(names))
    assert set(names) == set(TOOLS_BY_NAME)


def test_list_mcp_tools_comes_from_registry():
    registry_names = [tool.name for tool in TOOL_DEFINITIONS]
    mcp_tools = list_mcp_tools()

    assert [tool.name for tool in mcp_tools] == registry_names
    assert all(tool.inputSchema["type"] == "object" for tool in mcp_tools)


def test_advertiser_info_tool_is_registered():
    definition = TOOLS_BY_NAME["tiktok_ads_get_advertiser_info"]

    assert definition.requires_auth is True
    assert definition.input_schema["properties"]["advertiser_id"]["type"] == "string"


def test_remote_tiktok_tools_are_registered_locally():
    migrated_tools = {
        "tiktok_ads_get_ads",
        "tiktok_ads_get_audience_breakdown",
        "tiktok_ads_get_location_info",
        "tiktok_ads_get_pixel_list",
        "tiktok_ads_get_pixel_event_stats",
        "tiktok_ads_wasted_spend_audit",
    }

    assert migrated_tools.issubset(TOOLS_BY_NAME)


def test_draft_tools_are_not_exposed():
    draft_tools = {
        "tiktok_ads_get_ad_creatives",
        "tiktok_ads_get_targeting_options",
        "tiktok_ads_generate_report",
        "tiktok_ads_create_custom_audience",
        "tiktok_ads_analyze_audience_insights",
        "tiktok_ads_create_ad_creative",
        "tiktok_ads_analyze_creative_performance",
        "tiktok_ads_create_campaign",
        "tiktok_ads_create_adgroup",
        "tiktok_ads_upload_image",
    }

    assert draft_tools.isdisjoint(TOOLS_BY_NAME)


async def test_auth_status_is_safe_before_configuration():
    server = TikTokMCPServer()

    result = await dispatch_tool(server, "tiktok_ads_auth_status", {})

    assert result["success"] is True
    assert result["data"]["status"] == "not_configured"


async def test_authenticated_tools_require_login():
    server = TikTokMCPServer()

    result = await dispatch_tool(server, "tiktok_ads_get_campaigns", {"limit": 1})

    assert result["success"] is False
    assert "Not authenticated" in result["error"]


async def test_get_advertiser_info_uses_advertiser_info_endpoint(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )
    calls = []

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        calls.append({"method": method, "endpoint": endpoint, "params": params})
        if endpoint == "advertiser/info/":
            return {
                "code": 0,
                "data": {
                    "list": [
                        {
                            "advertiser_id": "456",
                            "timezone": "UTC",
                            "create_time": "1700000000",
                        }
                    ]
                },
            }
        return {
            "code": 0,
            "data": {
                "list": [
                    {
                        "metrics": {"spend": "1.23"},
                        "dimensions": {"stat_time_day": "2026-01-01 00:00:00"},
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    result = await client.get_advertiser_info("456")

    assert calls[0]["method"] == "GET"
    assert calls[0]["endpoint"] == "advertiser/info/"
    assert calls[0]["params"]["advertiser_id"] == "456"
    assert calls[0]["params"]["advertiser_ids"] == ["456"]
    assert "currency" in calls[0]["params"]["fields"]
    advertiser = result["data"]["list"][0]
    assert advertiser["now_based_on_timezone"]
    assert advertiser["first_cost_day"] == "2026-01-01"
    assert advertiser["all_cost_days"] == ["2026-01-01"]
    assert advertiser["create_time_readable"] == "2023-11-14 22:13:20"


async def test_get_ads_uses_ad_get_endpoint(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )
    captured = {}

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"code": 0, "data": {"list": []}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    await client.get_ads(campaign_ids=["c1"], status="STATUS_NOT_DELETE", limit=5)

    assert captured["method"] == "GET"
    assert captured["endpoint"] == "ad/get/"
    assert captured["params"]["page_size"] == 5
    assert "campaign_ids" in captured["params"]["filtering"]


async def test_adgroup_and_ad_detail_endpoints(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )
    calls = []

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        calls.append({"method": method, "endpoint": endpoint, "params": params})
        return {"code": 0, "data": {"list": []}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    await client.get_adgroup_details("ag1")
    await client.get_ad_details("ad1")

    assert calls[0]["method"] == "GET"
    assert calls[0]["endpoint"] == "adgroup/get/"
    assert "adgroup_ids" in calls[0]["params"]["filtering"]
    assert calls[1]["method"] == "GET"
    assert calls[1]["endpoint"] == "ad/get/"
    assert "ad_ids" in calls[1]["params"]["filtering"]


async def test_campaign_read_tools_use_consistent_list_and_detail_shapes(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        if endpoint == "campaign/get/" and "campaign_ids" in (params or {}).get("filtering", ""):
            return {
                "code": 0,
                "data": {
                    "list": [
                        {
                            "campaign_id": "c1",
                            "campaign_name": "Campaign 1",
                            "advertiser_id": "123",
                            "objective_type": "TRAFFIC",
                            "primary_status": "STATUS_ENABLE",
                            "secondary_status": "SECONDARY_STATUS_NORMAL",
                        }
                    ]
                },
            }
        if endpoint == "campaign/get/":
            return {
                "code": 0,
                "data": {
                    "list": [
                        {
                            "campaign_id": "c1",
                            "campaign_name": "Campaign 1",
                            "objective_type": "TRAFFIC",
                            "primary_status": "STATUS_ENABLE",
                            "extra_field": "keep-me",
                        }
                    ],
                    "page_info": {"total_number": 1},
                },
            }
        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    from tiktok_ads_mcp.tools.campaign_tools import CampaignTools

    tools = CampaignTools(client)
    list_result = await tools.get_campaigns(limit=1)
    detail_result = await tools.get_campaign_details("c1")

    assert list_result["success"] is True
    assert list_result["data"]["entity_type"] == "campaign"
    assert isinstance(list_result["data"]["items"], list)
    assert list_result["data"]["items"][0]["campaign_id"] == "c1"
    assert list_result["data"]["items"][0]["extra_field"] == "keep-me"
    assert list_result["data"]["total_count"] == 1

    assert detail_result["success"] is True
    assert detail_result["data"]["entity_type"] == "campaign"
    assert detail_result["data"]["campaign_id"] == "c1"
    assert detail_result["data"]["item"]["campaign_id"] == "c1"
    assert detail_result["data"]["item"]["primary_status"] == "STATUS_ENABLE"


async def test_adgroup_and_ad_read_tools_use_consistent_shapes(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        filtering = (params or {}).get("filtering", "")
        if endpoint == "adgroup/get/" and "adgroup_ids" in filtering:
            return {"code": 0, "data": {"list": [{"adgroup_id": "ag1", "campaign_id": "c1"}]}}
        if endpoint == "adgroup/get/":
            return {
                "code": 0,
                "data": {
                    "list": [
                        {
                            "adgroup_id": "ag1",
                            "adgroup_name": "Ad Group 1",
                            "campaign_id": "c1",
                            "optimization_goal": "CLICK",
                            "extra_field": "keep-adgroup",
                        }
                    ],
                    "page_info": {"total_number": 1},
                },
            }
        if endpoint == "ad/get/" and "ad_ids" in filtering:
            return {"code": 0, "data": {"list": [{"ad_id": "ad1", "adgroup_id": "ag1", "campaign_id": "c1"}]}}
        if endpoint == "ad/get/":
            return {
                "code": 0,
                "data": {
                    "list": [
                        {
                            "ad_id": "ad1",
                            "ad_name": "Ad 1",
                            "adgroup_id": "ag1",
                            "campaign_id": "c1",
                            "creative_material_mode": "CUSTOM",
                            "extra_field": "keep-ad",
                        }
                    ],
                    "page_info": {"total_number": 1},
                },
            }
        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    from tiktok_ads_mcp.tools.campaign_tools import CampaignTools

    tools = CampaignTools(client)
    adgroup_list_result = await tools.get_adgroups("c1", limit=1)
    adgroup_detail_result = await tools.get_adgroup_details("ag1")
    ad_list_result = await tools.get_ads(campaign_ids=["c1"], limit=1)
    ad_detail_result = await tools.get_ad_details("ad1")

    assert adgroup_list_result["success"] is True
    assert adgroup_list_result["data"]["entity_type"] == "adgroup"
    assert adgroup_list_result["data"]["campaign_id"] == "c1"
    assert adgroup_list_result["data"]["items"][0]["adgroup_id"] == "ag1"
    assert adgroup_list_result["data"]["items"][0]["extra_field"] == "keep-adgroup"

    assert adgroup_detail_result["success"] is True
    assert adgroup_detail_result["data"]["entity_type"] == "adgroup"
    assert adgroup_detail_result["data"]["adgroup_id"] == "ag1"
    assert adgroup_detail_result["data"]["item"]["adgroup_id"] == "ag1"

    assert ad_list_result["success"] is True
    assert ad_list_result["data"]["entity_type"] == "ad"
    assert ad_list_result["data"]["items"][0]["ad_id"] == "ad1"
    assert ad_list_result["data"]["items"][0]["extra_field"] == "keep-ad"
    assert ad_list_result["data"]["applied_filters"]["campaign_ids"] == ["c1"]

    assert ad_detail_result["success"] is True
    assert ad_detail_result["data"]["entity_type"] == "ad"
    assert ad_detail_result["data"]["ad_id"] == "ad1"
    assert ad_detail_result["data"]["item"]["ad_id"] == "ad1"


async def test_ad_performance_uses_auction_ad_report(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )
    captured = {}

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"code": 0, "data": {"list": []}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    from tiktok_ads_mcp.tools.performance_tools import PerformanceTools

    tools = PerformanceTools(client)
    result = await tools.get_ad_performance(["ad1"], "last_7_days")

    assert result["success"] is True
    assert captured["method"] == "GET"
    assert captured["endpoint"] == "report/integrated/get/"
    assert captured["params"]["data_level"] == "AUCTION_AD"
    assert captured["params"]["dimensions"] == ["ad_id"]
    assert captured["params"]["filtering"][0]["field_name"] == "ad_ids"


async def test_pixel_and_location_endpoints(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )
    calls = []

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        calls.append(
            {
                "method": method,
                "endpoint": endpoint,
                "params": params,
                "data": data,
            }
        )
        return {"code": 0, "data": {"list": []}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    await client.get_location_info(["6252001"])
    await client.get_pixel_list(name="main")
    await client.get_pixel_event_stats(["pixel1"], "2026-01-01", "2026-01-07")

    assert calls[0]["method"] == "POST"
    assert calls[0]["endpoint"] == "tool/targeting/info/"
    assert calls[0]["data"]["targeting_ids"] == ["6252001"]
    assert calls[1]["endpoint"] == "pixel/list/"
    assert calls[1]["params"]["name"] == "main"
    assert calls[2]["endpoint"] == "pixel/event/stats/"
    assert calls[2]["params"]["pixel_ids"] == ["pixel1"]


async def test_audience_breakdown_uses_audience_report(monkeypatch):
    client = TikTokAdsClient(
        app_id="app",
        app_secret="secret",
        access_token="token",
        advertiser_id="123",
        available_advertiser_ids=["123"],
    )
    captured = {}

    async def fake_make_request(method, endpoint, params=None, data=None, files=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {"code": 0, "data": {"list": []}}

    monkeypatch.setattr(client, "_make_request", fake_make_request)

    await client.get_audience_breakdown(
        audience_dimension="age_gender",
        id_dimension="campaign_id",
        entity_ids=["c1"],
        start_date="2026-01-01",
        end_date="2026-01-07",
    )

    assert captured["endpoint"] == "report/integrated/get/"
    assert captured["params"]["report_type"] == "AUDIENCE"
    assert captured["params"]["data_level"] == "AUCTION_CAMPAIGN"
    assert captured["params"]["dimensions"] == ["campaign_id", "age", "gender"]
