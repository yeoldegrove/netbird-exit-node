# NetBird Exit Node Management Tool

A comprehensive Python tool for managing NetBird exit nodes and routes with multiple interfaces: command-line, interactive ncurses menu, and system tray applet.

## 🚀 Features

### Core Functionality

- **Exit Node Management**: Set, remove, and list exit nodes for any peer
- **Route Management**: List and analyze NetBird routes
- **Multiple Interfaces**: CLI, ncurses menu, and system tray applet
- **Peer Management**: Target specific peers or use current hostname
- **Configuration Management**: Store API credentials securely

### Interfaces

- **🖥️ Command Line**: Full-featured CLI with all options
- **📟 Ncurses Menu**: Interactive terminal interface
- **🖱️ System Tray Applet**: GUI applet for desktop environments

## 📋 Requirements

- Python 3.9+
- NetBird API access with valid credentials
- Poetry for dependency management
- Qt6 (for system tray applet)
- Linux, macOS, or Windows

## 🛠️ Installation

### Using Nix (Recommended)

1. Clone this repository:

   ```bash
   git clone <repository-url>
   cd netbird-exit-node
   ```

2. Enter the Nix development shell:

   ```bash
   nix develop
   ```

3. The tools are now available:
   ```bash
   netbird-exit-node --help
   netbird-exit-node-applet
   ```

### Using Poetry

1. Install Poetry if not available:

   ```bash
   pip install poetry
   ```

2. Install dependencies:

   ```bash
   poetry install
   ```

3. Activate virtual environment:
   ```bash
   eval "$(poetry env activate)"
   ```

### Building with Nix

Build the package:

```bash
nix build
```

Run the built package:

```bash
result/bin/netbird-exit-node --help
result/bin/netbird-exit-node-applet
```

## ⚙️ Configuration

### First-time Setup

Configure your NetBird API credentials:

```bash
netbird-exit-node config set
```

This will prompt for:

- **API URL**: Your NetBird API endpoint (e.g., `https://api.netbird.io`)
- **Access Token**: Your NetBird access token

### View Configuration

```bash
netbird-exit-node config show
```

### Environment Variables (Alternative)

You can also use environment variables (they take precedence over config file):

```bash
export NETBIRD_API_URL="https://your-netbird-api.com"
export NETBIRD_ACCESS_TOKEN="your-access-token"
```

Configuration is stored in `~/.config/netbird/netbird-exit-node.json`.

## 📖 Usage

### Command Line Interface (CLI)

#### Exit Node Management

**List all exit nodes:**

```bash
netbird-exit-node exit-nodes list
```

**Set exit node for current peer:**

```bash
netbird-exit-node exit-nodes set exit-node-1
```

**Set exit node for specific peer:**

```bash
netbird-exit-node exit-nodes set exit-node-1 --peer hostname
```

**Remove from all exit nodes:**

```bash
netbird-exit-node exit-nodes rm
```

**Remove specific peer from exit nodes:**

```bash
netbird-exit-node exit-nodes rm --peer hostname
```

**Show exit node information:**

```bash
netbird-exit-node exit-nodes info
netbird-exit-node exit-nodes info --peer hostname
```

#### Route Management

**List routes for current peer:**

```bash
netbird-exit-node routes list
```

**List routes for specific peer:**

```bash
netbird-exit-node routes list --peer hostname
```

**JSON output:**

```bash
netbird-exit-node routes list --json-output
```

#### Configuration Management

**Set API credentials:**

```bash
netbird-exit-node config set
```

**Show current configuration:**

```bash
netbird-exit-node config show
```

#### Global Options

- `--verbose`: Enable verbose output for debugging
- `--help`: Show help for any command

#### Command Examples

```bash
# Basic exit node management
netbird-exit-node exit-nodes list
netbird-exit-node exit-nodes set exit-node-1

# Managing other peers
netbird-exit-node exit-nodes set exit-node-2 --peer server-1
netbird-exit-node exit-nodes rm --peer mobile-peer

# Route inspection
netbird-exit-node routes list --peer my-server
netbird-exit-node routes list --json-output > routes.json

# Configuration
netbird-exit-node config set
netbird-exit-node config show
```

### Interactive Ncurses Menu

Launch the interactive terminal interface:

```bash
netbird-exit-node
```

**Menu Options:**

1. **Set Exit Node**: Choose from available exit nodes
2. **Remove from Exit Nodes**: Remove current peer from all exit nodes
3. **Change Target Peer**: Switch to managing a different peer
4. **Quit**: Exit the application

**Navigation:**

- **↑/↓**: Navigate menu options
- **Enter**: Select option
- **Esc/q**: Quit application

**Features:**

- Visual indicators for current exit node status
- Real-time status updates
- Error handling with user-friendly messages
- Peer selection with online status

### System Tray Applet

Launch the GUI system tray applet:

```bash
netbird-exit-node-applet
```

**Features:**

- **System Tray Icon**: Always accessible from taskbar
- **Status Display**: Shows current exit node in tooltip
- **Exit Node Submenu**: Direct access to available exit nodes
- **Current Node Indicator**: 🎯 marks currently active exit node
- **Remove Option**: Quick removal from exit nodes
- **Configuration Dialog**: Edit API credentials from GUI
- **Auto-refresh**: Periodic status updates

**Menu Structure:**

