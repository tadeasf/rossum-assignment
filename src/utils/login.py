#!/usr/bin/env python3
"""
Authenticate with Rossum API and create a client instance.
Uses ElisAPIClientSync for authentication and API interaction.
"""
import argparse
import logging

# Local imports
from utils.config import API_BASE_URL, EMAIL, PASSWORD, save_auth_token

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global client instance for reuse
_api_client = None

def create_api_client(username=None, password=None, base_url=None):
    """
    Create and authenticate an ElisAPIClientSync client.
    
    If username, password, or base_url are None, they will be loaded from config.
    
    Args:
        username (str, optional): The username (email) to use for authentication
        password (str, optional): The password to use for authentication
        base_url (str, optional): The base URL of the Rossum API
        
    Returns:
        ElisAPIClientSync: The authenticated API client
    """
    try:
        from rossum_api import ElisAPIClientSync
        
        # Use provided values or fall back to config
        _username = username if username is not None else EMAIL
        _password = password if password is not None else PASSWORD
        _base_url = base_url if base_url is not None else API_BASE_URL
        
        # Make sure we don't have double slashes in the URL
        _base_url = _base_url.rstrip("/")
        
        # Ensure base_url ends with /v1
        if not _base_url.endswith('/v1'):
            if _base_url.endswith('/api'):
                _base_url += '/v1'
            else:
                _base_url += '/api/v1'
                
        logger.info(f"Creating API client with base URL: {_base_url}")
        
        # Create API client
        client = ElisAPIClientSync(
            base_url=_base_url,
            username=_username,
            password=_password,
        )
        
        return client
        
    except ImportError as e:
        logger.error(f"Failed to import ElisAPIClientSync: {str(e)}")
        logger.info("Trying to install rossum_api package...")
        import subprocess
        subprocess.check_call(["pip", "install", "rossum_api"])
        from rossum_api import ElisAPIClientSync
        logger.info("Successfully installed rossum_api package")
        
        # Retry creating the client after installing the package
        return create_api_client(username, password, base_url)
        
    except Exception as e:
        logger.error(f"Error creating API client: {str(e)}")
        raise

def get_client():
    """
    Get a reusable authenticated API client instance.
    
    This function reuses the same client instance if possible.
    
    Returns:
        ElisAPIClientSync: The authenticated API client
    """
    global _api_client
    
    if _api_client is None:
        _api_client = create_api_client()
        
    return _api_client

def get_auth_token():
    """
    Get authentication token from Rossum API.
    
    Returns:
        str: Authentication token
    """
    logger.info("Getting token from Rossum SDK client")
    client = get_client()
    token = client.get_token()
    return token

def main():
    """
    Command-line interface for testing authentication with Rossum API.
    """
    parser = argparse.ArgumentParser(description='Test authentication with Rossum API')
    parser.add_argument('--save-token', action='store_true', help='Save auth token to file')
    args = parser.parse_args()
    
    try:
        client = get_client()
        token = client.get_token()
        
        logger.info("Successfully authenticated with Rossum API")
        logger.info(f"Token: {token[:10]}...")
        
        if args.save_token:
            save_auth_token(token)
            logger.info("Saved authentication token")
        
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())