"""
Configuration utility for loading environment variables
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def get_claude_model():
    """Get Claude model name from environment variable"""
    return os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

def get_anthropic_api_key():
    """Get Anthropic API key from environment variable"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
    return api_key
