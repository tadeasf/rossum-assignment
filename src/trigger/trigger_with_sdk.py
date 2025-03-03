#!/usr/bin/env python3
"""
Simple script to trigger a Rossum serverless function using the /test endpoint.
"""

import json
import logging
import sys
import pycurl
from io import BytesIO
from utils.config import API_BASE_URL
from utils.login import get_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_hook(hook_id, base_url=API_BASE_URL, debug_token=None):
    """
    Simple function to test a hook using the /test endpoint.
    """
    if not hook_id:
        logger.error("No hook ID provided")
        sys.exit(1)
    
    # 1. Get client and token
    logger.info(f"Getting client for API URL: {base_url}")
    client = get_client()
    
    # Use provided debug token or get from client
    if debug_token:
        logger.info("Using provided debug token")
        token = debug_token
    else:
        # Extract token from client - simplified to just use get_token()
        try:
            token = client.get_token()
            if not token:
                logger.error("Token returned from client.get_token() is empty")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error getting token from client: {str(e)}")
            sys.exit(1)
    
    # Print masked token
    masked_token = token[:4] + "..." + token[-4:] if len(token) > 10 else "****"
    logger.info(f"Using token (masked): {masked_token}")
    
    # Format URL
    base_url = base_url.rstrip("/")
    test_url = f"{base_url}/hooks/{hook_id}/test"
    logger.info(f"Test URL: {test_url}")
    
    # 2. Create payload like curl command
    payload = {
        "payload": {
            "action": "manual",
            "event": "invocation",
            "base_url": "https://test-company-tadeas.rossum.app",
            "rossum_authorization_token": token,
            "annotation": {},
            "document": {},
            "settings": {
                "annotation_id": 7992402
            }
        }
    }
    
    # Print the equivalent curl command for comparison
    logger.info("Equivalent curl command:")
    print(f"""
curl '{test_url}' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Token {token}' \\
  -d '{json.dumps(payload, indent=2)}'
""")
    
    logger.info(f"Using payload: {json.dumps(payload, indent=2)}")
    
    # 3. Make the request with pycurl
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, test_url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.HTTPHEADER, [
        f'Authorization: Token {token}',
        'Content-Type: application/json'
    ])
    c.setopt(c.POST, 1)
    c.setopt(c.POSTFIELDS, json.dumps(payload))
    
    # Add verbose debugging
    c.setopt(c.VERBOSE, 1)
    
    # Execute the request
    logger.info("Sending request...")
    c.perform()
    
    # Get status code
    status_code = c.getinfo(c.RESPONSE_CODE)
    c.close()
    
    # Get response body
    response_body = buffer.getvalue().decode('utf-8')
    
    # 4. Show response
    logger.info(f"Response status: {status_code}")
    try:
        response_data = json.loads(response_body) if response_body else {}
        print("\nResponse:")
        print(json.dumps(response_data, indent=2))
    except json.JSONDecodeError:
        print("\nResponse (non-JSON):")
        print(response_body)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python trigger_with_sdk.py <hook_id> [base_url] [debug_token]")
        sys.exit(1)
    
    hook_id = sys.argv[1]
    base_url = API_BASE_URL
    debug_token = None
    
    # Use custom base URL if provided
    if len(sys.argv) > 2:
        base_url = sys.argv[2]
    
    # Use debug token if provided
    if len(sys.argv) > 3:
        debug_token = sys.argv[3]
        
    test_hook(hook_id, base_url, debug_token) 