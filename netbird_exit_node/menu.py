#!/usr/bin/env python3
"""
NetBird Exit Node Interactive Menu

This module provides an ncurses-based interactive menu for managing
NetBird exit nodes and routes.
"""

import curses
import os
import sys
from typing import List, Optional, Tuple, Dict, Any

from .main import (
    NetBirdAPIClient,
    get_current_hostname,
    format_route_output,
    get_exit_nodes_from_routes,
    format_exit_nodes_output,
    handle_api_error
)


class NetBirdMenu:
    """Interactive ncurses menu for NetBird management."""

    def __init__(self):
        self.current_selection = 0
        self.current_peer = get_current_hostname()
        self.client = None
        self.status_message = ""
        self.error_message = ""

    def initialize_client(self) -> bool:
        """Initialize the NetBird API client."""
        try:
            from .config import get_api_credentials, validate_config

            if not validate_config():
                self.error_message = "Error: NetBird configuration not found. Run 'netbird-cli config set' first."
                return False

            api_url, access_token = get_api_credentials()
            self.client = NetBirdAPIClient(api_url, access_token)
            return True
        except Exception as e:
            self.error_message = f"Failed to initialize API client: {e}"
            return False

    def draw_header(self, stdscr, width: int):
        """Draw the menu header."""
        stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
        title = "NetBird Exit Node Manager"
        stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
        stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)
        stdscr.addstr(3, 2, f"Current Peer: {self.current_peer}", curses.A_DIM)

        # Show current exit node status
        current_exit_node = self.get_current_exit_node()
        if current_exit_node:
            stdscr.addstr(4, 2, f"Current Exit Node: {current_exit_node}", curses.A_DIM)
        else:
            stdscr.addstr(4, 2, f"Current Exit Node: None", curses.A_DIM)

        stdscr.addstr(5, 0, "-" * width)

    def draw_menu_options(self, stdscr, start_y: int, width: int) -> int:
        """Draw the main menu options."""
        menu_options = [
            "1. Set Exit Node",
            "2. Remove from Exit Nodes",
            "3. Change Target Peer",
            "4. Quit"
        ]

        current_y = start_y
        stdscr.addstr(current_y, 2, "Main Menu:", curses.A_BOLD)
        current_y += 2

        for i, option in enumerate(menu_options):
            attr = curses.A_REVERSE if i == self.current_selection else curses.A_NORMAL
            stdscr.addstr(current_y + i, 4, option, attr)

        return current_y + len(menu_options) + 1

    def draw_status(self, stdscr, start_y: int, width: int):
        """Draw status and error messages."""
        if self.status_message:
            stdscr.addstr(start_y, 2, "Status:", curses.A_BOLD)
            stdscr.addstr(start_y + 1, 4, self.status_message[:width-6], curses.A_DIM)
            start_y += 3

        if self.error_message:
            stdscr.addstr(start_y, 2, "Error:", curses.A_BOLD | curses.color_pair(1))
            # Wrap long error messages
            error_lines = [self.error_message[i:i+width-6] for i in range(0, len(self.error_message), width-6)]
            for i, line in enumerate(error_lines[:3]):  # Max 3 lines
                stdscr.addstr(start_y + 1 + i, 4, line, curses.color_pair(1))

    def draw_footer(self, stdscr, height: int, width: int):
        """Draw the footer with navigation help."""
        footer_y = height - 2
        stdscr.addstr(footer_y, 0, "-" * width)
        footer_text = "Navigation: ↑/↓ or j/k to move, Enter to select, q to quit"
        stdscr.addstr(footer_y + 1, 2, footer_text[:width-4], curses.A_DIM)

    def get_input_string(self, stdscr, prompt: str, y: int, x: int) -> Optional[str]:
        """Get string input from user."""
        stdscr.addstr(y, x, prompt)
        stdscr.refresh()

        curses.echo()
        curses.curs_set(1)

        try:
            input_str = stdscr.getstr(y, x + len(prompt)).decode('utf-8')
            return input_str.strip() if input_str.strip() else None
        except KeyboardInterrupt:
            return None
        finally:
            curses.noecho()
            curses.curs_set(0)

    def show_selection_menu(self, stdscr, title: str, options: List[str]) -> Optional[int]:
        """Show a selection menu and return the selected index."""
        if not options:
            return None

        height, width = stdscr.getmaxyx()
        selection = 0

        while True:
            stdscr.clear()

            # Draw header
            stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)

            # Draw options
            start_y = 4
            for i, option in enumerate(options):
                attr = curses.A_REVERSE if i == selection else curses.A_NORMAL
                display_text = f"{i+1}. {option}"
                if start_y + i < height - 3:
                    stdscr.addstr(start_y + i, 4, display_text[:width-8], attr)

            # Draw footer
            footer_y = height - 2
            stdscr.addstr(footer_y, 0, "-" * width)
            footer_text = "↑/↓ to navigate, Enter to select, q to cancel"
            stdscr.addstr(footer_y + 1, 2, footer_text[:width-4], curses.A_DIM)

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()

            if key in [ord('q'), ord('Q'), 27]:  # q or ESC
                return None
            elif key in [curses.KEY_UP, ord('k')]:
                selection = (selection - 1) % len(options)
            elif key in [curses.KEY_DOWN, ord('j')]:
                selection = (selection + 1) % len(options)
            elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
                return selection

    def list_routes_screen(self, stdscr):
        """Show routes list screen."""
        if not self.client:
            self.error_message = "API client not initialized"
            return

        try:
            # Get peer selection
            peers = self.client.get_peers()
            peer_names = [peer.get('hostname', peer.get('name', 'Unknown')) for peer in peers]
            peer_names.insert(0, f"{self.current_peer} (current)")

            selected_idx = self.show_selection_menu(stdscr, "Select Peer for Routes", peer_names)
            if selected_idx is None:
                return

            if selected_idx == 0:
                target_peer = self.current_peer
            else:
                target_peer = peer_names[selected_idx].split(' (')[0]

            # Get routes
            routes = self.client.get_routes_for_peer(target_peer)
            all_peers = self.client.get_peers()

            # Display routes
            height, width = stdscr.getmaxyx()
            stdscr.clear()

            title = f"Routes for peer '{target_peer}'"
            stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)

            if routes:
                current_y = 4
                for i, route in enumerate(routes[:height-8]):  # Leave space for footer
                    route_text = format_route_output([route], all_peers, self.client)
                    lines = route_text.split('\n')
                    for line in lines:
                        if current_y < height - 4:
                            stdscr.addstr(current_y, 2, line[:width-4])
                            current_y += 1
                    current_y += 1
            else:
                stdscr.addstr(4, 2, f"No routes found for peer '{target_peer}'")

            # Footer
            footer_y = height - 2
            stdscr.addstr(footer_y, 0, "-" * width)
            stdscr.addstr(footer_y + 1, 2, "Press any key to return to main menu", curses.A_DIM)

            stdscr.refresh()
            stdscr.getch()

        except Exception as e:
            self.error_message = f"Error listing routes: {e}"

    def list_exit_nodes_screen(self, stdscr):
        """Show exit nodes list screen."""
        if not self.client:
            self.error_message = "API client not initialized"
            return

        try:
            routes = self.client.get_routes()
            exit_nodes = get_exit_nodes_from_routes(routes)
            all_peers = self.client.get_peers()

            # Display exit nodes
            height, width = stdscr.getmaxyx()
            stdscr.clear()

            title = "Available Exit Nodes"
            stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)

            if exit_nodes:
                current_y = 4
                exit_nodes_text = format_exit_nodes_output(exit_nodes, all_peers, self.client)
                lines = exit_nodes_text.split('\n')
                for line in lines:
                    if current_y < height - 4:
                        stdscr.addstr(current_y, 2, line[:width-4])
                        current_y += 1
            else:
                stdscr.addstr(4, 2, "No exit nodes found")

            # Footer
            footer_y = height - 2
            stdscr.addstr(footer_y, 0, "-" * width)
            stdscr.addstr(footer_y + 1, 2, "Press any key to return to main menu", curses.A_DIM)

            stdscr.refresh()
            stdscr.getch()

        except Exception as e:
            self.error_message = f"Error listing exit nodes: {e}"

    def set_exit_node_screen(self, stdscr):
        """Show set exit node screen."""
        if not self.client:
            self.error_message = "API client not initialized"
            return

        try:
            # Get available exit nodes
            routes = self.client.get_routes()
            exit_nodes = get_exit_nodes_from_routes(routes)
            all_peers = self.client.get_peers()

            if not exit_nodes:
                self.error_message = "No exit nodes available"
                return

            # Find current peer's distribution group to determine active exit node
            group_name = f"peer-{self.current_peer}"
            distribution_group = self.client.find_group_by_name(group_name)
            current_exit_node_id = None

            if distribution_group:
                group_id = distribution_group.get('id')
                # Find which exit node currently has this group
                for route in routes:
                    if ('peer' in route and route['peer'] and
                        'groups' in route and route['groups'] is not None and
                        group_id in route['groups'] and
                        route.get('enabled', False)):
                        current_exit_node_id = route['peer']
                        break

            # Create exit node selection list
            exit_node_names = []
            for exit_node in exit_nodes:
                peer_name = self.client.get_peer_name(exit_node['id'], all_peers)

                # Determine status
                if exit_node['id'] == current_exit_node_id:
                    status = "🎯 CURRENT"
                elif exit_node.get('enabled_routes', 0) > 0:
                    status = "ACTIVE"
                else:
                    status = "INACTIVE"

                exit_node_names.append(f"{peer_name} ({status})")

            # Select exit node
            title = f"Select Exit Node for '{self.current_peer}'"
            selected_exit_idx = self.show_selection_menu(stdscr, title, exit_node_names)
            if selected_exit_idx is None:
                return

            selected_exit_node = exit_nodes[selected_exit_idx]
            exit_node_name = self.client.get_peer_name(selected_exit_node['id'], all_peers)

            # Perform the operation directly on current peer
            from .main import set_exit_node

            height, width = stdscr.getmaxyx()
            stdscr.clear()

            title = f"Setting Exit Node for '{self.current_peer}'"
            stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)

            stdscr.addstr(4, 2, f"Exit Node: {exit_node_name}")
            stdscr.addstr(5, 2, f"Target Peer: {self.current_peer}")
            stdscr.addstr(6, 2, f"Processing...")
            stdscr.refresh()

            # This is a bit tricky since set_exit_node prints to stdout
            # We'll capture the result differently
            try:
                set_exit_node(exit_node_name, self.current_peer, False)
                stdscr.addstr(7, 2, f"✅ Successfully set {exit_node_name} as exit node for {self.current_peer}")
                self.status_message = f"Successfully set {exit_node_name} as exit node for {self.current_peer}"
            except Exception as e:
                stdscr.addstr(7, 2, f"❌ Failed to set exit node: {e}")
                self.error_message = f"Failed to set exit node: {e}"

            stdscr.addstr(9, 2, "Press any key to return to main menu", curses.A_DIM)
            stdscr.refresh()
            stdscr.getch()

        except Exception as e:
            self.error_message = f"Error in set exit node: {e}"

    def remove_exit_node_screen(self, stdscr):
        """Show remove from exit nodes screen."""
        if not self.client:
            self.error_message = "API client not initialized"
            return

        try:
            # Immediately remove current peer from all exit nodes
            from .main import remove_exit_node

            height, width = stdscr.getmaxyx()
            stdscr.clear()

            title = f"Removing '{self.current_peer}' from Exit Nodes"
            stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)

            stdscr.addstr(4, 2, f"Removing peer '{self.current_peer}' from all exit nodes...")
            stdscr.addstr(5, 2, "Processing...")
            stdscr.refresh()

            try:
                remove_exit_node(self.current_peer, False)
                stdscr.addstr(6, 2, f"✅ Successfully removed '{self.current_peer}' from all exit nodes")
                self.status_message = f"Successfully removed '{self.current_peer}' from all exit nodes"
            except Exception as e:
                stdscr.addstr(6, 2, f"❌ Failed to remove from exit nodes: {e}")
                self.error_message = f"Failed to remove from exit nodes: {e}"

            stdscr.addstr(8, 2, "Press any key to return to main menu", curses.A_DIM)
            stdscr.refresh()
            stdscr.getch()

        except Exception as e:
            self.error_message = f"Error in remove exit node: {e}"

    def show_info_screen(self, stdscr):
        """Show exit node info screen."""
        if not self.client:
            self.error_message = "API client not initialized"
            return

        try:
            # Get peer selection
            peers = self.client.get_peers()
            peer_names = [peer.get('hostname', peer.get('name', 'Unknown')) for peer in peers]
            peer_names.insert(0, f"{self.current_peer} (current)")

            selected_peer_idx = self.show_selection_menu(stdscr, "Select Peer for Info", peer_names)
            if selected_peer_idx is None:
                return

            if selected_peer_idx == 0:
                target_peer = self.current_peer
            else:
                target_peer = peer_names[selected_peer_idx].split(' (')[0]

            # Get info
            from .main import show_exit_node_info

            height, width = stdscr.getmaxyx()
            stdscr.clear()

            title = f"Exit Node Info - {target_peer}"
            stdscr.addstr(0, 0, "=" * width, curses.A_BOLD)
            stdscr.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(2, 0, "=" * width, curses.A_BOLD)

            # This would need to be refactored to return data instead of printing
            # For now, show basic info
            group_name = f"peer-{target_peer}"
            distribution_group = self.client.find_group_by_name(group_name)

            current_y = 4
            stdscr.addstr(current_y, 2, f"Target Peer: {target_peer}")
            current_y += 1
            stdscr.addstr(current_y, 2, f"Required Group Name: {group_name}")
            current_y += 2

            if distribution_group:
                stdscr.addstr(current_y, 2, f"✅ Distribution group '{group_name}' exists", curses.A_BOLD)
            else:
                stdscr.addstr(current_y, 2, f"❌ Distribution group '{group_name}' does not exist", curses.color_pair(1))

            current_y += 2

            # Show available groups
            all_groups = self.client.get_groups()
            stdscr.addstr(current_y, 2, "Available Groups:", curses.A_BOLD)
            current_y += 1

            if all_groups:
                for group in all_groups[:10]:  # Limit to first 10
                    if current_y < height - 4:
                        peers_list = group.get('peers', [])
                        peer_count = len(peers_list) if peers_list else 0
                        group_text = f"• {group.get('name', 'Unknown')} ({peer_count} peers)"
                        stdscr.addstr(current_y, 4, group_text[:width-8])
                        current_y += 1

            # Footer
            footer_y = height - 2
            stdscr.addstr(footer_y, 0, "-" * width)
            stdscr.addstr(footer_y + 1, 2, "Press any key to return to main menu", curses.A_DIM)

            stdscr.refresh()
            stdscr.getch()

        except Exception as e:
            self.error_message = f"Error showing info: {e}"

    def get_current_exit_node(self) -> str:
        """Get the current exit node for the current peer."""
        if not self.client:
            return "Unknown"

        try:
            # Find current peer's distribution group to determine active exit node
            group_name = f"peer-{self.current_peer}"
            distribution_group = self.client.find_group_by_name(group_name)

            if not distribution_group:
                return "None"

            group_id = distribution_group.get('id')
            routes = self.client.get_routes()
            all_peers = self.client.get_peers()

            # Find which exit node currently has this group
            for route in routes:
                if ('peer' in route and route['peer'] and
                    'groups' in route and route['groups'] is not None and
                    group_id in route['groups'] and
                    route.get('enabled', False)):
                    return self.client.get_peer_name(route['peer'], all_peers)

            return "None"
        except Exception:
            return "Unknown"

    def change_peer_screen(self, stdscr):
        """Change the target peer."""
        if not self.client:
            self.error_message = "API client not initialized"
            return

        try:
            peers = self.client.get_peers()
            peer_names = [peer.get('hostname', peer.get('name', 'Unknown')) for peer in peers]

            selected_idx = self.show_selection_menu(stdscr, "Select New Target Peer", peer_names)
            if selected_idx is not None:
                self.current_peer = peer_names[selected_idx]
                self.status_message = f"Changed target peer to: {self.current_peer}"

        except Exception as e:
            self.error_message = f"Error changing peer: {e}"

    def run(self, stdscr):
        """Main menu loop."""
        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

        # Setup
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)

        # Initialize API client
        if not self.initialize_client():
            height, width = stdscr.getmaxyx()
            stdscr.clear()
            stdscr.addstr(height//2, (width - len(self.error_message))//2, self.error_message, curses.color_pair(1))
            stdscr.addstr(height//2 + 2, (width - 30)//2, "Press any key to exit", curses.A_DIM)
            stdscr.refresh()
            stdscr.getch()
            return

        while True:
            height, width = stdscr.getmaxyx()
            stdscr.clear()

            # Draw UI
            self.draw_header(stdscr, width)
            menu_end_y = self.draw_menu_options(stdscr, 6, width)
            self.draw_status(stdscr, menu_end_y + 1, width)
            self.draw_footer(stdscr, height, width)

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()

            # Clear previous messages
            self.status_message = ""
            self.error_message = ""

            if key in [ord('q'), ord('Q'), ord('4')]:
                break
            elif key in [curses.KEY_UP, ord('k')]:
                self.current_selection = (self.current_selection - 1) % 4
            elif key in [curses.KEY_DOWN, ord('j')]:
                self.current_selection = (self.current_selection + 1) % 4
            elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')] or key in [ord('1'), ord('2'), ord('3')]:
                # Handle number key shortcuts
                if key in [ord('1'), ord('2'), ord('3')]:
                    self.current_selection = int(chr(key)) - 1

                # Execute selected action
                if self.current_selection == 0:  # Set Exit Node
                    self.set_exit_node_screen(stdscr)
                elif self.current_selection == 1:  # Remove from Exit Nodes
                    self.remove_exit_node_screen(stdscr)
                elif self.current_selection == 2:  # Change Peer
                    self.change_peer_screen(stdscr)
                elif self.current_selection == 3:  # Quit
                    break


def run_interactive_menu():
    """Run the interactive ncurses menu."""
    try:
        menu = NetBirdMenu()
        curses.wrapper(menu.run)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error running menu: {e}")
        sys.exit(1)
