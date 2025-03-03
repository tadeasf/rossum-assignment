"""
Trigger functions for Rossum API integration.
Provides utilities for triggering serverless functions in Rossum.
"""

from .trigger_with_sdk import (
    trigger_hook_with_sdk,
)

__all__ = [
    'trigger_hook_with_sdk',
]
