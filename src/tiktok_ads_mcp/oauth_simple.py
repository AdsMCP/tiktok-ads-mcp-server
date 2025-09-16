"""Simplified OAuth for MCP that doesn't block the server."""

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import urllib.parse
import webbrowser
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class SimpleTikTokOAuth:
    """Simplified TikTok OAuth that generates manual auth URL."""

    AUTHORIZATION_URL = "https://business-api.tiktok.com/portal/auth"
    TOKEN_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
    
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str = "https://adsmcp.com"):
        """Initialize OAuth client.
        
        Args:
            app_id: TikTok app ID
            app_secret: TikTok app secret
            redirect_uri: OAuth redirect URI configured in your TikTok app
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge."""
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    def get_authorization_url(self) -> str:
        """Generate authorization URL for OAuth flow."""

        params = {
            'app_id': self.app_id,
            'redirect_uri': self.redirect_uri,
        }
        
        url = f"{self.AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"
        return url
    
    async def exchange_code_for_token(self, auth_code: str) -> Optional[Dict]:
        """Exchange authorization code for access token."""
        try:
            data = {
                'app_id': self.app_id,
                'secret': self.app_secret,
                'auth_code': auth_code,
            }
            header = {
                "Content-Type": "application/json"
            }
            logger.info(f"Requesting token with data: {data}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.TOKEN_URL, json=data, headers=header)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Token exchange result: {result}")
                if result.get('code') != 0:
                    error_msg = result.get('message', 'Unknown error')
                    logger.error(f"Token exchange failed: {error_msg}")
                    return {
                        "error_message": error_msg
                    }
                
                token_data = result.get('data', {})
                access_token = token_data.get('access_token')
                advertiser_ids = token_data.get('advertiser_ids', [])
                
                # Save tokens
                self._save_tokens(access_token, advertiser_ids)
                
                return {
                    'access_token': access_token,
                    'advertiser_ids': advertiser_ids,
                    'primary_advertiser_id': advertiser_ids[0] if advertiser_ids else None
                }
                
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return {
                "error_message": str(e)
            }
    
    def _save_tokens(self, access_token: str, advertiser_ids: list):
        """Save tokens to file."""
        token_file = os.path.expanduser("~/.tiktok_ads_mcp/tokens.json")
        token_data = {
            'access_token': access_token,
            'advertiser_ids': advertiser_ids,
            'timestamp': int(time.time())
        }
        
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        logger.info(f"Tokens saved to {token_file}")
    
    def load_saved_tokens(self) -> Optional[Dict]:
        """Load previously saved tokens."""
        token_file = os.path.expanduser("~/.tiktok_ads_mcp/tokens.json")
        
        try:
            if not os.path.exists(token_file):
                return None
                
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            return {
                'access_token': token_data.get('access_token'),
                'advertiser_ids': token_data.get('advertiser_ids', []),
                'primary_advertiser_id': token_data.get('advertiser_ids', [None])[0]
            }
            
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            return None


def start_manual_oauth(app_id: str, app_secret: str, force_reauth: bool = False) -> Tuple[Dict[str, str], Optional[Dict]]:
    """Start manual OAuth flow that doesn't block the server."""
    oauth_client = SimpleTikTokOAuth(app_id, app_secret)
    
    # Check for existing tokens first
    saved_tokens = oauth_client.load_saved_tokens()
    if saved_tokens and saved_tokens.get('access_token') and not force_reauth:
        return {
            'authenticated': True,
            'advertiser_ids': saved_tokens.get('advertiser_ids', []),
            'primary_advertiser_id': saved_tokens.get('primary_advertiser_id'),
            'message': 'Already authenticated with saved tokens',
        }, saved_tokens
    
    # Generate auth URL
    auth_url = oauth_client.get_authorization_url()
    
    # Open browser
    webbrowser.open(auth_url)
    
    return {
        'status': 'auth_started',
        'message': 'Browser opened for authentication. After authorizing, use tiktok_complete_auth with the authorization code.',
        'auth_url': auth_url,
        'instructions': [
            '1. Complete authorization in the opened browser',
            '2. You will be redirected to your configured redirect URI',
            '3. Copy the "code" parameter from the redirect URL',
            '4. Use the tiktok_complete_auth tool with that code'
        ]
    },None