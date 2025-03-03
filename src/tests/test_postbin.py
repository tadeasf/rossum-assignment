#!/usr/bin/env python3
"""
Script to post a JSON payload to a PostBin URL.
"""

import argparse
import json
import requests
import sys
import os


def post_to_postbin(json_payload, postbin_url, debug=False):
    """
    Post JSON payload to a PostBin URL.
    
    Args:
        json_payload (dict): The JSON payload to post
        postbin_url (str): The PostBin URL to post to
        debug (bool): Whether to show debug information
    
    Returns:
        dict: The response data
    """
    try:
        print(f"Posting to URL: {postbin_url}")
        
        # Check if the URL is valid and accessible
        try:
            check_response = requests.get(postbin_url, timeout=5)
            if check_response.status_code == 404:
                print(f"WARNING: The URL {postbin_url} returned a 404 error.")
                print("This bin may have expired or is invalid.")
                print("\nTry these alternative services:")
                print("1. RequestBin: https://requestbin.com/")
                print("2. Webhook.site: https://webhook.site/")
                print("3. Beeceptor: https://beeceptor.com/")
                print("4. Pipedream: https://pipedream.com/requestbin")
        except Exception as e:
            print(f"WARNING: Could not check if the URL is valid: {str(e)}")
            print("Make sure the URL is accessible from your current network.")
        
        # Handle the payload format
        # Sometimes payload comes directly, sometimes in a 'payload' key
        actual_payload = json_payload
        if 'payload' in json_payload:
            print("Found nested 'payload' key, using the nested content")
            actual_payload = json_payload['payload']
        
        # Display payload summary
        print(f"Payload structure: {list(actual_payload.keys())}")
        
        if 'annotationId' in actual_payload:
            print(f"Payload contains 'annotationId': {actual_payload.get('annotationId')}")
        
        if 'content' in actual_payload:
            content_len = len(actual_payload['content'])
            print(f"Payload contains base64 content of length: {content_len}")
        
        if debug:
            print("\nFull payload:")
            print(json.dumps(actual_payload, indent=2))
        
        # Send the request
        print("\nSending POST request...")
        response = requests.post(
            postbin_url,
            json=actual_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Print status code
        print(f"Response status code: {response.status_code}")
        
        # Try to parse response as JSON
        try:
            response_json = response.json()
            print("\nResponse JSON:")
            print(json.dumps(response_json, indent=2))
            return response_json
        except json.JSONDecodeError:
            # Not JSON, print as text
            print("\nResponse (not JSON):")
            print(response.text[:1000])  # Limit to first 1000 chars if very long
            return {"status": "success", "raw_response": response.text[:500]}
            
    except Exception as e:
        print(f"Error posting to PostBin: {str(e)}")
        return {"status": "error", "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description='Post JSON payload to a PostBin URL')
    parser.add_argument('--payload', required=True, help='JSON payload string or file path (if starts with @)')
    parser.add_argument('--url', required=True, help='PostBin URL to post to')
    parser.add_argument('--debug', action='store_true', help='Show debug information including full payload')
    
    args = parser.parse_args()
    
    # Load the payload
    try:
        if args.payload.startswith('@'):
            # It's a file path
            file_path = args.payload[1:]
            print(f"Reading payload from file: {file_path}")
            
            if not os.path.exists(file_path):
                print(f"ERROR: File not found: {file_path}")
                print(f"Current directory: {os.getcwd()}")
                print(f"Files in current directory: {os.listdir('.')}")
                sys.exit(1)
                
            with open(file_path, 'r') as f:
                payload_str = f.read()
                try:
                    json_payload = json.loads(payload_str)
                except json.JSONDecodeError as e:
                    print(f"ERROR: Invalid JSON in file {file_path}: {str(e)}")
                    print(f"File contents (first 200 chars): {payload_str[:200]}")
                    sys.exit(1)
        else:
            # It's a JSON string
            try:
                json_payload = json.loads(args.payload)
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSON string: {str(e)}")
                print(f"Payload string (first 200 chars): {args.payload[:200]}")
                sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Failed to process payload: {str(e)}")
        sys.exit(1)
    
    # Post to PostBin
    post_to_postbin(json_payload, args.url, args.debug)


if __name__ == "__main__":
    main()
