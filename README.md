# TikTok Ads MCP Server

A Model Context Protocol (MCP) server for TikTok Ads API integration. This server enables AI assistants like Claude to interact with TikTok advertising campaigns, providing comprehensive campaign management, analytics, and optimization capabilities.

Part of the [AdsMCP](https://adsmcp.com) project - MCP servers for advertising platforms.

## Features

- **Campaign Management**: Create, read, and update campaigns and ad groups
- **Performance Analytics**: Retrieve detailed performance metrics and insights
- **Audience Management**: Handle custom audiences and targeting options
- **Creative Management**: Upload and manage ad creatives
- **Reporting**: Generate and download custom performance reports

## Installation

### Prerequisites

- Python 3.10+
- TikTok For Business account with API access
- TikTok Ads Developer account and app registration

### Local Installation

```bash
# Clone the repository
git clone <repository-url>
cd adsmcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Using uv (recommended)

```bash
# Install with uv
uv sync
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
TIKTOK_APP_ID=your_app_id
TIKTOK_APP_SECRET=your_app_secret
TIKTOK_ACCESS_TOKEN=your_access_token
TIKTOK_ADVERTISER_ID=your_advertiser_id
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "tiktok-ads": {
      "command": "python",
      "args": ["/path/to/adsmcp-server/run_server.py"],
      "env": {
        "TIKTOK_APP_ID": "your_app_id",
        "TIKTOK_APP_SECRET": "your_app_secret",
        "TIKTOK_ACCESS_TOKEN": "your_access_token",
        "TIKTOK_ADVERTISER_ID": "your_advertiser_id"
      }
    }
  }
}
```

## Available Tools

### Authentication
- `tiktok_login` - Start TikTok Ads OAuth authentication flow
- `tiktok_complete_auth` - Complete OAuth authentication with authorization code
- `tiktok_auth_status` - Check current authentication status
- `switch_ad_account` - Switch to a different advertiser account

### Campaign Management
- `get_campaigns` - Retrieve all campaigns for the advertiser account
- `get_campaign_details` - Get detailed information about a specific campaign
- `get_adgroups` - Retrieve ad groups for a campaign

### Performance & Analytics
- `get_campaign_performance` - Get performance metrics for campaigns with detailed metrics support
- `get_adgroup_performance` - Get performance metrics for ad groups with breakdowns

## Authentication

### TikTok Ads API Setup

1. **Register as Developer**
   - Visit [TikTok For Business Developer Portal](https://business-api.tiktok.com/)
   - Create a developer account
   - Register your application

2. **Get API Credentials**
   - App ID and App Secret from your registered app
   - Generate access token through OAuth flow
   - Note your Advertiser ID

3. **OAuth Flow** (for production)
   - Implement OAuth 2.0 flow for user authorization
   - Handle token refresh automatically
   - Store tokens securely

### Development vs Production

- **Development**: Use long-lived access tokens
- **Production**: Implement full OAuth flow with refresh tokens

## Security Best Practices

- Never commit API credentials to version control
- Use environment variables for sensitive data
- Implement proper token rotation
- Monitor API usage and rate limits
- Use HTTPS for all communications

## API Rate Limits

TikTok Ads API has the following limits:
- 1000 requests per hour per app
- 10 concurrent requests
- Specific endpoint limits may apply

The server includes built-in rate limiting and retry logic.

## Error Handling

The server provides comprehensive error handling:
- API rate limit management
- Token expiration handling
- Network connectivity issues
- Invalid parameter validation

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=tiktok_ads_mcp
```

### Code Formatting

```bash
# Format code
black .
isort .

# Type checking
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, please create an issue in this repository.

## Changelog

### v0.1.0 (Initial Release)
- Basic TikTok Ads API integration
- Campaign and ad group management
- Performance reporting
- OAuth authentication support