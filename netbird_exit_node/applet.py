#!/usr/bin/env python3
"""
NetBird Exit Node System Tray Applet

This module provides a PyQt6-based system tray applet for managing
NetBird exit nodes and routes from the desktop taskbar.
"""

import sys
import os
import threading
import time
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QComboBox, QProgressBar, QTextEdit, QLineEdit,
    QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont, QAction

from .main import (
    NetBirdAPIClient,
    get_current_hostname,
    get_exit_nodes_from_routes,
    set_exit_node,
    remove_exit_node
)
from .config import get_api_credentials, validate_config


class NetBirdWorker(QThread):
    """Worker thread for NetBird API operations."""

    finished = pyqtSignal(bool, str)  # success, message
    status_updated = pyqtSignal(str, str)  # current_peer, current_exit_node
    exit_nodes_loaded = pyqtSignal(list)  # exit_nodes data

    def __init__(self, operation: str, **kwargs):
        super().__init__()
        self.operation = operation
        self.kwargs = kwargs
        self.client = None

    def run(self):
        """Execute the NetBird operation in a separate thread."""
        try:
            # Initialize API client using config system
            api_url, access_token = get_api_credentials()

            if not api_url or not access_token:
                self.finished.emit(False, "NetBird API credentials not configured")
                return

            self.client = NetBirdAPIClient(api_url, access_token)

            if self.operation == "set_exit_node":
                self._set_exit_node()
            elif self.operation == "remove_exit_node":
                self._remove_exit_node()
            elif self.operation == "get_status":
                self._get_status()
            elif self.operation == "get_exit_nodes":
                self._get_exit_nodes()

        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

    def _set_exit_node(self):
        """Set exit node for peer."""
        try:
            exit_node_name = self.kwargs.get('exit_node_name')
            peer = self.kwargs.get('peer')

            set_exit_node(exit_node_name, peer, False)
            self.finished.emit(True, f"Successfully set {exit_node_name} as exit node")
        except Exception as e:
            self.finished.emit(False, f"Failed to set exit node: {str(e)}")

    def _remove_exit_node(self):
        """Remove peer from all exit nodes."""
        try:
            peer = self.kwargs.get('peer')

            remove_exit_node(peer, False)
            self.finished.emit(True, f"Successfully removed {peer} from all exit nodes")
        except Exception as e:
            self.finished.emit(False, f"Failed to remove from exit nodes: {str(e)}")

    def _get_status(self):
        """Get current status."""
        try:
            current_peer = get_current_hostname()
            current_exit_node = self._get_current_exit_node(current_peer)
            self.status_updated.emit(current_peer, current_exit_node)
            self.finished.emit(True, "Status updated")
        except Exception as e:
            self.finished.emit(False, f"Failed to get status: {str(e)}")

    def _get_exit_nodes(self):
        """Get available exit nodes."""
        try:
            routes = self.client.get_routes()
            exit_nodes = get_exit_nodes_from_routes(routes)
            all_peers = self.client.get_peers()

            exit_node_list = []
            current_peer = get_current_hostname()
            current_exit_node_id = self._get_current_exit_node_id(current_peer)

            for exit_node in exit_nodes:
                peer_name = self.client.get_peer_name(exit_node['id'], all_peers)

                if exit_node['id'] == current_exit_node_id:
                    status = "🎯 CURRENT"
                elif exit_node.get('enabled_routes', 0) > 0:
                    status = "ACTIVE"
                else:
                    status = "INACTIVE"

                exit_node_list.append({
                    'name': peer_name,
                    'id': exit_node['id'],
                    'status': status
                })

            self.exit_nodes_loaded.emit(exit_node_list)
            self.finished.emit(True, "Exit nodes retrieved")
        except Exception as e:
            self.finished.emit(False, f"Failed to get exit nodes: {str(e)}")

    def _get_current_exit_node(self, peer: str) -> str:
        """Get current exit node for peer."""
        try:
            current_exit_node_id = self._get_current_exit_node_id(peer)
            if current_exit_node_id:
                all_peers = self.client.get_peers()
                return self.client.get_peer_name(current_exit_node_id, all_peers)
            return "None"
        except Exception:
            return "Unknown"

    def _get_current_exit_node_id(self, peer: str) -> Optional[str]:
        """Get current exit node ID for peer."""
        try:
            group_name = f"peer-{peer}"
            distribution_group = self.client.find_group_by_name(group_name)

            if not distribution_group:
                return None

            group_id = distribution_group.get('id')
            routes = self.client.get_routes()

            for route in routes:
                if ('peer' in route and route['peer'] and
                    'groups' in route and route['groups'] is not None and
                    group_id in route['groups'] and
                    route.get('enabled', False)):
                    return route['peer']

            return None
        except Exception:
            return None



