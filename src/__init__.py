"""
Rossum API Integration Package.
Provides utilities for working with the Rossum API, including:
- Authentication and client creation
- Deploying serverless functions
- Triggering serverless functions
- Utilities for configuration and helper functions
"""

# Import main components for easy access
from utils import (
    API_TOKEN,
    API_BASE_URL,
    create_api_client,
)

from deploy import (
    deploy_function_with_sdk,
    list_queues_with_sdk,
)

from trigger import (
    trigger_hook_with_sdk,
)

__all__ = [
    # Configuration
    'API_TOKEN',
    'API_BASE_URL',
    
    # Client creation
    'create_api_client',
    
    # Deployment
    'deploy_function_with_sdk',
    'list_queues_with_sdk',
    
    # Triggering
    'trigger_hook_with_sdk',
]
