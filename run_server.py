#!/usr/bin/env python3
"""Entry point script for TikTok Ads MCP Server."""

import asyncio
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from tiktok_ads_mcp.server import main
    
    if __name__ == "__main__":
        asyncio.run(main())
        
except Exception as e:
    print(f"Error starting TikTok Ads MCP server: {e}", file=sys.stderr)
    sys.exit(1)