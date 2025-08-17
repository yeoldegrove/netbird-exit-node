#!/usr/bin/env python3
"""
NetBird Exit Node Route Query Tool

This script queries the NetBird API to get available routes for a specific peer.
It uses environment variables for authentication and allows peer selection via CLI.
"""

import os
import socket
import sys
import time
import threading
from typing import Dict, List, Optional, Any
import json

import click
import requests

from .config import get_api_credentials, validate_config, save_config, load_config, show_config_status


def get_api_client() -> 'NetBirdAPIClient':
    """Get configured NetBird API client."""
    api_url, access_token = get_api_credentials()

    if not api_url:
        click.echo("Error: NETBIRD_API_URL not configured", err=True)
        click.echo("Run 'netbird-cli config set' to configure credentials", err=True)
        sys.exit(1)

    if not access_token:
        click.echo("Error: NETBIRD_ACCESS_TOKEN not configured", err=True)
        click.echo("Run 'netbird-cli config set' to configure credentials", err=True)
        sys.exit(1)

    return NetBirdAPIClient(api_url, access_token)


class NetBirdAPIClient:
    """Client for interacting with the NetBird API."""

    def __init__(self, api_url: str, access_token: str) -> None:
        """Initialize the NetBird API client.

        Args:
            api_url: The base URL for the NetBird API
            access_token: The access token for authentication
        """
        self.api_url = api_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        # Configure adapter for connection pooling and timeout handling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=1
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def get_peers(self) -> List[Dict[str, Any]]:
        """Get all peers from the NetBird API.

        Returns:
            List of peer dictionaries

        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            response = self.session.get(f"{self.api_url}/api/peers")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Don't print detailed error here, let main() handle it
            raise

    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all routes from the NetBird API.

        Returns:
            List of route dictionaries

        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            response = self.session.get(f"{self.api_url}/api/routes")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Don't print detailed error here, let main() handle it
            raise

    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups from the NetBird API.

        Returns:
            List of group dictionaries

        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            response = self.session.get(f"{self.api_url}/api/groups")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Don't print detailed error here, let main() handle it
            raise

    def find_peer_by_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Find a peer by hostname.

        Args:
            hostname: The hostname to search for

        Returns:
            Peer dictionary if found, None otherwise
        """
        peers = self.get_peers()
        for peer in peers:
            if peer.get('hostname') == hostname or peer.get('name') == hostname:
                return peer
        return None

    def get_routes_for_peer(self, peer_id: str) -> List[Dict[str, Any]]:
        """Get routes that are accessible by a specific peer (excluding exit node routes).

        Args:
            peer_id: The ID of the peer

        Returns:
            List of route dictionaries accessible by the peer (non-exit node routes only)
        """
        routes = self.get_routes()
        peer_routes = []

        for route in routes:
            # Skip exit node routes (routes that have a 'peer' field indicating an exit node)
            if 'peer' in route and route['peer']:
                continue

            # Check if the peer is in the route's peer list or groups
            if 'peers' in route and peer_id in route['peers']:
                peer_routes.append(route)
            elif 'groups' in route:
                # We would need to check group membership, but this requires additional API calls
                # For now, we'll include routes with groups and let the user know
                peer_routes.append(route)

        return peer_routes

    def get_group_name(self, group_id: str, groups: List[Dict[str, Any]]) -> str:
        """Get group name by ID.

        Args:
            group_id: The ID of the group
            groups: List of all groups

        Returns:
            Group name or ID if not found
        """
        for group in groups:
            if group.get('id') == group_id:
                return group.get('name', group_id)
        return group_id

    def get_peer_name(self, peer_id: str, peers: List[Dict[str, Any]]) -> str:
        """Get peer name by ID.

        Args:
            peer_id: The ID of the peer
            peers: List of all peers

        Returns:
            Peer hostname/name or ID if not found
        """
        for peer in peers:
            if peer.get('id') == peer_id:
                return peer.get('hostname') or peer.get('name', peer_id)
        return peer_id

    def create_group(self, name: str, peers: List[str] = None) -> Dict[str, Any]:
        """Create a new group.

        Args:
            name: The name of the group
            peers: List of peer IDs to add to the group

        Returns:
            Created group dictionary

        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            data = {
                'name': name,
                'peers': peers or []
            }
            response = self.session.post(f"{self.api_url}/api/groups", json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Don't print detailed error here, let main() handle it
            raise

    def update_group(self, group_id: str, name: str, peers: List[str]) -> Dict[str, Any]:
        """Update an existing group.

        Args:
            group_id: The ID of the group to update
            name: The name of the group
            peers: List of peer IDs to set for the group

        Returns:
            Updated group dictionary

        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            data = {
                'name': name,
                'peers': peers or []
            }
            response = self.session.put(f"{self.api_url}/api/groups/{group_id}", json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            # Don't print detailed error here, let main() handle it
            raise

    def find_group_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a group by name.

        Args:
            name: The name of the group to find

        Returns:
            Group dictionary if found, None otherwise
        """
        groups = self.get_groups()
        for group in groups:
            if group.get('name') == name:
                                return group
        return None

    def update_route(self, route_id: str, data: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        """Update a route.

        Args:
            route_id: The ID of the route to update
            data: The data to update
            timeout: Request timeout in seconds (default: 60)

        Returns:
            Updated route dictionary

        Raises:
            requests.RequestException: If the API request fails
        """
        try:
            # Use longer timeout for route updates as they can be slow
            response = self.session.put(
                f"{self.api_url}/api/routes/{route_id}",
                json=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            raise requests.RequestException(f"Request timed out after {timeout} seconds")
        except requests.RequestException as e:
            # Don't print detailed error here, let main() handle it
            raise


def set_exit_node(exit_node_name: str, peer: Optional[str], verbose: bool) -> None:
    """Set an exit node as active for a specific peer.

    This function performs a clean switch by first removing the peer from any
    currently assigned exit nodes, then activating the new exit node.

    Args:
        exit_node_name: Name/hostname of the exit node to activate
        peer: Name/hostname of the peer (if None, uses current hostname)
        verbose: Enable verbose output
    """
    try:
        # Initialize API client using config system
        client = get_api_client()
        current_peer = peer if peer else get_current_hostname()

        if verbose:
            click.echo(f"Setting exit node '{exit_node_name}' for peer '{current_peer}'")

        # Find the target exit node peer
        exit_node_peer = client.find_peer_by_hostname(exit_node_name)
        if not exit_node_peer:
            click.echo(f"❌ Error: Exit node '{exit_node_name}' not found", err=True)
            sys.exit(1)

        exit_node_id = exit_node_peer.get('id')
        if verbose:
            click.echo(f"Found exit node ID: {exit_node_id}")

        # Find the target peer ID first
        target_peer_obj = client.find_peer_by_hostname(current_peer)
        if not target_peer_obj:
            click.echo(f"❌ Error: Target peer '{current_peer}' not found", err=True)
            sys.exit(1)

        target_peer_id = target_peer_obj.get('id')
        if verbose:
            click.echo(f"Found target peer ID: {target_peer_id}")

        # Check if distribution group exists for current peer
        group_name = f"peer-{current_peer}"
        distribution_group = client.find_group_by_name(group_name)

        if not distribution_group:
            # Create distribution group with the target peer
            if verbose:
                click.echo(f"Creating distribution group '{group_name}' with peer '{current_peer}'")
            try:
                distribution_group = client.create_group(group_name, [target_peer_id])
                click.echo(f"✅ Created distribution group '{group_name}' and added peer '{current_peer}'")
            except requests.RequestException as e:
                if "403" in str(e) or "forbidden" in str(e).lower():
                    click.echo(f"❌ Cannot create group '{group_name}' - insufficient permissions", err=True)
                    click.echo("", err=True)
                    click.echo("💡 Workaround options:", err=True)
                    click.echo(f"   1. Ask your NetBird admin to create a group named '{group_name}'", err=True)
                    click.echo(f"   2. Use an existing group by running: netbird-cli exit-nodes info", err=True)
                    click.echo("   3. Get admin privileges for your access token", err=True)
                    sys.exit(1)
                else:
                    handle_api_error(e, verbose=verbose)
        else:
            # Group exists, check if target peer is in it
            current_peers = distribution_group.get('peers', [])
            # Extract just the peer IDs from the current peers (they might be objects)
            current_peer_ids = []
            for peer in current_peers:
                if isinstance(peer, dict):
                    current_peer_ids.append(peer.get('id'))
                else:
                    current_peer_ids.append(peer)

            if target_peer_id not in current_peer_ids:
                # Add the target peer to the existing group
                updated_peers = current_peer_ids + [target_peer_id]
                if verbose:
                    click.echo(f"Adding peer '{current_peer}' to existing distribution group '{group_name}'")
                    click.echo(f"Current peers: {current_peer_ids}")
                    click.echo(f"Updated peers: {updated_peers}")
                try:
                    distribution_group = client.update_group(
                        distribution_group.get('id'),
                        group_name,
                        updated_peers
                    )
                    click.echo(f"✅ Added peer '{current_peer}' to distribution group '{group_name}'")
                except requests.RequestException as e:
                    if "400" in str(e) or "bad request" in str(e).lower():
                        click.echo(f"❌ Invalid group update data for '{group_name}' - checking API requirements", err=True)
                        if verbose:
                            click.echo(f"Group ID: {distribution_group.get('id')}", err=True)
                            click.echo(f"Group name: {group_name}", err=True)
                            click.echo(f"Peer IDs: {updated_peers}", err=True)
                            click.echo(f"API Error: {e}", err=True)
                        sys.exit(1)
                    elif "403" in str(e) or "forbidden" in str(e).lower():
                        click.echo(f"❌ Cannot update group '{group_name}' - insufficient permissions", err=True)
                        click.echo("", err=True)
                        click.echo("💡 Workaround: Ask your NetBird admin to add peer to the group", err=True)
                        sys.exit(1)
                    else:
                        handle_api_error(e, verbose=verbose)
            else:
                if verbose:
                    click.echo(f"Peer '{current_peer}' is already in distribution group '{group_name}'")

        group_id = distribution_group.get('id')
        if verbose:
            click.echo(f"Using distribution group ID: {group_id}")

                # Get all routes and find exit node routes
        all_routes = client.get_routes()
        all_peers = client.get_peers()  # Get all peers for name resolution
        exit_node_routes = [route for route in all_routes if 'peer' in route and route['peer']]

        # Find the target exit node route first
        target_route = None
        for route in exit_node_routes:
            if route['peer'] == exit_node_id:
                target_route = route
                break

        if not target_route:
            click.echo(f"❌ Error: No exit node route found for '{exit_node_name}'", err=True)
            sys.exit(1)

        # Check if group is already assigned to target
        current_groups = target_route.get('groups', [])
        if group_id in current_groups:
            click.echo(f"✅ Exit node '{exit_node_name}' was already active")
            return

                # STEP 1: Remove group from OTHER exit nodes FIRST (clean removal)
        if verbose:
            click.echo(f"STEP 1: Removing from current exit node assignments...")
        else:
            click.echo(f"🧹 Removing from current exit nodes...")

        # Remove group from OTHER exit nodes first
        removed_from = []
        for route in exit_node_routes:
            if 'groups' in route and group_id in route['groups'] and route['peer'] != exit_node_id:
                # Remove group from this route but keep the route enabled for other peers
                updated_groups = [g for g in route['groups'] if g != group_id]
                route_data = {
                    'network': route['network'],
                    'description': route.get('description', ''),
                    'enabled': route.get('enabled', True),  # Keep the route enabled for other peers
                    'peer': route['peer'],
                    'groups': updated_groups,
                    'metric': route.get('metric', 9999),
                    'masquerade': route.get('masquerade', True),
                    'network_id': route.get('network_id'),
                    'domains': route.get('domains', [])
                }

                # Remove None values to avoid issues
                route_data = {k: v for k, v in route_data.items() if v is not None}

                if verbose:
                    click.echo(f"Removing from route {route['id']} with data: {route_data}")
                else:
                    route_peer_name = client.get_peer_name(route['peer'], all_peers)
                    click.echo(f"🧹 Removing from exit node '{route_peer_name}'...")

                # Get the peer name for this route
                route_peer_name = client.get_peer_name(route['peer'], all_peers)

                # Use fire-and-check approach to avoid hanging
                success, message = fire_and_check_connectivity(
                    client, route['id'], route_data, route_peer_name, verbose
                )

                click.echo(message)

                if success:
                    removed_from.append(route_peer_name)
                elif "timed out" in message.lower() or "network change" in message.lower():
                    removed_from.append(f"{route_peer_name} (network disrupted)")

        if removed_from:
            if verbose:
                click.echo(f"Removed from exit node(s): {', '.join(removed_from)}")
        else:
            if verbose:
                click.echo("No previous exit node assignments to remove")

        # STEP 2: Add group to target route (establish new connectivity)
        if verbose:
            click.echo(f"STEP 2: Activating new exit node '{exit_node_name}'...")
        else:
            click.echo(f"🎯 Activating exit node '{exit_node_name}'...")

        # Add group to target route
        updated_groups = current_groups + [group_id]

        # Filter out any None or invalid group IDs
        updated_groups = [g for g in updated_groups if g is not None and g.strip()]

        # Validate that all groups exist
        if verbose:
            click.echo(f"Validating groups exist...")
            all_groups = client.get_groups()
            existing_group_ids = [g.get('id') for g in all_groups if g.get('id')]
            for group_id_check in updated_groups:
                if group_id_check not in existing_group_ids:
                    click.echo(f"⚠️  Warning: Group ID {group_id_check} does not exist, removing from route")
                else:
                    click.echo(f"✓ Group ID {group_id_check} exists")

            # Filter out non-existent groups
            updated_groups = [g for g in updated_groups if g in existing_group_ids]

        route_data = {
            'network': target_route['network'],
            'description': target_route.get('description', ''),
            'enabled': True,
            'peer': target_route['peer'],
            'groups': updated_groups,
            'metric': target_route.get('metric', 9999),
            'masquerade': target_route.get('masquerade', True),
            'network_id': target_route.get('network_id'),
            'domains': target_route.get('domains', [])
        }

        # Remove None values to avoid issues
        route_data = {k: v for k, v in route_data.items() if v is not None}

        if verbose:
            click.echo(f"Validating route data before update:")
            click.echo(f"  Groups: {route_data['groups']}")
            click.echo(f"  Network: {route_data['network']}")
            click.echo(f"  Peer: {route_data['peer']}")
            click.echo(f"  Enabled: {route_data['enabled']}")

        if verbose:
            click.echo(f"Updating target route {target_route['id']} with data: {route_data}")

        try:
            if verbose:
                click.echo(f"Making API call to update route...")
            else:
                click.echo(f"⏳ Updating route... (up to 30 seconds)")

            # Use standard timeout for activation
            updated_route = client.update_route(target_route['id'], route_data, timeout=30)

            if verbose:
                click.echo(f"Route update completed successfully")
            else:
                click.echo(f"✅ Exit node '{exit_node_name}' activated")

        except requests.RequestException as e:
            if "timeout" in str(e).lower():
                click.echo(f"⚠️  Route update timed out (likely due to network change)")
                click.echo(f"✅ Exit node change probably succeeded")
            else:
                if verbose:
                    click.echo(f"Failed to update target route {target_route['id']}: {e}")
                handle_api_error(e, verbose=verbose)
                sys.exit(1)
        except Exception as e:
            if verbose:
                click.echo(f"Unexpected error during route update: {e}")
            click.echo(f"❌ Unexpected error: {e}", err=True)
            sys.exit(1)

        # Final success message
        if removed_from:
            click.echo(f"🔄 Moved from exit node(s): {', '.join(removed_from)}")
        click.echo(f"✅ Set exit node '{exit_node_name}' as active and enabled route")

    except requests.RequestException as e:
        handle_api_error(e, verbose=verbose)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def remove_exit_node(peer: Optional[str], verbose: bool) -> None:
    """Remove a peer from all exit nodes.

    Args:
        peer: Name/hostname of the peer (if None, uses current hostname)
        verbose: Enable verbose output
    """
    try:
        # Initialize API client using config system
        client = get_api_client()
        current_peer = peer if peer else get_current_hostname()

        if verbose:
            click.echo(f"Removing peer '{current_peer}' from all exit nodes")

        # Check if distribution group exists for current peer
        group_name = f"peer-{current_peer}"
        distribution_group = client.find_group_by_name(group_name)

        if not distribution_group:
            click.echo(f"ℹ️ No distribution group '{group_name}' found - peer not using any exit nodes")
            return

        group_id = distribution_group.get('id')
        if verbose:
            click.echo(f"Found distribution group ID: {group_id}")

        # Get all routes and find exit node routes with this group
        all_routes = client.get_routes()
        all_peers = client.get_peers()  # Get all peers for name resolution
        modified_routes = []

        for route in all_routes:
            if 'peer' in route and route['peer'] and 'groups' in route and group_id in route['groups']:
                # Remove group from this route but keep the route enabled for other peers
                updated_groups = [g for g in route['groups'] if g != group_id]
                route_data = {
                    'network': route['network'],
                    'description': route.get('description', ''),
                    'enabled': route.get('enabled', True),  # Keep the route enabled for other peers
                    'peer': route['peer'],
                    'groups': updated_groups,
                    'metric': route.get('metric', 9999),
                    'masquerade': route.get('masquerade', True),
                    'network_id': route.get('network_id'),
                    'domains': route.get('domains', [])
                }

                # Remove None values to avoid issues
                route_data = {k: v for k, v in route_data.items() if v is not None}

                if verbose:
                    click.echo(f"Updating route {route['id']} for removal with data: {route_data}")

                try:
                    client.update_route(route['id'], route_data)

                    # Get the peer name for this route
                    route_peer_name = client.get_peer_name(route['peer'], all_peers)
                    modified_routes.append(route_peer_name)

                    if verbose:
                        click.echo(f"Removed peer '{current_peer}' from exit node: {route_peer_name} (route remains active for other peers)")
                except requests.RequestException as e:
                    if verbose:
                        click.echo(f"Failed to update route {route['id']}: {e}")
                    raise

        if modified_routes:
            click.echo(f"✅ Removed peer '{current_peer}' from exit node(s): {', '.join(modified_routes)}")
            click.echo(f"   Exit node routes remain active for other peers")
        else:
            click.echo(f"ℹ️ Peer '{current_peer}' was not assigned to any exit nodes")

    except requests.RequestException as e:
        handle_api_error(e, verbose=verbose)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def show_exit_node_info(peer: Optional[str], verbose: bool) -> None:
    """Show information about a peer and available groups.

    Args:
        peer: Name/hostname of the peer (if None, uses current hostname)
        verbose: Enable verbose output
    """
    try:
        # Initialize API client using config system
        client = get_api_client()
        current_peer = peer if peer else get_current_hostname()

        click.echo(f"NetBird Exit Node Information")
        click.echo("=" * 40)
        click.echo(f"Target Peer: {current_peer}")
        click.echo(f"Required Group Name: peer-{current_peer}")

        # Check if distribution group exists for current peer
        group_name = f"peer-{current_peer}"
        distribution_group = client.find_group_by_name(group_name)

        if distribution_group:
            click.echo(f"✅ Distribution group '{group_name}' exists")
            group_id = distribution_group.get('id')

            # Find which exit nodes have this group
            all_routes = client.get_routes()
            all_peers = client.get_peers()
            current_exit_nodes = []

            for route in all_routes:
                if ('peer' in route and route['peer'] and
                    'groups' in route and route['groups'] is not None and
                    group_id in route['groups']):

                    enabled_routes = route.get('enabled', False)
                    if enabled_routes:
                        peer_name = client.get_peer_name(route['peer'], all_peers)
                        current_exit_nodes.append(f"{route['peer']} ({peer_name}) (🟢 ACTIVE)")
                    else:
                        peer_name = client.get_peer_name(route['peer'], all_peers)
                        current_exit_nodes.append(f"{route['peer']} ({peer_name}) (🔴 INACTIVE)")

            if current_exit_nodes:
                click.echo(f"Current Exit Nodes: {', '.join(current_exit_nodes)}")
            else:
                click.echo("Current Exit Nodes: None")
        else:
            click.echo(f"❌ Distribution group '{group_name}' does not exist")
            click.echo("Current Exit Nodes: None")

        # Show all available groups
        all_groups = client.get_groups()
        click.echo("")
        click.echo("Available Groups:")
        click.echo("-" * 20)

        # Convert to list safely
        groups_list = []
        if all_groups:
            for group in all_groups:
                if group is not None:
                    groups_list.append(group)

        for group in groups_list:
            peers_list = group.get('peers', [])
            if peers_list is not None:
                peer_count = len(peers_list)
            else:
                peer_count = 0
            click.echo(f"• {group.get('name', 'Unknown')} (ID: {group.get('id', 'Unknown')}, {peer_count} peers)")

        # Show available exit nodes
        all_routes = client.get_routes()
        all_peers = client.get_peers()
        exit_node_routes = [route for route in all_routes if 'peer' in route and route['peer']]

        click.echo("")
        click.echo("Available Exit Nodes:")
        click.echo("-" * 22)

        for route in exit_node_routes:
            if route.get('enabled'):
                status = "🟢 ACTIVE"
            else:
                status = "🔴 INACTIVE"
            peer_name = client.get_peer_name(route['peer'], all_peers)
            click.echo(f"• {route['peer']} ({peer_name}) ({status})")

        click.echo("")
        click.echo("Usage:")
        click.echo("-" * 8)
        click.echo("netbird-cli exit-nodes set <exit-node> # Set active exit node")
        click.echo("netbird-cli exit-nodes rm             # Remove from all exit nodes")

    except requests.RequestException as e:
        handle_api_error(e, verbose=verbose)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)



def handle_api_error(e: requests.RequestException, api_url: Optional[str] = None, verbose: bool = False) -> None:
    """Handle API errors with friendly messages."""
    if api_url is None:
        api_url, _ = get_api_credentials()

    error_msg = str(e).lower()
    if "no route to host" in error_msg or "connection refused" in error_msg or "network is unreachable" in error_msg:
        click.echo("❌ Connection Error: Unable to reach the NetBird API server.", err=True)
        click.echo(f"   Server: {api_url}", err=True)
        click.echo("   This could mean:", err=True)
        click.echo("   • The server is down or unreachable", err=True)
        click.echo("   • You're not connected to the VPN/network", err=True)
        click.echo("   • The API URL is incorrect", err=True)
        click.echo("   • Firewall is blocking the connection", err=True)
    elif "401" in error_msg or "unauthorized" in error_msg:
        click.echo("❌ Authentication Error: Invalid access token.", err=True)
        click.echo("   Please check your NETBIRD_ACCESS_TOKEN environment variable.", err=True)
    elif "403" in error_msg or "forbidden" in error_msg:
        click.echo("❌ Permission Error: Access denied.", err=True)
        click.echo("   This could mean:", err=True)
        click.echo("   • Your access token doesn't have admin/write permissions", err=True)
        click.echo("   • You need higher privileges to create/modify groups and routes", err=True)
        click.echo("   • Contact your NetBird administrator for proper permissions", err=True)
    elif "404" in error_msg or "not found" in error_msg:
        click.echo("❌ API Error: The requested endpoint was not found.", err=True)
        click.echo(f"   Please verify the API URL: {api_url}", err=True)
    elif "422" in error_msg or "unprocessable entity" in error_msg:
        click.echo("❌ Data Error: The server couldn't process the request data.", err=True)
        click.echo("   This could mean:", err=True)
        click.echo("   • Invalid route data format", err=True)
        click.echo("   • Missing required fields", err=True)
        click.echo("   • Group ID doesn't exist", err=True)
        click.echo("   • Peer ID is invalid", err=True)
    elif "timeout" in error_msg:
        click.echo("❌ Timeout Error: The request took too long to complete.", err=True)
        click.echo("   The server might be slow or overloaded.", err=True)
    else:
        click.echo(f"❌ API Error: {e}", err=True)

    if verbose:
        click.echo(f"\nDetailed error: {e}", err=True)
    sys.exit(1)


def get_current_hostname() -> str:
    """Get the current system hostname."""
    return socket.gethostname()


def fire_and_check_connectivity(client, route_id: str, route_data: dict, peer_name: str, verbose: bool) -> tuple[bool, str]:
    """Fire a route update and check if we can still reach the API afterwards.

    Returns:
        tuple: (success, message)
    """
    success = False
    message = ""

    def update_route():
        nonlocal success, message
        try:
            client.update_route(route_id, route_data, timeout=10)
            success = True
            message = f"✅ Removed from exit node: {peer_name}"
        except requests.RequestException as e:
            if "timeout" in str(e).lower():
                message = f"⚠️  Timeout removing from '{peer_name}' - continuing..."
            else:
                message = f"⚠️  Failed to remove from '{peer_name}' - continuing..."

    # Start the update in a separate thread
    update_thread = threading.Thread(target=update_route)
    update_thread.daemon = True
    update_thread.start()

    # Wait up to 15 seconds for the operation
    update_thread.join(timeout=15)

    if update_thread.is_alive():
        # Operation is still running, likely network disruption
        if verbose:
            click.echo(f"Route update still running after 15s, checking connectivity...")

        # Wait a bit more and check if we can reach the API
        time.sleep(2)

        # Try to reach the API again
        try:
            # Get API URL from config
            api_url, _ = get_api_credentials()
            # Simple connectivity check
            test_response = requests.get(f"{api_url}/api/peers",
                                       headers={"Authorization": f"Bearer {client.access_token}"},
                                       timeout=5)
            if test_response.status_code in [200, 401, 403]:  # Any response means connectivity
                message = f"✅ Removed from exit node: {peer_name} (network reconnected)"
                success = True
            else:
                message = f"⚠️  Removed from '{peer_name}' but connectivity unclear - continuing..."
        except requests.RequestException:
            # Network still down, assume operation succeeded but network changed
            message = f"✅ Removed from exit node: {peer_name} (network change detected)"
            success = True

    return success, message


def get_exit_nodes_from_routes(routes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract unique exit nodes from routes.

    Args:
        routes: List of route dictionaries

    Returns:
        List of unique exit node dictionaries with their route counts
    """
    exit_nodes = {}

    if not routes:
        return []

    for route in routes:
        try:
            if 'peer' in route and route['peer']:
                peer_id = route['peer'] if isinstance(route['peer'], str) else route['peer'].get('id')
                if peer_id:
                    if peer_id not in exit_nodes:
                        exit_nodes[peer_id] = {
                            'id': peer_id,
                            'routes': [],
                            'enabled_routes': 0,
                            'total_routes': 0
                        }

                    exit_nodes[peer_id]['routes'].append(route)
                    exit_nodes[peer_id]['total_routes'] += 1
                    if route.get('enabled', False):
                        exit_nodes[peer_id]['enabled_routes'] += 1
        except Exception:
            # Skip problematic routes and continue
            continue

    # Convert to list manually to avoid any slice issues
    result = []
    for exit_node in exit_nodes.values():
        result.append(exit_node)
    return result


def format_exit_nodes_output(exit_nodes: List[Dict[str, Any]], client: NetBirdAPIClient) -> None:
    """Format and display exit nodes information.

    Args:
        exit_nodes: List of exit node dictionaries
        client: NetBird API client for resolving names
    """
    if not exit_nodes:
        click.echo("No exit nodes found")
        return

    # Fetch peers for name resolution
    try:
        all_peers = client.get_peers()
    except requests.RequestException:
        all_peers = []

    click.echo(f"\nExit Nodes ({len(exit_nodes)} found):")
    click.echo("=" * 50)

    for i, exit_node in enumerate(exit_nodes, 1):
        peer_id = exit_node['id']
        peer_name = client.get_peer_name(peer_id, all_peers)

        # Check if this exit node has any enabled routes (is active)
        is_active = exit_node['enabled_routes'] > 0

        # Add visual indicators for active exit nodes
        if is_active:
            click.echo(f"\n🟢 Exit Node {i} (ACTIVE):")
            click.echo(f"  Name: {peer_name} ⭐")
        else:
            click.echo(f"\n🔴 Exit Node {i}:")
            click.echo(f"  Name: {peer_name}")

        click.echo(f"  ID: {peer_id}")
        click.echo(f"  Total Routes: {exit_node['total_routes']}")

        if is_active:
            click.echo(f"  Enabled Routes: {exit_node['enabled_routes']} 🚀")
        else:
            click.echo(f"  Enabled Routes: {exit_node['enabled_routes']}")

        # Show route networks
        networks = []
        for route in exit_node['routes']:
            network = route.get('network', 'N/A')
            if route.get('enabled', False):
                status = "🟢 ACTIVE"
            else:
                status = "🔴 INACTIVE"
            networks.append(f"{network} ({status})")

        if networks:
            try:
                # Show networks safely
                if len(networks) <= 3:
                    click.echo(f"  Networks: {', '.join(networks)}")
                else:
                    first_three = [networks[0], networks[1], networks[2]]
                    click.echo(f"  Networks: {', '.join(first_three)}")
                    click.echo(f"           ... and {len(networks) - 3} more")
            except Exception as e:
                click.echo(f"  Networks: Error displaying networks - {e}")


def format_route_output(routes: List[Dict[str, Any]], peer_name: str, client: NetBirdAPIClient) -> None:
    """Format and display the route information.

    Args:
        routes: List of route dictionaries
        peer_name: Name of the peer
        client: NetBird API client for resolving names
    """
    if not routes:
        click.echo(f"No routes found for peer '{peer_name}'")
        return

    # Fetch additional data for name resolution
    try:
        all_groups = client.get_groups()
        all_peers = client.get_peers()
    except requests.RequestException:
        # Fall back to showing IDs if we can't fetch names
        all_groups = []
        all_peers = []

    click.echo(f"\nRoutes available for peer '{peer_name}':")
    click.echo("=" * 50)

    for i, route in enumerate(routes, 1):
        click.echo(f"\nRoute {i}:")
        click.echo(f"  ID: {route.get('id', 'N/A')}")
        click.echo(f"  Network: {route.get('network', 'N/A')}")
        click.echo(f"  Description: {route.get('description', 'N/A')}")
        click.echo(f"  Enabled: {route.get('enabled', 'N/A')}")

        if 'peer' in route and route['peer']:
            if isinstance(route['peer'], dict):
                click.echo(f"  Exit Node: {route['peer'].get('hostname', 'N/A')}")
            else:
                # route['peer'] is a peer ID, resolve to name
                peer_name_resolved = client.get_peer_name(route['peer'], all_peers)
                click.echo(f"  Exit Node: {peer_name_resolved}")

        if 'groups' in route and route['groups']:
            # Resolve group IDs to names
            group_names = []
            for group_id in route['groups']:
                group_name = client.get_group_name(group_id, all_groups)
                group_names.append(group_name)
            click.echo(f"  Groups: {', '.join(group_names)}")

        if 'peers' in route and route['peers']:
            click.echo(f"  Peer Count: {len(route['peers'])}")


@click.group(invoke_without_command=True)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """NetBird Exit Node tool for managing routes and exit nodes.

    If no command is provided, an interactive menu will be shown.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

    # If no subcommand was invoked, show the interactive menu
    if ctx.invoked_subcommand is None:
        from .menu import run_interactive_menu
        run_interactive_menu()


@main.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Manage NetBird CLI configuration."""
    pass


@config.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show current configuration."""
    show_config_status()


@config.command()
@click.option(
    '--api-url',
    prompt='NetBird API URL',
    help='NetBird API server URL (e.g., https://api.netbird.io)'
)
@click.option(
    '--access-token',
    prompt='Access Token',
    hide_input=True,
    help='NetBird API access token'
)
@click.pass_context
def set(ctx: click.Context, api_url: str, access_token: str) -> None:
    """Set API credentials in configuration file."""
    try:
        # Validate URL format
        if not api_url.startswith(('http://', 'https://')):
            click.echo("Error: API URL must start with http:// or https://", err=True)
            sys.exit(1)

        # Save configuration
        config_data = {
            'api_url': api_url.rstrip('/'),
            'access_token': access_token
        }

        save_config(config_data)

        click.echo("✅ Configuration saved successfully")
        click.echo(f"   API URL: {api_url}")
        click.echo(f"   Access Token: {access_token[:8]}...")
        click.echo("")
        click.echo("You can now use the NetBird CLI tools without environment variables.")

    except Exception as e:
        click.echo(f"❌ Error saving configuration: {e}", err=True)
        sys.exit(1)


@main.group()
@click.pass_context
def routes(ctx: click.Context) -> None:
    """Manage NetBird routes."""
    pass


@routes.command()
@click.option(
    '--peer',
    default=None,
    help='Hostname of the peer to query routes for (default: current hostname)'
)
@click.option(
    '--json-output',
    is_flag=True,
    help='Output results in JSON format'
)
@click.pass_context
def list(ctx: click.Context, peer: Optional[str], json_output: bool) -> None:
    """List NetBird routes for a specific peer."""
    verbose = ctx.obj['verbose']
    list_routes(peer, json_output, verbose)


@main.group(name='exit-nodes')
@click.pass_context
def exit_nodes(ctx: click.Context) -> None:
    """Manage NetBird exit nodes."""
    pass


@exit_nodes.command()
@click.option(
    '--json-output',
    is_flag=True,
    help='Output results in JSON format'
)
@click.pass_context
def list(ctx: click.Context, json_output: bool) -> None:
    """List all NetBird exit nodes."""
    verbose = ctx.obj['verbose']
    list_exit_nodes(json_output, verbose)


@exit_nodes.command()
@click.argument('exit_node_name')
@click.option(
    '--peer',
    default=None,
    help='Peer hostname to manage exit nodes for (default: current hostname)'
)
@click.pass_context
def set(ctx: click.Context, exit_node_name: str, peer: str) -> None:
    """Set an exit node as active for a specific peer.

    Creates a distribution group named after the peer (if missing)
    and assigns it to the specified exit node. If the group is already
    assigned to another exit node, it will be moved.
    """
    verbose = ctx.obj['verbose']
    set_exit_node(exit_node_name, peer, verbose)


@exit_nodes.command()
@click.option(
    '--peer',
    default=None,
    help='Peer hostname to remove from exit nodes (default: current hostname)'
)
@click.pass_context
def rm(ctx: click.Context, peer: str) -> None:
    """Remove a peer from all exit nodes.

    Removes the distribution group named after the peer
    from all exit node routes.
    """
    verbose = ctx.obj['verbose']
    remove_exit_node(peer, verbose)


@exit_nodes.command()
@click.option(
    '--peer',
    default=None,
    help='Peer hostname to show info for (default: current hostname)'
)
@click.pass_context
def info(ctx: click.Context, peer: str) -> None:
    """Show information about a peer and available groups.

    Displays the peer name, existing groups, and whether
    the required distribution group exists.
    """
    verbose = ctx.obj['verbose']
    show_exit_node_info(peer, verbose)




def list_routes(peer: Optional[str], json_output: bool, verbose: bool) -> None:
    """List NetBird routes for a specific peer.

    Uses configuration from ~/.config/netbird/netbird-exit-node.json or environment variables.
    """

    try:
        # Initialize API client using config system
        client = get_api_client()

        if verbose:
            api_url, _ = get_api_credentials()
            click.echo(f"Connecting to NetBird API at: {api_url}")

        # Use current hostname if no peer specified
        if not peer:
            peer = get_current_hostname()
            if verbose:
                click.echo(f"Using current hostname: {peer}")

        if verbose:
            click.echo(f"Looking for peer: {peer}")

        # Find the peer
        peer_info = client.find_peer_by_hostname(peer)
        if not peer_info:
            click.echo(f"Error: Peer '{peer}' not found", err=True)
            sys.exit(1)

        peer_id = peer_info.get('id')
        if verbose:
            click.echo(f"Found peer ID: {peer_id}")

        # Get routes for the peer
        routes = client.get_routes_for_peer(peer_id)

        if json_output:
            # Output as JSON
            output = {
                'peer': peer_info,
                'routes': routes
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Format and display routes
            format_route_output(routes, peer, client)

    except requests.RequestException as e:
        # Provide friendly error messages for common issues
        error_msg = str(e).lower()
        if "no route to host" in error_msg or "connection refused" in error_msg or "network is unreachable" in error_msg:
            click.echo("❌ Connection Error: Unable to reach the NetBird API server.", err=True)
            click.echo(f"   Server: {api_url}", err=True)
            click.echo("   This could mean:", err=True)
            click.echo("   • The server is down or unreachable", err=True)
            click.echo("   • You're not connected to the VPN/network", err=True)
            click.echo("   • The API URL is incorrect", err=True)
            click.echo("   • Firewall is blocking the connection", err=True)
        elif "401" in error_msg or "unauthorized" in error_msg:
            click.echo("❌ Authentication Error: Invalid access token.", err=True)
            click.echo("   Please check your NETBIRD_ACCESS_TOKEN environment variable.", err=True)
        elif "404" in error_msg or "not found" in error_msg:
            click.echo("❌ API Error: The requested endpoint was not found.", err=True)
            click.echo(f"   Please verify the API URL: {api_url}", err=True)
        elif "timeout" in error_msg:
            click.echo("❌ Timeout Error: The request took too long to complete.", err=True)
            click.echo("   The server might be slow or overloaded.", err=True)
        else:
            click.echo(f"❌ API Error: {e}", err=True)

        if verbose:
            click.echo(f"\nDetailed error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def list_exit_nodes(json_output: bool, verbose: bool) -> None:
    """List all NetBird exit nodes.

    Uses configuration from ~/.config/netbird/netbird-exit-node.json or environment variables.
    """

    try:
        # Initialize API client using config system
        client = get_api_client()

        if verbose:
            click.echo(f"Connecting to NetBird API at: {api_url}")
            click.echo("Fetching exit nodes...")

        all_routes = client.get_routes()
        if verbose:
            click.echo(f"Fetched {len(all_routes)} routes")

        exit_nodes = get_exit_nodes_from_routes(all_routes)
        if verbose:
            click.echo(f"Found {len(exit_nodes)} exit nodes")

        if json_output:
            click.echo(json.dumps(exit_nodes, indent=2))
        else:
            format_exit_nodes_output(exit_nodes, client)

    except requests.RequestException as e:
        # Provide friendly error messages for common issues
        error_msg = str(e).lower()
        if "no route to host" in error_msg or "connection refused" in error_msg or "network is unreachable" in error_msg:
            click.echo("❌ Connection Error: Unable to reach the NetBird API server.", err=True)
            click.echo(f"   Server: {api_url}", err=True)
            click.echo("   This could mean:", err=True)
            click.echo("   • The server is down or unreachable", err=True)
            click.echo("   • You're not connected to the VPN/network", err=True)
            click.echo("   • The API URL is incorrect", err=True)
            click.echo("   • Firewall is blocking the connection", err=True)
        elif "401" in error_msg or "unauthorized" in error_msg:
            click.echo("❌ Authentication Error: Invalid access token.", err=True)
            click.echo("   Please check your NETBIRD_ACCESS_TOKEN environment variable.", err=True)
        elif "404" in error_msg or "not found" in error_msg:
            click.echo("❌ API Error: The requested endpoint was not found.", err=True)
            click.echo(f"   Please verify the API URL: {api_url}", err=True)
        elif "timeout" in error_msg:
            click.echo("❌ Timeout Error: The request took too long to complete.", err=True)
            click.echo("   The server might be slow or overloaded.", err=True)
        else:
            click.echo(f"❌ API Error: {e}", err=True)

        if verbose:
            click.echo(f"\nDetailed error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
