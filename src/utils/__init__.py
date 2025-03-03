#!/usr/bin/env python3
"""
Utils package for Rossum API integration.
Provides utilities for authentication, configuration, and API interaction.
"""

from .config import (
    API_TOKEN,
    API_BASE_URL,
    EMAIL,
    PASSWORD,
    COMPANY_ID,
    DEFAULT_ANNOTATION_ID,
    DEFAULT_FUNCTION_NAME,
    DEFAULT_FUNCTION_FILE,
    DEFAULT_QUEUE,
    DEFAULT_SCHEMA,
    POSTBIN_URL,
    DEFAULT_TEST_FILE,
    normalize_api_url,
    determine_api_url,
    get_auth_header,
    save_auth_token
)

from .login import (
    create_api_client,
)

__all__ = [
    # Configuration
    'API_BASE_URL',
    'API_TOKEN',
    'EMAIL',
    'PASSWORD',
    'COMPANY_ID',
    'DEFAULT_ANNOTATION_ID',
    'DEFAULT_FUNCTION_NAME',
    'DEFAULT_FUNCTION_FILE',
    'DEFAULT_QUEUE',
    'DEFAULT_SCHEMA',
    'POSTBIN_URL',
    'DEFAULT_TEST_FILE',
    
    # Functions
    'normalize_api_url',
    'determine_api_url',
    'get_auth_header',
    'save_auth_token',
    'create_api_client',
] 