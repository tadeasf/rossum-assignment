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

from lib.deploy import (
    deploy_function_with_sdk,
)

from lib.trigger import (
    test_hook,
)

__all__ = [
    # Configuration
    'API_TOKEN',
    'API_BASE_URL',
    
    # Client creation
    'create_api_client',
    
    # Deployment
    'deploy_function_with_sdk',
    
    # Triggering
    'test_hook',
]
