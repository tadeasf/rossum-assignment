#!/usr/bin/env python3
"""
Deploy a serverless function to Rossum using the Rossum Python SDK.
This script creates or updates a hook in Rossum with the function code.
"""

import argparse
import logging
import os
import sys
import json
from typing import Dict, Any, Optional, List

# Add the src directory to the path to make imports work properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
 

def get_hook_code(hook_obj):
    """
    Safely extract code from a hook object regardless of its structure.
    
    Args:
        hook_obj: The hook object to extract code from
        
    Returns:
        str: The extracted code or a message indicating code was not found
    """
    # Try different possible structures
    if hasattr(hook_obj, 'function') and hasattr(hook_obj.function, 'code'):
        return hook_obj.function.code
    elif hasattr(hook_obj, 'code'):
        return hook_obj.code
    elif hasattr(hook_obj, 'function') and isinstance(hook_obj.function, dict) and 'code' in hook_obj.function:
        return hook_obj.function['code']
    elif isinstance(hook_obj, dict) and 'function' in hook_obj and 'code' in hook_obj['function']:
        return hook_obj['function']['code']
    elif isinstance(hook_obj, dict) and 'code' in hook_obj:
        return hook_obj['code']
    
    # If we get here, we couldn't find the code
    return None

def read_function_file(file_path: str) -> str:
    """Read the function code from a file."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading function file: {e}")
        return None

def should_update_function(existing_hook, new_function_code: str, client) -> bool:
    """
    Determine if a function needs to be updated by checking if the code has changed.
    
    Args:
        existing_hook: The existing hook object
        new_function_code: The new function code to compare with
        client: Authenticated ElisAPIClientSync client
        
    Returns:
        bool: True if the function needs updating, False otherwise
    """
    try:
        # Get hook ID safely, handling different object types
        hook_id = None
        if hasattr(existing_hook, 'id'):
            hook_id = existing_hook.id
        elif isinstance(existing_hook, dict) and 'id' in existing_hook:
            hook_id = existing_hook['id']
        
        if not hook_id:
            logger.warning("Could not determine hook ID, assuming update is needed")
            return True
            
        # Get detailed hook information including function code if possible
        try:
            hook_detail = client.retrieve_hook(hook_id)
        except Exception as e:
            logger.warning(f"Could not retrieve hook details: {str(e)}. Assuming update is needed.")
            return True
            
        existing_code = get_hook_code(hook_detail)
        
        # If we can't retrieve the code, assume we need to update
        if not existing_code:
            logger.warning("Could not retrieve existing function code for comparison, assuming update is needed")
            return True
            
        # Compare code content (ignoring whitespace differences)
        existing_code_normalized = "\n".join(line.strip() for line in existing_code.splitlines() if line.strip())
        new_code_normalized = "\n".join(line.strip() for line in new_function_code.splitlines() if line.strip())
        
        if existing_code_normalized != new_code_normalized:
            logger.info("Function code has changed - update is needed")
            return True
        else:
            logger.info("Function code is identical - no update needed")
            return False
            
    except Exception as e:
        logger.warning(f"Error comparing function code: {str(e)}. Assuming update is needed.")
        return True

def deploy_function_with_sdk(
    client,
    function_code: str,
    function_name: str,
    queue_id: Optional[int] = None,
    token_owner: Optional[str] = None,
    events: List[str] = None,
    force_update: bool = False,
) -> Dict[str, Any]:
    """
    Deploy a serverless function to Rossum using the SDK.
    
    Args:
        client: Authenticated ElisAPIClientSync client
        function_code: The Python code for the function
        function_name: Name of the function
        queue_id: Optional queue ID to associate with the function
        token_owner: Optional token owner URL (format: https://example.rossum.app/api/v1/users/123)
        events: List of event types to trigger the function (default: ["invocation.manual"])
        force_update: Force update even if no code changes are detected
        
    Returns:
        The created or updated hook data
    """
    try:
        # Validate that the function includes the required handler function
        if "rossum_hook_request_handler" not in function_code:
            logger.error("Error: Function code must include a 'rossum_hook_request_handler' function")
            return None
        
        # Use default events if none provided
        if not events:
            events = ["invocation.manual"]
        
        # Prepare hook data with function code correctly included
        hook_data = {
            "name": function_name,
            "type": "function",
            "active": True,
            "config": {
                "url": "https://dummy-url.com",  # Required field but not used for serverless functions
                "runtime": "python3.12",  # Required runtime field
                "code": function_code,  # Code should be in config.code for hooks of type "function"
                "timeout_s": 30,  # Add a reasonable timeout
                "retry_count": 3  # Add retry count for reliability
            },
            "events": events,  # Use provided events
            "queues": []  # Required field
        }
        
        # Add token_owner if provided
        if token_owner:
            hook_data["token_owner"] = token_owner
            logger.info(f"Setting token_owner to: {token_owner}")
        
        # Note: The Rossum API doesn't return the function code in API responses
        # for security and performance reasons. The code is still saved on the server.
        # You won't see the code in the API response or when retrieving the hook later,
        # but it will execute properly when triggered.
        
        # Basic logging of function details
        logger.info(f"Function code length: {len(function_code)} characters")
        logger.info(f"Function code preview (first 100 chars): {function_code[:100]}...")
        
        # Add queue if specified
        if queue_id:
            hook_data["queues"] = [queue_id]
        
        # Check if hook already exists
        existing_hook = None
        logger.info("Checking for existing hooks...")
        for hook in client.list_all_hooks(name=function_name):
            existing_hook = hook
            break
        
        if existing_hook:
            # Update existing hook
            logger.info(f"Updating existing hook '{function_name}' with ID {existing_hook.id}")
            
            # Check if the function code has actually changed
            update_needed = should_update_function(existing_hook, function_code, client)
            
            if not update_needed and not force_update:
                logger.info("No code changes detected and force_update not specified. Skipping update.")
                return existing_hook
                
            # IMPORTANT: For updating hooks, we need to explicitly include the function code
            # Otherwise, the API might ignore the code update
            updated_hook_data = {
                "config": {
                    "code": function_code,  # Code should be in config.code for hooks of type "function"
                    "runtime": "python3.12",
                    "timeout_s": 30,
                    "retry_count": 3
                }
            }
            
            # Keep important fields like events if they exist in the current hook configuration
            try:
                # Get full details of the existing hook
                existing_hook_detail = client.retrieve_hook(existing_hook.id)
                
                # Preserve existing events if they're set and not being explicitly updated
                if hasattr(existing_hook_detail, 'events') and existing_hook_detail.events and not events:
                    updated_hook_data["events"] = existing_hook_detail.events
                    logger.info(f"Preserving existing events: {updated_hook_data['events']}")
                else:
                    updated_hook_data["events"] = events
                    logger.info(f"Setting events to: {events}")
                
                # Include other required fields
                updated_hook_data["type"] = "function"
                updated_hook_data["active"] = True
                updated_hook_data["name"] = function_name
                
                # Add config if it doesn't exist in the update data
                if "config" not in updated_hook_data:
                    updated_hook_data["config"] = {
                        "url": "https://dummy-url.com",
                        "runtime": "python3.12"
                    }
                
                # Add token_owner if provided
                if token_owner:
                    updated_hook_data["token_owner"] = token_owner
                
                # Add queue if specified
                if queue_id:
                    updated_hook_data["queues"] = [queue_id]
                elif hasattr(existing_hook_detail, 'queues') and existing_hook_detail.queues:
                    updated_hook_data["queues"] = existing_hook_detail.queues
                else:
                    updated_hook_data["queues"] = []
                    
            except Exception as e:
                logger.warning(f"Could not retrieve full details of existing hook: {str(e)}")
                # Fall back to using the original hook_data
                updated_hook_data = hook_data
            
            # Log the update operation
            logger.info("Updating hook with the following data:")
            logger.info(f"- Name: {updated_hook_data.get('name', 'unchanged')}")
            logger.info(f"- Function code length: {len(function_code)} characters")
            logger.info(f"- Events: {updated_hook_data.get('events', 'unchanged')}")
            logger.info(f"- Queues: {updated_hook_data.get('queues', 'unchanged')}")
            
            # Debug the actual data we're sending
            logger.debug(f"Update data structure: {json.dumps(updated_hook_data, indent=2, default=str)}")
            
            try:
                # Get hook ID safely
                hook_id = None
                if hasattr(existing_hook, 'id'):
                    hook_id = existing_hook.id
                elif isinstance(existing_hook, dict) and 'id' in existing_hook:
                    hook_id = existing_hook['id']
                
                if not hook_id:
                    logger.error("Cannot update hook: missing ID")
                    raise ValueError("Hook ID not found in existing hook object")
                
                # Attempt the update
                result = client.update_part_hook(hook_id, data=updated_hook_data)
                operation = "updated"
                logger.debug(f"Update result: {result}")
            except Exception as e:
                logger.error(f"Failed to update hook: {str(e)}")
                # Try to fetch the hook to see if it actually changed despite the error
                try:
                    updated_hook = client.retrieve_hook(existing_hook.id)
                    logger.debug(f"Hook after update attempt: {updated_hook}")
                except Exception as inner_e:
                    logger.error(f"Failed to retrieve hook after update attempt: {str(inner_e)}")
                raise e
        else:
            # Create new hook
            logger.info(f"Creating new hook '{function_name}'")
            result = client.create_new_hook(data=hook_data)
            operation = "created"
        
        logger.info(f"Successfully {operation} hook '{function_name}' with ID {result.id}")
        
        # Double-check by retrieving the hook directly
        try:
            retrieved_hook = client.retrieve_hook(result.id)
            logger.info(f"Retrieved hook after {operation}: ID {retrieved_hook.id}")
            logger.info("The function code was deployed successfully")
            logger.info(f"To test the function, use the trigger tool: rye run trigger {result.id}")
                
        except Exception as e:
            logger.warning(f"Could not retrieve hook for verification: {str(e)}")
        
        # Return result as dictionary
        hook_dict = {
            "id": result.id,
            "name": result.name,
            "url": result.url,
            "active": result.active,
            "type": result.type,
        }
        
        # Print success message
        print(f"\nFunction '{function_name}' deployed successfully with ID {result.id}")
        print(f"URL: {result.url}")
        print("\nNOTE: The function code won't be visible in the API responses,")
        print("but it has been saved on the server and will execute when triggered.")
        print(f"\nTo test the function, run: rye run trigger {result.id}")
        print("\n")
        
        return hook_dict
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        # Print more detailed information for debugging
        import traceback
        traceback.print_exc()
        return None

def parse_arguments():
    """Parse command line arguments for function deployment.
    
    Returns:
        argparse.Namespace: The parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Deploy a serverless function to Rossum")
    
    # Function source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--file", "-f", dest="file_path", help="Path to the function file")
    source_group.add_argument("--code", "-c", dest="function_code", help="Function code as a string")
    
    # Function configuration
    parser.add_argument("--function-name", "-n", required=True, help="Name of the function")
    parser.add_argument("--queue-id", "-q", type=int, help="Queue ID to associate with the function")
    parser.add_argument("--token-owner", "-o", help="User ID or URL to set as token owner")
    parser.add_argument("--events", "-e", help="Comma-separated list of event types (e.g., 'invocation.manual,annotation.status.changed')")
    parser.add_argument("--force-update", "-u", action="store_true", help="Force update even if no code changes are detected")
    
    # Extra options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
        
    return args

def main():
    """Main function for deploying a serverless function to Rossum."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Get API client
        logger.info("Getting authenticated API client")
        from utils.login import get_client
        client = get_client()
        
        if not client:
            logger.error("Failed to get API client")
            return None
            
        # Load function code
        if args.file_path:
            logger.info(f"Loading function code from file: {args.file_path}")
            function_code = read_function_file(args.file_path)
        elif args.function_code:
            logger.info("Using provided function code")
            function_code = args.function_code
        else:
            logger.error("No function code provided. Use --file or --code")
            return None
            
        # Convert token owner to URL format if needed
        token_owner_url = None
        if args.token_owner:
            token_owner_url = args.token_owner
            if not token_owner_url.startswith('http'):
                token_owner_url = f"{client.url.rstrip('/v1')}/users/{token_owner_url}"
                
        # Convert events to list
        events = []
        if args.events:
            events = [e.strip() for e in args.events.split(",")]
            
        # Deploy the function
        result = deploy_function_with_sdk(
            client,
            function_code,
            args.function_name,
            args.queue_id,
            token_owner_url,
            events,
            args.force_update,
        )        
        return result
    except Exception as e:
        logger.error(f"Error deploying function: {str(e)}")
        return None

if __name__ == "__main__":
    try:
        result = main()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")