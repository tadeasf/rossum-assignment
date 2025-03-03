#!/usr/bin/env python3
"""
Utility script to get hook details from Rossum API.
This can be used to extract information about users associated with hooks
and analyze/fix event subscription issues.
"""

import argparse
import json
import logging
import os
import sys
import requests
from typing import Dict, Any, Optional, List

# Add the src directory to the path to make imports work properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from utils.config import API_TOKEN, API_BASE_URL
from utils.login import get_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Standard event types that can be used with hooks
STANDARD_EVENT_TYPES = [
    "annotation.created", 
    "annotation.updated",
    "document.created", 
    "document.updated",
    "export.created", 
    "export.updated",
    "invocation", 
    "invocation.manual",
    "queue.created", 
    "queue.updated",
    "user.created", 
    "user.updated",
    "workspace.created", 
    "workspace.updated"
]

def get_hook_details(hook_id: str, token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed information about a hook from the Rossum API.
    
    Args:
        hook_id: ID of the hook to retrieve
        token: API token for authentication (will use API_TOKEN if not provided)
        base_url: API base URL (will use API_BASE_URL if not provided)
        
    Returns:
        Dictionary containing hook details
    """
    # Use provided values or defaults
    token = token or API_TOKEN
    base_url = base_url or API_BASE_URL
    
    if not token:
        logger.error("API token is required. Provide it as an argument or set it in the .env file.")
        sys.exit(1)
    
    logger.info(f"Retrieving details for hook {hook_id}")
    
    try:
        # First, try to get the hook using the SDK client
        client = get_client()
        
        if hasattr(client, "retrieve_hook") and callable(client.retrieve_hook):
            logger.info("Using SDK client to retrieve hook")
            hook = client.retrieve_hook(hook_id)
            
            # Convert to dictionary if it's an object
            if not isinstance(hook, dict):
                # Try to convert to dict using __dict__ attribute
                if hasattr(hook, '__dict__'):
                    hook_dict = {k: v for k, v in hook.__dict__.items() if not k.startswith('_')}
                else:
                    # Fallback method
                    hook_dict = {}
                    for attr in dir(hook):
                        if not attr.startswith('_') and not callable(getattr(hook, attr)):
                            hook_dict[attr] = getattr(hook, attr)
            else:
                hook_dict = hook
            
            logger.info(f"Successfully retrieved hook {hook_id}")
            return hook_dict
        
        # Fallback to direct API request
        logger.info("Falling back to direct API request")
        
        # Format the API URL
        api_url = base_url.rstrip("/")
        if not api_url.endswith("/v1"):
            if api_url.endswith("/api"):
                api_url = f"{api_url}/v1"
            elif not api_url.endswith("/api/v1"):
                api_url = f"{api_url}/api/v1"
        
        hook_url = f"{api_url}/hooks/{hook_id}"
        
        # Create headers for the request
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
        
        # Make the request
        response = requests.get(hook_url, headers=headers)
        response.raise_for_status()
        
        hook_data = response.json()
        logger.info(f"Successfully retrieved hook {hook_id}")
        
        return hook_data
        
    except Exception as e:
        logger.error(f"Error retrieving hook: {str(e)}")
        return {"error": str(e)}

def update_hook_events(hook_id: str, events: List[str], token: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the events a hook is subscribed to.
    
    Args:
        hook_id: ID of the hook to update
        events: List of events to subscribe the hook to
        token: API token for authentication
        base_url: API base URL
        
    Returns:
        Updated hook data
    """
    token = token or API_TOKEN
    base_url = base_url or API_BASE_URL
    
    if not token:
        logger.error("API token is required")
        sys.exit(1)
    
    logger.info(f"Updating events for hook {hook_id} to: {events}")
    
    try:
        # Get the current hook data first
        hook_data = get_hook_details(hook_id, token, base_url)
        if "error" in hook_data:
            return hook_data
        
        # Try to use the SDK client first
        client = get_client()
        
        # Prepare the update data
        update_data = {"events": events}
        
        if hasattr(client, "update_part_hook") and callable(client.update_part_hook):
            logger.info("Using SDK client to update hook")
            result = client.update_part_hook(hook_id, data=update_data)
            
            # Convert result to dict if needed
            if not isinstance(result, dict):
                if hasattr(result, '__dict__'):
                    result_dict = {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
                else:
                    result_dict = {}
                    for attr in dir(result):
                        if not attr.startswith('_') and not callable(getattr(result, attr)):
                            result_dict[attr] = getattr(result, attr)
            else:
                result_dict = result
                
            logger.info("Successfully updated hook events")
            return result_dict
        
        # Fallback to direct API request
        logger.info("Falling back to direct API request for update")
        
        # Format the API URL
        api_url = base_url.rstrip("/")
        if not api_url.endswith("/v1"):
            if api_url.endswith("/api"):
                api_url = f"{api_url}/v1"
            elif not api_url.endswith("/api/v1"):
                api_url = f"{api_url}/api/v1"
        
        hook_url = f"{api_url}/hooks/{hook_id}"
        
        # Create headers for the request
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
        
        # Make the PATCH request
        response = requests.patch(hook_url, headers=headers, json=update_data)
        response.raise_for_status()
        
        updated_hook = response.json()
        logger.info("Successfully updated hook events via API")
        
        return updated_hook
        
    except Exception as e:
        logger.error(f"Error updating hook events: {str(e)}")
        return {"error": str(e)}

def extract_user_id_from_hook(hook_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract user ID from hook data, specifically looking for token_owner or related fields.
    
    Args:
        hook_data: Dictionary containing hook details
        
    Returns:
        User ID or None if not found
    """
    token_owner = hook_data.get("token_owner")
    if token_owner:
        # If token_owner is a URL, extract the user ID
        if isinstance(token_owner, str) and '/users/' in token_owner:
            user_id = token_owner.split('/users/')[-1].rstrip('/')
            return user_id
    
    # Check if there's a creator field
    creator = hook_data.get("creator")
    if creator:
        # If creator is a URL, extract the user ID
        if isinstance(creator, str) and '/users/' in creator:
            user_id = creator.split('/users/')[-1].rstrip('/')
            return user_id
    
    # If we reach here, we couldn't find a user ID
    return None

def check_event_support(hook_data: Dict[str, Any], event: str) -> bool:
    """
    Check if a hook supports a specific event.
    
    Args:
        hook_data: Dictionary containing hook details
        event: Event to check for
        
    Returns:
        True if the event is supported, False otherwise
    """
    if "events" not in hook_data:
        return False
        
    events = hook_data["events"]
    
    # Check if the exact event is in the list
    if event in events:
        return True
        
    # Check for parent events (e.g., "invocation" for "invocation.manual")
    if '.' in event:
        parent_event = event.split('.')[0]
        if parent_event in events:
            return True
            
    return False

def validate_event_format(event: str) -> bool:
    """
    Validate that an event string is properly formatted.
    
    Args:
        event: Event string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not event:
        return False
        
    # Check if it's a standard event
    if event in STANDARD_EVENT_TYPES:
        return True
        
    # Basic format check: should be in the format "category.action"
    parts = event.split('.')
    if len(parts) != 2:
        logger.warning(f"Event '{event}' doesn't follow the standard format 'category.action'")
        return False
        
    return True

def suggest_event_fixes(hook_data: Dict[str, Any], desired_event: str) -> List[str]:
    """
    Suggest fixes for event subscription issues.
    
    Args:
        hook_data: Dictionary containing hook details
        desired_event: Event that we want to use
        
    Returns:
        List of suggested fixes
    """
    if "events" not in hook_data:
        return ["Add events list to hook configuration"]
        
    events = hook_data["events"]
    
    suggestions = []
    
    # If the hook doesn't have any events, suggest adding the desired event
    if not events:
        suggestions.append(f"Add '{desired_event}' to the events list")
        return suggestions
        
    # If the desired event is already in the list, no need to fix
    if desired_event in events:
        suggestions.append("No fixes needed, event is already supported")
        return suggestions
        
    # Check if there's a parent/child relationship
    if '.' in desired_event:
        parent_event = desired_event.split('.')[0]
        if parent_event in events:
            suggestions.append(f"Use parent event '{parent_event}' instead of '{desired_event}'")
            suggestions.append(f"Or add '{desired_event}' to the events list")
        else:
            suggestions.append(f"Add '{desired_event}' to the events list")
    else:
        # If we're trying to use a parent event like "invocation" but hook has "invocation.manual"
        child_events = [e for e in events if e.startswith(f"{desired_event}.")]
        if child_events:
            suggestions.append(f"Use specific event(s) {', '.join(child_events)} instead of generic '{desired_event}'")
            suggestions.append(f"Or add '{desired_event}' to the events list")
        else:
            suggestions.append(f"Add '{desired_event}' to the events list")
    
    return suggestions

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Get hook details from Rossum API")
    parser.add_argument("hook_id", help="ID of the hook to retrieve")
    parser.add_argument("--token", help="Rossum API token")
    parser.add_argument("--base-url", help="Rossum API base URL", default=API_BASE_URL)
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format (default: text)")
    parser.add_argument("--user-only", action="store_true", help="Only output the user ID")
    parser.add_argument("--check-event", help="Check if hook supports a specific event")
    parser.add_argument("--update-events", nargs='+', help="Update hook events (provide space-separated list)")
    parser.add_argument("--add-event", help="Add a single event to the hook's events list")
    parser.add_argument("--fix-invocation", action="store_true", help="Fix invocation event issues (add both invocation and invocation.manual)")
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Get hook details
    hook_data = get_hook_details(args.hook_id, args.token, args.base_url)
    
    # Check for errors
    if "error" in hook_data:
        print(f"Error: {hook_data['error']}")
        sys.exit(1)
    
    # Handle event checking request
    if args.check_event:
        is_supported = check_event_support(hook_data, args.check_event)
        if is_supported:
            print(f"✅ Event '{args.check_event}' is supported by this hook")
        else:
            print(f"❌ Event '{args.check_event}' is NOT supported by this hook")
            suggestions = suggest_event_fixes(hook_data, args.check_event)
            print("\nSuggested fixes:")
            for suggestion in suggestions:
                print(f"  • {suggestion}")
        return
    
    # Handle fix-invocation request
    if args.fix_invocation:
        current_events = hook_data.get("events", [])
        new_events = list(current_events)  # Make a copy
        
        # Add invocation events if not present
        if "invocation" not in new_events:
            new_events.append("invocation")
        if "invocation.manual" not in new_events:
            new_events.append("invocation.manual")
        
        # Update the hook if changes were made
        if set(new_events) != set(current_events):
            print(f"Updating hook events from {current_events} to {new_events}")
            updated_hook = update_hook_events(args.hook_id, new_events, args.token, args.base_url)
            
            if "error" in updated_hook:
                print(f"Error updating events: {updated_hook['error']}")
                sys.exit(1)
                
            print("✅ Successfully updated hook to support both 'invocation' and 'invocation.manual' events")
            hook_data = updated_hook  # Use updated data for the rest of the output
        else:
            print("✅ Hook already supports both 'invocation' and 'invocation.manual' events")
    
    # Handle update-events request
    elif args.update_events:
        new_events = args.update_events
        
        # Validate event formats
        for event in new_events:
            if not validate_event_format(event):
                print(f"Warning: '{event}' may not be a valid event format")
        
        print(f"Updating hook events to: {new_events}")
        updated_hook = update_hook_events(args.hook_id, new_events, args.token, args.base_url)
        
        if "error" in updated_hook:
            print(f"Error updating events: {updated_hook['error']}")
            sys.exit(1)
            
        print("✅ Successfully updated hook events")
        hook_data = updated_hook  # Use updated data for the rest of the output
    
    # Handle add-event request
    elif args.add_event:
        new_event = args.add_event
        
        # Validate event format
        if not validate_event_format(new_event):
            print(f"Warning: '{new_event}' may not be a valid event format")
        
        current_events = hook_data.get("events", [])
        
        if new_event in current_events:
            print(f"Event '{new_event}' is already in the hook's events list")
        else:
            new_events = list(current_events) + [new_event]
            print(f"Adding event '{new_event}' to hook")
            updated_hook = update_hook_events(args.hook_id, new_events, args.token, args.base_url)
            
            if "error" in updated_hook:
                print(f"Error updating events: {updated_hook['error']}")
                sys.exit(1)
                
            print(f"✅ Successfully added '{new_event}' to hook events")
            hook_data = updated_hook  # Use updated data for the rest of the output
    
    # Extract user ID if needed
    user_id = extract_user_id_from_hook(hook_data)
    
    # If only user ID was requested, output that
    if args.user_only:
        if user_id:
            print(user_id)
        else:
            print("No user ID found")
        return
    
    # Otherwise, output full details
    if args.format == "json":
        # Pretty print the JSON
        print(json.dumps(hook_data, indent=2))
    else:
        # Text format
        print(f"\nHook Details (ID: {args.hook_id}):")
        print("=" * 50)
        
        # Print key information
        if "name" in hook_data:
            print(f"Name: {hook_data['name']}")
        
        if "type" in hook_data:
            print(f"Type: {hook_data['type']}")
        
        if "active" in hook_data:
            print(f"Active: {hook_data['active']}")
        
        # Print events information (highlighted)
        if "events" in hook_data:
            events = hook_data["events"]
            print(f"\n📋 Events: {', '.join(events)}")
            
            # Check for common invocation events
            if "invocation.manual" in events:
                print("  ✅ Supports manual invocation ('invocation.manual')")
            elif "invocation" in events:
                print("  ✅ Supports generic invocation ('invocation')")
                print("  ⚠️ Does NOT explicitly support 'invocation.manual'")
                print("     Try using just 'invocation' as the event type when triggering")
            else:
                print("  ❌ Does NOT support any invocation events")
                print("     Add 'invocation' or 'invocation.manual' to enable triggering")
        
        if "token_owner" in hook_data:
            print(f"\nToken Owner: {hook_data['token_owner']}")
            
            if user_id:
                print(f"User ID: {user_id}")
                print(f"For token_owner setting: {hook_data['token_owner']}")
        
        if "url" in hook_data:
            print(f"\nURL: {hook_data['url']}")
        
        if "id" in hook_data:
            print(f"ID: {hook_data['id']}")
        
        # Print any other interesting fields
        interesting_fields = ["creator", "config", "queues"]
        for field in interesting_fields:
            if field in hook_data:
                if isinstance(hook_data[field], (dict, list)):
                    print(f"\n{field.capitalize()}:")
                    print(json.dumps(hook_data[field], indent=2))
                else:
                    print(f"{field.capitalize()}: {hook_data[field]}")
        
        # Provide a recommendation for deploy_with_sdk.py
        if user_id:
            base_url = args.base_url.rstrip("/").replace("/api/v1", "")
            print("\nRecommended token_owner setting for deploy_with_sdk.py:")
            print(f"token_owner: {base_url}/api/v1/users/{user_id}")
        else:
            print("\nCould not determine user ID for token_owner setting")
            
        # Provide help for the invocation issue
        print("\n📝 Troubleshooting Invocation:")
        print("If you're having trouble with 'invocation.manual not in the hook.event list':")
        print("  1. Run this command to fix it automatically:")
        print(f"     rye run python src/utils/get_hook.py {args.hook_id} --fix-invocation")
        print("  2. Or manually update the events:")
        print(f"     rye run python src/utils/get_hook.py {args.hook_id} --update-events invocation invocation.manual")

if __name__ == "__main__":
    main()