```
NetBird Exit Node Manager
├── Exit Nodes ►
│   ├── 🎯 exit-node-1 (CURRENT)
│   ├── exit-node-2
│   └── exit-node-3
├── Remove from Exit Nodes
├── ─────────────
├── Configuration...
├── Refresh Status
└── Quit
```

**Usage:**

1. **Right-click** tray icon to open menu
2. **Hover over "Exit Nodes"** to see submenu
3. **Click exit node name** to switch to it
4. **Click "Remove from Exit Nodes"** to disconnect
5. **Click "Configuration..."** to edit API settings

## 🔧 API Endpoints Used

- `GET /api/peers` - List all peers in the network
- `GET /api/routes` - List all routes and exit nodes
- `GET /api/groups` - List distribution groups
- `POST /api/groups` - Create distribution groups for peers
- `PUT /api/groups/{id}` - Update group membership
- `PUT /api/routes/{id}` - Update route configurations

## 📊 Output Examples

### Exit Nodes List

```
Exit Nodes (3 found):
==================================================

🟢 Exit Node 1 (ACTIVE):
  Name: exit-node-1 ⭐
  ID: nb_1234567890abcdef
  Total Routes: 1
  Enabled Routes: 1 🚀
  Networks: 0.0.0.0/0 (🟢 ACTIVE)

🟢 Exit Node 2 (ACTIVE):
  Name: exit-node-2 ⭐
  ID: nb_2345678901bcdefg
  Total Routes: 1
  Enabled Routes: 1 🚀
  Networks: 0.0.0.0/0 (🟢 ACTIVE)
```

### Routes List

```
Routes available for peer 'my-computer':
============================================

🌐 Route 1 (ENABLED):
  ID: nb_4567890123defghi
  Network: 0.0.0.0/0
  Description: Default Route via exit-node-1
  Exit Node: exit-node-1 (nb_1234567890abcdef)
  Groups: peer-my-computer
  Metric: 9999
  Masquerade: Yes
  Domains: None
```

### Exit Node Info

```
NetBird Exit Node Information
========================================
Target Peer: my-computer
Required Group Name: peer-my-computer
✅ Distribution group 'peer-my-computer' exists
Current Exit Nodes: exit-node-1 (🟢 ACTIVE)

Available Groups:
--------------------
• All (ID: nb_5678901234efghij, 11 peers)
• server (ID: nb_6789012345fghijk, 8 peers)
• peer-my-computer (ID: nb_7890123456ghijkl, 1 peers)

Available Exit Nodes:
----------------------
• nb_3456789012cdefgh (exit-node-3) (🟢 ACTIVE)
• nb_2345678901bcdefg (exit-node-2) (🟢 ACTIVE)
• nb_1234567890abcdef (exit-node-1) (🟢 ACTIVE)
```

## 🛡️ Error Handling

The tool provides comprehensive error handling with user-friendly messages:

### Connection Errors

```
❌ Connection Error: Unable to reach the NetBird API server.
   Server: https://api.netbird.io
   Please check your internet connection and API URL.
```

### Authentication Errors

```
❌ Authentication Error: Invalid access token.
   Please check your NetBird access token.
   You can get a new token from: https://app.netbird.io/settings/tokens
```

### Configuration Errors

```
❌ Configuration Error: NetBird API credentials not found.
   Run 'netbird-exit-node config set' to configure your credentials.
```

### Validation

- Input validation for exit node names
- Peer existence verification
- Network connectivity checks
- API response validation

## 🔧 Development

### Development Environment

```bash
# Enter Nix development shell
nix develop

# Or use Poetry directly
poetry install
poetry shell
```

### Code Quality

```bash
# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run flake8

# Type checking
poetry run mypy netbird_exit_node/

# Run tests
poetry run pytest
```

### Building

```bash
# Build with Nix
nix build

# Build wheel with Poetry
poetry build
```

### Architecture

```
netbird_exit_node/
├── main.py          # CLI commands and API client
├── menu.py          # Ncurses interactive interface
├── applet.py        # PyQt6 system tray applet
├── config.py        # Configuration management
└── __init__.py      # Package initialization
```

## 🖥️ Platform Support

- **Linux**: Full support (CLI, ncurses, applet)
- **macOS**: Full support (CLI, ncurses, applet)
- **Windows**: CLI and applet support (ncurses limited)

### GUI Dependencies

The system tray applet requires:

- Qt6 libraries
- System tray support in desktop environment
- Proper Qt platform plugins (automatically configured)

## 🐛 Troubleshooting

### Qt Platform Issues

If the applet shows platform plugin errors:

```bash
# Set Qt platform explicitly
export QT_QPA_PLATFORM=xcb  # Linux
export QT_QPA_PLATFORM=cocoa  # macOS
```

### API Connection Issues

1. Verify API URL and access token
2. Check network connectivity
3. Ensure access token has proper permissions
4. Use `--verbose` flag for detailed debugging

### Configuration Issues

```bash
# Reset configuration
rm ~/.config/netbird/netbird-exit-node.json
netbird-exit-node config set
```

## 📄 License

This project is licensed under the GNU General Public License v3.0. See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📚 Additional Resources

- [NetBird Documentation](https://docs.netbird.io/)
- [NetBird API Reference](https://docs.netbird.io/api)
- [Python Poetry Documentation](https://python-poetry.org/docs/)
- [Nix Package Manager](https://nixos.org/download.html)
