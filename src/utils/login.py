#!/usr/bin/env python3
"""
Authenticate with Rossum API and create a client instance.
Uses ElisAPIClientSync for authentication and API interaction.
"""

import sys
import argparse
import logging
import os

# Local imports
from utils.config import API_BASE_URL, EMAIL, PASSWORD, save_auth_token, API_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_api_client(username, password=None, base_url=API_BASE_URL, token=None):
    """
    Create and authenticate an ElisAPIClientSync client.
    
    Args:
        username (str): The username (email) to use for authentication (can be None if token is provided)
        password (str): The password to use for authentication (can be None if token is provided)
        base_url (str): The base URL of the Rossum API
        token (str): Optional API token for authentication (if provided, username and password are ignored)
        
    Returns:
        tuple: (client, token) - The authenticated API client and the token used
    """
    try:
        from rossum_api import ElisAPIClientSync
        
        # Make sure we don't have double slashes in the URL
        base_url = base_url.rstrip("/")
        
        # Ensure base_url ends with /v1
        if not base_url.endswith('/v1'):
            if base_url.endswith('/api'):
                base_url = f"{base_url}/v1"
            elif "/api" not in base_url and "rossum.app" in base_url:
                base_url = f"{base_url}/api/v1"
            elif not base_url.endswith('/api/v1'):
                base_url = f"{base_url}/v1"
                
        logger.info(f"Using API URL: {base_url}")
        
        # Log authentication method
        logger.info(f"Creating API client with username/password authentication as {username}")
        client = ElisAPIClientSync(
            username=username,
            password=password,
            base_url=base_url,
        )
        
        # Test the connection by making a simple API call
        try:
            workspaces = client.list_all_workspaces(limit=1)
            # Force evaluation of generator to ensure we're connected
            next(iter(workspaces), None)
            logger.info("Connection test successful")
        except Exception as e:
            logger.warning(f"Could not list workspaces: {str(e)}")
            # Continue anyway as we might still have the token
        
        # Extract the token from the client if it wasn't provided
        extracted_token = token
        if not extracted_token:
            if hasattr(client, '_token'):
                extracted_token = client._token
            elif hasattr(client, '_http_client') and hasattr(client._http_client, '_token'):
                extracted_token = client._http_client._token
        
        if extracted_token:
            logger.info("Authentication successful!")
            return client, extracted_token
        else:
            logger.warning("Client created but couldn't extract token")
            return client, None
            
    except Exception as e:
        logger.error(f"Failed to create API client: {str(e)}")
        return None, None

def get_client():
    """
    Get an authenticated API client using environment variables or configuration.
    
    Returns:
        ElisAPIClientSync: The authenticated API client
    """
    token = API_TOKEN or os.environ.get("ROSSUM_TOKEN")
    if token:
        logger.info("Creating client with token authentication")
        client, _ = create_api_client(None, None, API_BASE_URL, token)
        return client
    
    username = EMAIL or os.environ.get("ROSSUM_USERNAME")
    password = PASSWORD or os.environ.get("ROSSUM_PASSWORD")
    
    if username and password:
        logger.info(f"Creating client with username/password authentication as {username}")
        client, _ = create_api_client(username, password, API_BASE_URL)
        return client
    
    logger.error("No authentication information available. Please set ROSSUM_TOKEN or username/password.")
    return None

def main():
    """Main function to parse arguments and create an authenticated API client."""
    parser = argparse.ArgumentParser(description="Authenticate with Rossum API and create client")
    parser.add_argument("--username", help="Username (email) for Rossum API")
    parser.add_argument("--password", help="Password for Rossum API")
    parser.add_argument("--token", help="API token for authentication (alternative to username/password)")
    parser.add_argument("--base-url", help="Base URL for Rossum API", default=API_BASE_URL)
    parser.add_argument("--save", action="store_true", help="Save token to .env file")
    
    args = parser.parse_args()
    
    # Get credentials from arguments or environment variables
    username = args.username or EMAIL
    password = args.password or PASSWORD
    base_url = args.base_url or API_BASE_URL
    token = args.token
    
    if not token and (not username or not password):
        logger.error("Either a token or username and password are required. Provide them as arguments or set them in the .env file.")
        sys.exit(1)
    
    # Create and authenticate the client
    client, extracted_token = create_api_client(username, password, base_url, token)
    
    if client:
        if extracted_token:
            logger.info(f"Token: {extracted_token}")
            
            if args.save and extracted_token:
                save_auth_token(extracted_token)
                     
            return client, extracted_token
        else:
            logger.warning("Client created but couldn't extract token")
            return client, None
    else:
        logger.error("Failed to create API client")
        sys.exit(1)

if __name__ == "__main__":
    main()