# Virtual Environment Manager

A comprehensive Python package for managing virtual environments, providing equivalent functionality to the bash `venv.sh` script with enhanced features.

## Features

- **Environment Creation**: Create virtual environments using `uv`, `python3`, or `python` with automatic fallback
- **Smart Activation**: Activate environments with directory mapping for auto-activation
- **Package Management**: Install, uninstall, update, and search packages using `uv` or `pip`
- **History Tracking**: Track directory-to-environment mappings for automatic activation
- **Cross-Platform**: Works on Linux, macOS, and Windows with Python 3.7+

## Installation

### From Source

```bash

pip install git+https://github.com/anhvth/uv-virtual-environs-manager
```

### From PyPI (once published)

```bash
pip install pyve
```

## Quick Start

```bash
# Create a new virtual environment
ve create myproject --python=3.12

# Activate an environment (creates directory mapping)
atv myproject

# List all environments
ve list

# Install packages
ve install requests numpy

# Show environment info
ve info

# Auto-activation: when you cd back to this directory, 
# the environment will be suggested for activation
```

## Commands

### Main Commands

- `ve create <name> [options]` - Create a new virtual environment
- `ve activate <name>` - Activate a virtual environment  
- `ve deactivate` - Deactivate current virtual environment
- `ve list` - List all virtual environments
- `ve delete <name>` - Delete a virtual environment
- `ve info` - Show current virtual environment info
- `ve which <name>` - Show path to virtual environment

### Package Management

- `ve install <pkg>...` - Install packages in active venv
- `ve installed` - List installed packages in active venv
- `ve uninstall <pkg>...` - Uninstall packages from active venv
- `ve search <pkg>` - Search for packages on PyPI
- `ve update <pkg>...` - Update packages in active venv
- `ve run <cmd>...` - Run command in active venv

### History & Auto-Activation

- `ve history` - Show directory → environment mappings
- `ve clear-history` - Clear all atv history
- `atv <name>` - Activate with directory mapping (alias for `ve activate`)

### Utility Commands

- `create_env <name>` - Alternative create command
- `install_uv` - Install uv package manager

## Configuration

The package uses the following files for tracking:

- `~/.venv_all_env` - Global environment tracking
- `~/.config/atv_history` - Directory-to-environment mappings
- `~/.venvs/` - Default location for virtual environments
- `~/.last_venv` - Last activated environment

## Shell Integration

For full shell integration (auto-activation on directory change), add this to your shell configuration:

### Zsh

```bash
# Add to ~/.zshrc
eval "$(ve shell-integration zsh)"  # Future feature
```

### Bash

```bash
# Add to ~/.bashrc
eval "$(ve shell-integration bash)"  # Future feature
```

## Auto-Activation

When you use `atv <name>` to activate an environment, the current directory is mapped to that environment. When you navigate back to that directory later, you'll be reminded to activate the environment.

## Examples

```bash
# Create a new project environment
ve create myproject --python=3.12
cd /path/to/myproject

# Install dependencies
ve install requests flask pytest

# Later, when you cd back to the project
cd /path/to/myproject
# The tool will remind you about the mapped environment

# View all mappings

# Clean up
ve delete myproject
```

## Differences from Shell Version

- **Shell Integration**: The Python version can't directly modify the current shell environment. It provides activation commands to run.
- **Auto-Activation**: Requires shell integration for automatic activation on directory change.
- **Browser Opening**: Package search opens browser when available.

## Development

### Local Development

```bash
# Clone and install in development mode
git clone <repo-url>
cd virtual_envs_manager
pip install -e .

# Run tests (if available)
python -m pytest

# Type checking
mypy vex/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Author

anhvth5