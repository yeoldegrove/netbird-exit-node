#!/usr/bin/env python3
"""
NetBird Exit Node Configuration Management

This module handles loading and saving configuration for the NetBird Exit Node tools.
Configuration is stored in ~/.config/netbird/netbird-exit-node.json
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

import click


def get_config_dir() -> Path:
    """Get the configuration directory."""
    config_dir = Path.home() / ".config" / "netbird"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "netbird-exit-node.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    config_file = get_config_file()

    if not config_file.exists():
        return {}

    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        click.echo(f"Warning: Error reading config file {config_file}: {e}", err=True)
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_file = get_config_file()

    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        click.echo(f"Error: Could not save config file {config_file}: {e}", err=True)
        raise


def get_api_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get API URL and access token from config or environment variables.

    Environment variables take precedence over config file.

    Returns:
        tuple: (api_url, access_token)
    """
    # Check environment variables first
    api_url = os.getenv('NETBIRD_API_URL')
    access_token = os.getenv('NETBIRD_ACCESS_TOKEN')

    if api_url and access_token:
        return api_url, access_token

    # Fall back to config file
    config = load_config()

    if not api_url:
        api_url = config.get('api_url')

    if not access_token:
        access_token = config.get('access_token')

    return api_url, access_token


def validate_config() -> bool:
    """Validate that configuration is complete.

    Returns:
        bool: True if configuration is valid
    """
    api_url, access_token = get_api_credentials()
    return bool(api_url and access_token)


def show_config_status() -> None:
    """Show current configuration status."""
    config = load_config()
    api_url, access_token = get_api_credentials()

    click.echo("NetBird CLI Configuration Status")
    click.echo("=" * 35)
    click.echo("")

    click.echo("Configuration file:")
    click.echo(f"  Location: {get_config_file()}")
    click.echo(f"  Exists: {'Yes' if get_config_file().exists() else 'No'}")
    click.echo("")

    click.echo("API Configuration:")
    if api_url:
        click.echo(f"  API URL: {api_url}")
        source = "environment" if os.getenv('NETBIRD_API_URL') else "config file"
        click.echo(f"           (from {source})")
    else:
        click.echo("  API URL: Not configured")

    if access_token:
        masked_token = access_token[:8] + "..." + access_token[-4:] if len(access_token) > 12 else "***"
        click.echo(f"  Access Token: {masked_token}")
        source = "environment" if os.getenv('NETBIRD_ACCESS_TOKEN') else "config file"
        click.echo(f"                (from {source})")
    else:
        click.echo("  Access Token: Not configured")

    click.echo("")
    if validate_config():
        click.echo("✅ Configuration is complete")
    else:
        click.echo("❌ Configuration is incomplete")
        click.echo("")
        click.echo("To configure, run:")
        click.echo("  netbird-cli config set")