class ConfigDialog(QDialog):
    """Dialog for editing NetBird configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NetBird Configuration")
        self.setMinimumSize(400, 300)

        self.setup_ui()
        self.load_current_config()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()

        # Header
        header = QLabel("NetBird API Configuration")
        header.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(header)

        # Form layout
        form_layout = QFormLayout()

        # API URL field
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("https://api.netbird.io")
        form_layout.addRow("API URL:", self.api_url_input)

        # Access Token field
        self.access_token_input = QLineEdit()
        self.access_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.access_token_input.setPlaceholderText("Your access token")
        form_layout.addRow("Access Token:", self.access_token_input)

        layout.addLayout(form_layout)

        # Status label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.save_and_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_config)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_current_config(self):
        """Load current configuration into the form."""
        api_url, access_token = get_api_credentials()

        if api_url:
            self.api_url_input.setText(api_url)
        if access_token:
            self.access_token_input.setText(access_token)

        self.update_status()

    def update_status(self):
        """Update the status label."""
        if validate_config():
            self.status_label.setText("✅ Configuration is complete")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("❌ Configuration is incomplete")
            self.status_label.setStyleSheet("color: red;")

    def apply_config(self):
        """Apply configuration without closing dialog."""
        try:
            api_url = self.api_url_input.text().strip()
            access_token = self.access_token_input.text().strip()

            if not api_url:
                QMessageBox.warning(self, "Error", "API URL is required")
                return

            if not access_token:
                QMessageBox.warning(self, "Error", "Access Token is required")
                return

            if not api_url.startswith(('http://', 'https://')):
                QMessageBox.warning(self, "Error", "API URL must start with http:// or https://")
                return

            # Save configuration
            from .config import save_config
            config_data = {
                'api_url': api_url.rstrip('/'),
                'access_token': access_token
            }

            save_config(config_data)
            self.update_status()

            QMessageBox.information(self, "Success", "Configuration saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{str(e)}")

    def save_and_accept(self):
        """Save configuration and close dialog."""
        self.apply_config()
        if validate_config():
            self.accept()



class NetBirdApplet(QSystemTrayIcon):
    """System tray applet for NetBird exit node management."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_peer = get_current_hostname()
        self.current_exit_node = "Unknown"

        self.setup_icon()
        self.setup_menu()
        self.setup_timer()

        # Initial status update
        self.update_status()

    def setup_icon(self):
        """Setup the system tray icon."""
        # Create a simple icon (you can replace with a proper icon file)
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.blue)
        painter.drawEllipse(2, 2, 18, 18)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(6, 6, 10, 10)
        painter.end()

        icon = QIcon(pixmap)
        self.setIcon(icon)

        self.update_tooltip()

    def setup_menu(self):
        """Setup the context menu."""
        self.main_menu = QMenu()

        # Status section
        self.status_action = self.main_menu.addAction(f"Current Peer: {self.current_peer}")
        self.status_action.setEnabled(False)

        self.exit_node_action = self.main_menu.addAction(f"Exit Node: {self.current_exit_node}")
        self.exit_node_action.setEnabled(False)

        self.main_menu.addSeparator()

        # Exit nodes submenu
        self.exit_nodes_submenu = QMenu("Exit Nodes", self.main_menu)
        self.main_menu.addMenu(self.exit_nodes_submenu)

        # Populate the submenu initially (will be updated automatically)
        self.update_exit_nodes_submenu()

        remove_action = self.main_menu.addAction("Remove from Exit Nodes")
        remove_action.triggered.connect(self.remove_from_exit_nodes)

        self.main_menu.addSeparator()

        self.main_menu.addSeparator()

        config_action = self.main_menu.addAction("Configuration...")
        config_action.triggered.connect(self.show_config_dialog)

        refresh_action = self.main_menu.addAction("Refresh Status")
        refresh_action.triggered.connect(self.update_status)

        self.main_menu.addSeparator()

        quit_action = self.main_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_applet)

        self.setContextMenu(self.main_menu)

    def update_exit_nodes_submenu(self):
        """Update the exit nodes submenu with available exit nodes."""
        if not hasattr(self, 'exit_nodes_submenu'):
            return

        # Prevent multiple concurrent updates
        if hasattr(self, '_updating_submenu') and self._updating_submenu:
            return
        self._updating_submenu = True

        # Clear existing actions
        self.exit_nodes_submenu.clear()

        # Add loading indicator
        loading_action = self.exit_nodes_submenu.addAction("Loading...")
        loading_action.setEnabled(False)

        # Load exit nodes in background
        self.worker = NetBirdWorker("get_exit_nodes")
        self.worker.exit_nodes_loaded.connect(self.populate_exit_nodes_submenu)
        self.worker.finished.connect(self.on_submenu_worker_finished)
        self.worker.start()

    def populate_exit_nodes_submenu(self, exit_nodes):
        """Populate the exit nodes submenu with the loaded data."""
        if not hasattr(self, 'exit_nodes_submenu'):
            return

        # Clear existing actions
        self.exit_nodes_submenu.clear()

        if not exit_nodes:
            no_nodes_action = self.exit_nodes_submenu.addAction("No exit nodes available")
            no_nodes_action.setEnabled(False)
            return

        # Add exit node actions using the pre-processed data from worker
        try:
            for exit_node in exit_nodes:
                try:
                    peer_name = exit_node['name']
                    status = exit_node['status']

                    # Create action text with status
                    if status == "🎯 CURRENT":
                        action_text = f"🎯 {peer_name} (CURRENT)"
                        action = self.exit_nodes_submenu.addAction(action_text)
                        action.setEnabled(False)  # Disable current exit node
                    elif status == "ACTIVE":
                        action_text = f"  {peer_name}"
                        action = self.exit_nodes_submenu.addAction(action_text)
                        action.triggered.connect(self.create_exit_node_handler(peer_name))
                    else:  # INACTIVE
                        action_text = f"  {peer_name} (inactive)"
                        action = self.exit_nodes_submenu.addAction(action_text)
                        action.triggered.connect(self.create_exit_node_handler(peer_name))

                except Exception as e:
                    # Skip this exit node if there's an error
                    continue

        except Exception as e:
            error_action = self.exit_nodes_submenu.addAction(f"Error loading: {str(e)}")
            error_action.setEnabled(False)
        finally:
            # Reset the updating flag
            self._updating_submenu = False

    def create_exit_node_handler(self, peer_name: str):
        """Create a handler function for exit node selection."""
        def handler():
            self.set_exit_node(peer_name)
        return handler

    def on_submenu_worker_finished(self, success: bool, message: str):
        """Handle submenu worker completion."""
        try:
            if not success:
                # Clear and show error
                if hasattr(self, 'exit_nodes_submenu'):
                    self.exit_nodes_submenu.clear()
                    error_action = self.exit_nodes_submenu.addAction(f"Error: {message}")
                    error_action.setEnabled(False)
        finally:
            # Reset the updating flag
            self._updating_submenu = False

    def setup_timer(self):
        """Setup automatic status refresh timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)  # This will trigger submenu update via on_status_updated
        self.timer.start(30000)  # Refresh every 30 seconds

    def update_tooltip(self):
        """Update the tooltip."""
        tooltip = f"NetBird Exit Node Manager\nPeer: {self.current_peer}\nExit Node: {self.current_exit_node}"
        self.setToolTip(tooltip)

    def update_status(self):
        """Update current status."""
        self.worker = NetBirdWorker("get_status")
        self.worker.status_updated.connect(self.on_status_updated)
        self.worker.finished.connect(self.on_status_worker_finished)
        self.worker.start()

    def on_status_updated(self, current_peer: str, current_exit_node: str):
        """Handle status update."""
        self.current_peer = current_peer
        self.current_exit_node = current_exit_node

        # Update menu items
        self.status_action.setText(f"Current Peer: {self.current_peer}")
        self.exit_node_action.setText(f"Exit Node: {self.current_exit_node}")

        self.update_tooltip()

        # Update the exit nodes submenu when status changes
        self.update_exit_nodes_submenu()

    def on_status_worker_finished(self, success: bool, message: str):
        """Handle status worker completion."""
        if not success:
            print(f"Status update failed: {message}")

    def set_exit_node(self, exit_node_name: str):
        """Set exit node for current peer."""
        self.worker = NetBirdWorker("set_exit_node",
                                   exit_node_name=exit_node_name,
                                   peer=self.current_peer)
        self.worker.finished.connect(self.on_operation_finished)
        self.worker.start()

    def remove_from_exit_nodes(self):
        """Remove current peer from all exit nodes."""
        reply = QMessageBox.question(
            None,
            "Confirm Removal",
            f"Remove '{self.current_peer}' from all exit nodes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.worker = NetBirdWorker("remove_exit_node", peer=self.current_peer)
            self.worker.finished.connect(self.on_operation_finished)
            self.worker.start()



    def show_config_dialog(self):
        """Show configuration dialog with editing capability."""
        dialog = ConfigDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh status after config change
            self.update_status()

    def on_operation_finished(self, success: bool, message: str):
        """Handle operation completion."""
        if success:
            self.showMessage("NetBird", message, QSystemTrayIcon.MessageIcon.Information, 3000)
            # Update status after successful operation
            QTimer.singleShot(1000, self.update_status)
        else:
            self.showMessage("NetBird Error", message, QSystemTrayIcon.MessageIcon.Critical, 5000)

    def quit_applet(self):
        """Quit the applet."""
        QApplication.quit()


def main():
    """Main entry point for the applet."""
    app = QApplication(sys.argv)

    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "System Tray",
                           "System tray is not available on this system.")
        sys.exit(1)

    # Check configuration
    if not validate_config():
        QMessageBox.critical(None, "Configuration Error",
                           "NetBird API credentials not configured.\n\n"
                           "Please run in terminal:\n"
                           "netbird-cli config set\n\n"
                           "Or set environment variables:\n"
                           "• NETBIRD_API_URL\n"
                           "• NETBIRD_ACCESS_TOKEN")
        sys.exit(1)

    # Create and show the applet
    applet = NetBirdApplet()
    applet.show()

    # Prevent app from quitting when last window is closed
    app.setQuitOnLastWindowClosed(False)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
