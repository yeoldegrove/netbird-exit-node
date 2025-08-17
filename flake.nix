{
  description = "NetBird Exit Node - Python Development Environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05"; # https://github.com/NixOS/nixpkgs
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable"; # https://github.com/NixOS/nixpkgs
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, nixpkgs-unstable, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pkgs-unstable = nixpkgs-unstable.legacyPackages.${system};
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          requests
          click
          pyqt6
        ]);
        buildInputs = with pkgs; [
          libGL
          libGLU
          libxkbcommon
          glib
          zlib
          xorg.libX11
          xorg.libXext
          xorg.libXrender
          fontconfig
          freetype
          stdenv.cc.cc.lib
          qt6.qtbase
          qt6.qtwayland
        ];
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            python3Packages.pip
            python3Packages.setuptools
            python3Packages.wheel
            poetry
            # GUI dependencies for the applet
            qt6.qtbase
            qt6.qtwayland
          ] ++ buildInputs;

          shellHook = ''
            # Set up Qt environment for the applet
            export QT_QPA_PLATFORM=xcb
            export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.qt6.qtbase}/lib/qt-6/plugins"
            export QT_PLUGIN_PATH="${pkgs.qt6.qtbase}/lib/qt-6/plugins:$QT_PLUGIN_PATH"

            poetry install
            echo "Installing Poetry virtual environment..."
            eval "$(poetry env activate)"
            echo "NetBird Exit Node Python Development Environment"
            echo "Python version: $(python --version)"
            echo "Poetry version: $(poetry --version)"
            echo "Virtual environment: ACTIVATED"
            echo ""
            echo "Available commands:"
            echo "  python - Python interpreter"
            echo "  pip - Package installer"
            echo "  poetry - Dependency management"
            echo "  netbird-exit-node - NetBird CLI tool (terminal/ncurses)"
            echo "  netbird-exit-node-applet - NetBird system tray applet (GUI)"
            echo ""
            echo "Environment variables (take precedence over config file):"
            echo "  export NETBIRD_API_URL=\"https://your-netbird-api.com\""
            echo "  export NETBIRD_ACCESS_TOKEN=\"your-access-token\""
            echo ""
            echo "Quick start:"
            echo "  netbird-exit-node config set                # Configure API credentials"
            echo "  netbird-exit-node config show               # Show configuration status"
            echo "  netbird-exit-node                           # Interactive ncurses menu (no args)"
            echo "  netbird-exit-node --help                    # Show CLI usage"
            echo "  netbird-exit-node routes list               # List routes for current hostname"
            echo "  netbird-exit-node routes list --peer host   # List routes for specific peer"
            echo "  netbird-exit-node exit-nodes list           # List all exit nodes"
            echo "  netbird-exit-node exit-nodes info           # Show peer info & groups"
            echo "  netbird-exit-node exit-nodes info --peer peer-2 # Show info for specific peer"
            echo "  netbird-exit-node exit-nodes set exit-node-1     # Set exit node for current peer"
            echo "  netbird-exit-node exit-nodes set exit-node-1 --peer peer-2 # Set exit node for peer-2"
            echo "  netbird-exit-node exit-nodes rm             # Remove current peer from exit nodes"

          '';
        };

        # Package definitions
        packages = {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "netbird-exit-node";
            version = "0.1.0";
            src = ./.;
            format = "pyproject";

            nativeBuildInputs = with pkgs; [
              python3Packages.poetry-core
              makeWrapper
              qt6.wrapQtAppsHook
            ];

            buildInputs = with pkgs; [
              libGL
              libGLU
              libxkbcommon
              glib
              zlib
              xorg.libX11
              xorg.libXext
              xorg.libXrender
              fontconfig
              freetype
              stdenv.cc.cc.lib
              qt6.qtbase
              qt6.qtwayland
            ];

            propagatedBuildInputs = with pkgs.python3Packages; [
              requests
              click
              pyqt6
            ] ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isLinux [
              # Linux-specific dependencies
            ] ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isDarwin [
              # macOS-specific dependencies
            ] ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isWindows [
              # Windows-specific dependencies
              windows-curses
            ];

            # Let wrapQtAppsHook handle Qt application wrapping automatically
            # It will set up Qt plugin paths and environment variables

            # Additional runtime dependencies for GUI libraries
            qtWrapperArgs = [
              "--prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [
                pkgs.libGL pkgs.libGLU pkgs.libxkbcommon pkgs.glib.out pkgs.zlib
                pkgs.xorg.libX11 pkgs.xorg.libXext pkgs.xorg.libXrender
                pkgs.fontconfig.lib pkgs.freetype pkgs.stdenv.cc.cc.lib
              ]}"
              "--set QT_QPA_PLATFORM xcb"
            ];

            postInstall = ''
              mkdir -p $out/share/applications
              cp ${./netbird-exit-node-applet.desktop} $out/share/applications/
            '';

            meta = with pkgs.lib; {
              description = "NetBird Exit Node Management Tool";
              homepage = "https://github.com/yeoldegrove/netbird-exit-node";
              license = licenses.gpl3Only;
              maintainers = [ ];
              platforms = platforms.unix;
            };
          };

          netbird-exit-node = self.packages.${system}.default;
        };
      });
}
