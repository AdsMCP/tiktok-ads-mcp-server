# TikTok Ads MCP Server

A local Model Context Protocol (MCP) server for TikTok Ads API integration. It lets MCP clients such as Claude Desktop connect to TikTok Ads, authenticate with a TikTok Business app, and use read-only tools for campaign lookup, ad group and ad inspection, performance reporting, audience breakdowns, advertiser info, pixels, and targeting locations.

## What This Server Does

- **Authentication**: Start and complete TikTok Ads OAuth from an MCP client.
- **Campaign lookup**: List campaigns, inspect campaign details, list ad groups, and inspect ads.
- **Performance analytics**: Pull campaign, ad group, ad, and audience metrics for common date ranges.
- **Audience and account data**: Retrieve custom audiences, advertiser info, location IDs, pixels, and pixel event stats.
- **Read-only operation**: The public MCP tool registry does not expose campaign creation, ad group creation, creative upload, or other write operations.

## Hosted Option

This repository is for users who want to run a local TikTok Ads MCP server.

If you do not want to install Python, manage dependencies, or configure a TikTok developer app, [AdsMCP](https://adsmcp.com) provides a hosted remote MCP server:

[AdsMCP Remote MCP Server Setup Guide](https://adsmcp.com/onboarding)

The rest of this README covers the local setup.

## Prerequisites

You need:

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- A TikTok For Business account with Marketing API access
- A TikTok developer app with an App ID and App Secret
- An MCP client that supports local stdio servers, such as Claude Desktop

### Install uv

macOS and Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, confirm that `uv` is available:

```bash
uv --version
```

Find the absolute path to `uv` before configuring a desktop MCP client:

macOS and Linux:

```bash
whereis uv
which uv
```

Use the path returned by `whereis uv` or `which uv` as the MCP `command` value if your client cannot find `uv` by name.

Windows PowerShell:

```powershell
where.exe uv
```

Common paths are:

- macOS/Linux: `/Users/<your-name>/.local/bin/uv`
- Windows: `C:\\Users\\<your-name>\\.local\\bin\\uv.exe`

## Install Locally

Clone the repository and install dependencies:

```bash
git clone https://github.com/AdsMCP/tiktok-ads-mcp-server.git
cd tiktok-ads-mcp-server
uv sync
```

Find the absolute path to the project directory. You will use this path in the MCP config as the `uv --directory` value:

macOS and Linux:

```bash
pwd
```

Windows PowerShell:

```powershell
Get-Location
```

Verify that the project environment can import MCP:

```bash
uv run python -c "from mcp.server import Server; print('ok')"
```

You should see:

```text
ok
```

## Important: Use uv to Run the Server

Do not configure your MCP client to run this server with system `python` or `python3` unless you have manually installed all dependencies into that exact Python environment.

Use this:

```bash
uv run python run_server.py
```

Not this:

```bash
python run_server.py
python3 run_server.py
```

Why: MCP desktop apps often launch a different Python than the one you use in your terminal. If that Python does not have the `mcp` package installed, the server exits with:

```text
No module named 'mcp'
```

`uv run` makes the MCP client use this project's dependency environment.

## Configure Claude Desktop

Claude Desktop reads its MCP server config from:

macOS:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

Windows:

```text
%APPDATA%\\Claude\\claude_desktop_config.json
```

Linux paths vary by distribution and client package, but they are usually under:

```text
~/.config/Claude/
```

### macOS / Linux Config

Use `uv --directory` so the server starts from the project directory even if your MCP client does not apply `cwd` correctly.

To fill in `"/absolute/path/to/tiktok-ads-mcp-server"`, open a terminal in the cloned repository and run:

```bash
pwd
```

Use the printed value as the `--directory` argument. If Claude cannot find `uv`, replace `"uv"` with the absolute path from `whereis uv` or `which uv`, such as `"/Users/yourname/.local/bin/uv"`.

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/tiktok-ads-mcp-server",
        "run",
        "python",
        "run_server.py"
      ],
      "env": {
        "TIKTOK_APP_ID": "your_app_id",
        "TIKTOK_APP_SECRET": "your_app_secret"
      }
    }
  }
}
```

### Windows Config

Use escaped backslashes in JSON paths. To find the project path, open PowerShell in the cloned repository and run:

```powershell
Get-Location
```

Use the printed value as the `--directory` argument, with each `\` escaped as `\\` in JSON:

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\tiktok-ads-mcp-server",
        "run",
        "python",
        "run_server.py"
      ],
      "env": {
        "TIKTOK_APP_ID": "your_app_id",
        "TIKTOK_APP_SECRET": "your_app_secret"
      }
    }
  }
}
```

