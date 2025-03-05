#!/usr/bin/env python3
"""
Trigger a webhook test using the Rossum SDK.
This script sends a test request to a webhook with a simulated annotation event.
"""

import json
import logging
import os
import yaml
import pycurl
from io import BytesIO
from utils.login import get_auth_token as get_token

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

####### STEP 1: Load YAML Configuration #######
def load_config(yaml_path):
    """
    Load configuration from YAML file
    
    Args:
        yaml_path (str): Path to YAML configuration file
        
    Returns:
        dict: Configuration data
    """
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create absolute path to config.yml in the same directory
    config_path = os.path.join(script_dir, yaml_path)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        logger.info(f"Successfully loaded configuration from {config_path}")
        return config

####### STEP 2: Get Authentication Token #######
def get_auth_token():
    """
    Get authentication token from Rossum SDK        
    Returns:
        str: Authentication token
    """
    logger.info("Getting token from Rossum SDK client")
    return get_token()

####### STEP 3: Send Test Request to Rossum API #######
def send_test_request(hook_id, token, payload, base_url):
    """
    Send test request to Rossum API
    
    Args:
        hook_id (str): Hook ID
        token (str): Authentication token
        payload (dict): Request payload
        base_url (str): Base API URL
        
    Returns:
        dict: Response data
    """
    # Prepare test URL
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    test_url = f"{base_url}/hooks/{hook_id}/test"
    logger.info(f"Sending test request to: {test_url}")
    
    # Send request with PyCurl
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
    c.setopt(c.VERBOSE, 1)
    
    logger.info("Sending request...")
    c.perform()
    
    status_code = c.getinfo(c.RESPONSE_CODE)
    c.close()
    
    logger.info(f"Response status code: {status_code}")
    
    # Parse response
    response_body = buffer.getvalue().decode('utf-8')
    try:
        response_data = json.loads(response_body) if response_body else {}
        return {
            "status": "success", 
            "code": status_code, 
            "response": response_data
        }
    except json.JSONDecodeError:
        return {
            "status": "success", 
            "code": status_code, 
            "response_text": response_body
        }

####### MAIN TEST HOOK FUNCTION #######
def test_hook(hook_id, annotation_id="7992402", base_url=None, debug_token=None, config_path="config.yml"):
    """
    Test a webhook by sending a simulated annotation event
    
    Args:
        hook_id (str): Hook ID to test
        annotation_id (str): Annotation ID to use in the test
        base_url (str, optional): Base API URL, defaults to API_BASE_URL from config
        debug_token (str, optional): Debug token to use instead of getting a new one
        config_path (str): Path to configuration file
        
    Returns:
        dict: Response data from the API
    """
    logger.info(f"Testing hook {hook_id} with annotation {annotation_id}")
    
    # Step 1: Load configuration
    config = load_config(config_path)
    
    # Step 2: Get authentication token
    token = debug_token if debug_token else get_auth_token()
    
    if not token:
        logger.error("Failed to get authentication token")
        return None
        
    # If base_url not provided, get it from the login module
    if base_url is None:
        from utils.config import API_BASE_URL
        base_url = API_BASE_URL
        
    # Step 3: Prepare the test request payload
    payload = {
        "payload": {
            "action": "manual",
            "event": "invocation",
            "base_url": "https://test-company-tadeas.rossum.app",
            "rossum_authorization_token": token,
            "annotation": {},
            "document": {},
            "settings": {
                "annotation_id": annotation_id,
                "config": config
            }
        }
    }
    
    # 5. Log details
    logger.info(f"Testing hook ID: {hook_id}")
    logger.info(f"Using annotation ID: {annotation_id}")
    logger.info(f"Config loaded from: {config_path}")
    
    # 6. Send test request
    result = send_test_request(hook_id, token, payload, base_url)
    
    # 7. Display results
    if "response" in result:
        logger.info("\nResponse:")
        logger.info(json.dumps(result["response"], indent=2))
    else:
        logger.info("\nResponse (non-JSON):")
        logger.info(result.get("response_text", "No response text"))
    
    return result

####### CLI ENTRY POINT #######
if __name__ == "__main__":
    import argparse
    from utils.config import API_BASE_URL
    
    parser = argparse.ArgumentParser(description="Test a Rossum serverless function")
    parser.add_argument("hook_id", help="The ID of the hook to test")
    parser.add_argument("--annotation-id", default="7992402", help="The annotation ID to use for testing")
    parser.add_argument("--config", default="config.yml", help="Path to YAML configuration file")
    parser.add_argument("--debug-token", help="Debug token to use instead of getting from client")
    parser.add_argument("--base-url", default=API_BASE_URL, help="Base URL for the API")
    
    args = parser.parse_args()
    
    result = test_hook(
        args.hook_id,
        annotation_id=args.annotation_id,
        base_url=args.base_url,
        debug_token=args.debug_token,
        config_path=args.config
    )
    
    if result.get("status") == "error":
        logger.error(result.get("message"))
        exit(1)  # Only use exit in the CLI entry point, not in the function 