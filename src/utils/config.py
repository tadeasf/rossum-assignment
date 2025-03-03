#!/usr/bin/env python3
"""
Configuration settings for the Rossum serverless function.
Loads environment variables and provides a central place for configuration.
"""

import os
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Find and load .env file
ENV_PATH = Path('.') / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# API settings
API_TOKEN = os.getenv('ROSSUM_API_TOKEN', '')
API_BASE_URL = os.getenv('ROSSUM_BASE_URL', 'https://test-company-tadeas.rossum.app/api/v1')

# Authentication settings
EMAIL = os.getenv('ROSSUM_EMAIL', '')
PASSWORD = os.getenv('ROSSUM_PASSWORD', '')
COMPANY_ID = os.getenv('ROSSUM_COMPANY_ID', '')

# Default values for testing
DEFAULT_QUEUE = os.getenv('ROSSUM_DEFAULT_QUEUE', '')
DEFAULT_SCHEMA = os.getenv('ROSSUM_DEFAULT_SCHEMA', '')
DEFAULT_ANNOTATION_ID = os.getenv('DEFAULT_ANNOTATION_ID', '')
DEFAULT_FUNCTION_NAME = os.getenv('DEFAULT_FUNCTION_NAME', 'XML Exporter')
DEFAULT_FUNCTION_FILE = os.getenv('DEFAULT_FUNCTION_FILE', 'src/rossum_hook.py')
DEFAULT_HOOK_ID = os.getenv('DEFAULT_HOOK_ID', '603851')  # Default to the ID from the example
POSTBIN_URL = os.getenv('POSTBIN_URL', '')
DEFAULT_TEST_FILE = os.getenv('DEFAULT_TEST_FILE', '')

def normalize_api_url(url):
    """
    Normalize the API URL to ensure it has the correct format.
    
    Args:
        url (str): The URL to normalize
        
    Returns:
        str: The normalized URL
    """
    if not url:
        return API_BASE_URL
        
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # If this is a rossum.app domain and doesn't have /api in it, add it
    if "rossum.app" in url and "/api" not in url:
        url = f"{url}/api"
    
    # Ensure it ends with /v1
    if not url.endswith('/v1'):
        url = f"{url}/v1"
    
    return url

def determine_api_url(url=None):
    """
    Determine the API URL based on the provided URL or the environment variable.
    Normalizes the URL to ensure it's properly formatted for API calls.
    
    Args:
        url (str, optional): The URL to use. If None, use the environment variable.
        
    Returns:
        str: The properly formatted API URL
    """
    # Use the provided URL or fall back to the environment variable
    api_url = url if url else API_BASE_URL
    
    # Normalize the URL to ensure proper format
    return normalize_api_url(api_url)


def get_auth_header(token=None):
    """
    Get the authorization header for API requests.
    
    Args:
        token (str, optional): The token to use. If None, use the environment variable.
        
    Returns:
        dict: The authorization header
    """
    token = token or API_TOKEN
    if not token:
        logger.warning("No token provided for authorization header")
        return {}
    return {"Authorization": f"Token {token}"}

def save_auth_token(token):
    """
    Save the authentication token to the .env file.
    
    Args:
        token (str): The token to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the contents of the .env file
        with open(ENV_PATH, 'r') as f:
            content = f.read()
            
        # Check if the token already exists in the file
        token_pattern = re.compile(r'^ROSSUM_API_TOKEN=.*$', re.MULTILINE)
        
        if token_pattern.search(content):
            # Replace the existing token
            content = token_pattern.sub(f'ROSSUM_API_TOKEN="{token}"', content)
        else:
            # Add the token at the beginning of the file
            content = f'ROSSUM_API_TOKEN="{token}"\n{content}'
            
        # Write the updated content back to the file
        with open(ENV_PATH, 'w') as f:
            f.write(content)
            
        logger.info("Token saved to .env file")
        return True
        
    except Exception as e:
        logger.error(f"Error saving token to .env file: {str(e)}")
        return False

def get_api_client_config() -> Dict[str, Any]:
    """
    Get configuration for creating an API client.
    
    Returns:
        Dict[str, Any]: The configuration dict with username, password, and base_url
    """
    return {
        "username": EMAIL,
        "password": PASSWORD,
        "base_url": API_BASE_URL,
        "token": API_TOKEN,
        "company_id": COMPANY_ID
    }