If Claude cannot find `uv` on Windows, use the full path:

```json
"command": "C:\\Users\\yourname\\.local\\bin\\uv.exe"
```

After editing the config, fully restart Claude Desktop.

## TikTok App Setup

1. Go to the [TikTok For Business Developer Portal](https://business-api.tiktok.com/).
2. Create or open a developer app.
3. Copy the App ID and App Secret.
4. Make sure the redirect URI configured in your TikTok app matches the redirect URI used by this server. By default, this project uses:

```text
https://adsmcp.com
```

5. Add the App ID and App Secret to your MCP client config under `env`.

## Authentication Flow

Once the MCP server is connected:

1. Run `tiktok_ads_login` from your MCP client.
2. Open the authorization URL returned by the tool.
3. Approve access in TikTok.
4. Copy the `code` parameter from the redirect URL.
5. Run `tiktok_ads_complete_auth` with that code.
6. Run `tiktok_ads_auth_status` to confirm the account is authenticated.

## Token Storage and Security

After OAuth completes, TikTok access and refresh tokens are stored locally under:

```text
~/.tiktok_ads_mcp/tokens.json
```

This file is what lets the local MCP server call TikTok Marketing API after you authenticate. Treat it like a password:

- Do not commit it to Git or share it in issue reports.
- Keep it on your own machine and protect it with your normal OS account permissions.
- Remove it if you want to disconnect the local server from your TikTok account.

The local server stores tokens only for the TikTok account you authorize, and only so it can make authenticated TikTok API calls for that account.

## Available Tools

The local server currently exposes the following tools through its MCP registry.
This list is the source of truth for the open-source package.

### Authentication

- `tiktok_ads_login` - Start TikTok Ads OAuth authentication.
- `tiktok_ads_complete_auth` - Complete OAuth using the authorization code.
- `tiktok_ads_auth_status` - Check current authentication status.
- `tiktok_ads_switch_ad_account` - Switch to a different advertiser account.

### Campaign Management

- `tiktok_ads_get_campaigns` - Retrieve campaigns for the advertiser account.
- `tiktok_ads_get_campaign_details` - Get details for a specific campaign.
- `tiktok_ads_get_adgroups` - Retrieve ad groups for a campaign.
- `tiktok_ads_get_adgroup_details` - Get details for a specific ad group.
- `tiktok_ads_get_ads` - Retrieve ads by campaign, ad group, ad ID, or status.
- `tiktok_ads_get_ad_details` - Get details for a specific ad.

### Performance and Analytics

- `tiktok_ads_get_campaign_performance` - Get campaign-level metrics.
- `tiktok_ads_get_adgroup_performance` - Get ad group-level metrics.
- `tiktok_ads_get_ad_performance` - Get ad-level metrics.
- `tiktok_ads_get_audience_breakdown` - Break down campaign, ad group, or ad performance by audience dimension.
- `tiktok_ads_wasted_spend_audit` - Run a read-only audit for spend and clicks without conversion signal.

### Creative and Audience

- `tiktok_ads_get_custom_audiences` - List custom audiences.
- `tiktok_ads_get_advertiser_info` - Get account-level advertiser details such as currency, timezone, status, industry, country, and creation time.
- `tiktok_ads_get_location_info` - Resolve TikTok targeting location IDs.
- `tiktok_ads_get_pixel_list` - List pixels attached to the advertiser account.
- `tiktok_ads_get_pixel_event_stats` - Get pixel event activity for a date range.

## Implementation Audit

Current MCP tools are only listed when they are wired to real OAuth, local token
state, or TikTok Marketing API calls. This repository does not expose placeholder
or mock tools.

| Tool | Backing implementation |
| --- | --- |
| `tiktok_ads_login` | Starts TikTok OAuth and returns an authorization URL. |
| `tiktok_ads_complete_auth` | Exchanges an OAuth code for TikTok tokens and stores them locally. |
| `tiktok_ads_auth_status` | Checks local configuration and saved token state. |
| `tiktok_ads_switch_ad_account` | Switches the active local advertiser account after authentication. |
| `tiktok_ads_get_campaigns` | Calls TikTok Marketing API `campaign/get/`. |
| `tiktok_ads_get_campaign_details` | Calls TikTok Marketing API `campaign/get/` with `campaign_ids` filtering. |
| `tiktok_ads_get_adgroups` | Calls TikTok Marketing API `adgroup/get/`. |
| `tiktok_ads_get_adgroup_details` | Calls TikTok Marketing API `adgroup/get/` with `adgroup_ids` filtering. |
| `tiktok_ads_get_ads` | Calls TikTok Marketing API `ad/get/`. |
| `tiktok_ads_get_ad_details` | Calls TikTok Marketing API `ad/get/` with `ad_ids` filtering. |
| `tiktok_ads_get_campaign_performance` | Calls TikTok Marketing API `report/integrated/get/` at campaign level. |
| `tiktok_ads_get_adgroup_performance` | Calls TikTok Marketing API `report/integrated/get/` at ad group level. |
| `tiktok_ads_get_ad_performance` | Calls TikTok Marketing API `report/integrated/get/` at ad level. |
| `tiktok_ads_get_audience_breakdown` | Calls TikTok Marketing API `report/integrated/get/` with `report_type=AUDIENCE`. |
| `tiktok_ads_wasted_spend_audit` | Read-only workflow that calls `campaign/get/`, `adgroup/get/`, and `report/integrated/get/`. |
| `tiktok_ads_get_custom_audiences` | Calls TikTok Marketing API `dmp/custom_audience/list/`. |
| `tiktok_ads_get_advertiser_info` | Calls TikTok Marketing API `advertiser/info/` and enriches with recent spend dates from `report/integrated/get/`. |
| `tiktok_ads_get_location_info` | Calls TikTok Marketing API `tool/targeting/info/`. |
| `tiktok_ads_get_pixel_list` | Calls TikTok Marketing API `pixel/list/`. |
| `tiktok_ads_get_pixel_event_stats` | Calls TikTok Marketing API `pixel/event/stats/`. |

## Roadmap

Planned areas:

- Broader GMV Max campaign coverage.
- Safe write operations for campaigns, ad groups, ads, and assets.
- Creative and asset management.
- Full async report lifecycle: create, status, and download.
- Targeting discovery and audience management.

## Troubleshooting

### Failed to spawn process: No such file or directory

The MCP client cannot find the command you configured.

Fix:

- Use `"command": "uv"` if `uv` is on the app's PATH.
- Otherwise use the full path, for example:

```json
"command": "/Users/yourname/.local/bin/uv"
```

### No module named 'mcp'

You are running the server with system Python instead of the project's environment.

Fix your MCP config to use:

```json
"command": "uv",
"args": ["--directory", "/path/to/tiktok-ads-mcp-server", "run", "python", "run_server.py"]
```

Then run:

```bash
cd /path/to/tiktok-ads-mcp-server
uv sync
```

### can't open file '//run_server.py'

Your MCP client started `uv`, but it did not run the command from the project directory.

Fix your MCP config to put the project directory in the `uv` arguments instead of relying on `cwd`:

```json
"command": "uv",
"args": ["--directory", "/path/to/tiktok-ads-mcp-server", "run", "python", "run_server.py"]
```

### Missing TikTok API credentials

The server did not receive `TIKTOK_APP_ID` or `TIKTOK_APP_SECRET`.

Fix:

- Add both values under `env` in your MCP client config.
- Restart your MCP client after changing the config.

### OAuth succeeds, but tools still say unauthenticated

Check whether the token file exists:

```bash
ls ~/.tiktok_ads_mcp/tokens.json
```

If you want to restart authentication, remove the token file and run `tiktok_ads_login` again:

```bash
rm ~/.tiktok_ads_mcp/tokens.json
```

### Claude Desktop still shows the old error after config changes

Fully quit and reopen Claude Desktop. On macOS, closing the window is not always enough.

## Security Notes

- Do not commit `.env`, token files, App Secrets, or OAuth codes.
- Keep `~/.tiktok_ads_mcp/tokens.json` private.
- Use a TikTok developer app with only the permissions you need.
- The current public MCP registry is read-only for TikTok Ads objects. Write operations are roadmap items and should be reviewed carefully before being exposed.

## Development

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run --extra dev pytest
```

Run the server manually:

```bash
uv run python run_server.py
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Support

For issues and questions, please create an issue in this repository.
