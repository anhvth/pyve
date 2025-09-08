# Copilot Instructions for pyve (Virtual Environment Manager)

## Project Overview
This is a Python virtual environment manager (`pyve`) that provides conda-style CLI commands and shell integration for managing Python virtual environments. It's designed as a comprehensive replacement for manual venv management with features like auto-activation, directory mapping, and unified package management.

## Architecture & Key Components

### Core Structure
- **`pyve/manager.py`**: Core `VenvManager` class handling all environment operations
- **`pyve/cli.py`**: Rich CLI interface with conda-style command compatibility  
- **`pyve/shell_integration_*.sh`**: Shell wrapper functions enabling proper activation
- **`install_shell_integration.py`**: Standalone installer for shell integration

### Key Design Patterns

#### Dual CLI Interface
The project supports both simple and conda-style commands:
```bash
# Simple style
ve create myenv --python=3.11
ve activate myenv

# Conda-style (fully compatible)
ve env create -n myenv python=3.11 numpy pandas
ve env list
ve env remove -n myenv
```

#### Shell Integration Wrapper Pattern
Unlike pure Python tools, `pyve` uses shell function wrappers to enable proper environment activation:
- `ve activate` calls Python CLI → outputs activation command → shell wrapper sources the script
- Shell integration files in `pyve/shell_integration_*.sh` contain the wrapper functions
- Installation via `ve install` (no packages) adds shell functions to `~/.zshrc`/`~/.bashrc`

#### State Management Files
Environment state is tracked in multiple files:
- `~/.venv_all_env`: Global environment registry (name → activate_script_path)
- `~/.config/atv_history`: Directory → environment mappings for auto-activation
- `~/.venvs/`: Default virtual environment storage location
- `~/.last_venv`: Last activated environment tracking

## Development Patterns

### Rich CLI Framework
All user output uses Rich library for consistent formatting:
- Color helpers: `c_red()`, `c_green()`, `c_yellow()`, `c_blue()` methods in `VenvManager`
- Console object: `self.console = Console()` for Rich output
- Error handling with colored messages and help suggestions

### Command Parsing Pattern
CLI commands follow this pattern in `cli.py`:
1. Check for help flags: `check_help_flag(args)`
2. Parse arguments with special handling for conda-style syntax
3. Interactive selection with fzf when no args provided
4. Delegate to `VenvManager` methods

### Environment Creation Flow
1. Parse Python version and packages from args (handles `python=3.11` syntax)
2. Use tool preference: `uv` → `python3` → `python` with fallback
3. Update global tracking file with environment paths
4. Install packages if specified during creation

### Auto-Activation Mechanism
Directory-to-environment mapping enables auto-activation suggestions:
- `ve activate` updates `~/.config/atv_history` with current directory
- Shell hook (`_ve_auto_activate`) checks mappings on directory change
- Suggests activation command when entering mapped directories

## Critical Development Workflows

### Testing Environment Creation
```bash
# Test both command styles
ve create testenv --python=3.11
ve env create -n testenv2 python=3.11 requests

# Verify tracking files
cat ~/.venv_all_env
cat ~/.config/atv_history
```

### Shell Integration Development
```bash
# Install integration for testing
ve install
source ~/.zshrc

# Test activation (should work without PATH manipulation)
ve activate testenv
echo $VIRTUAL_ENV
```

### Package Management Testing
Base requirements are auto-installed from `base_reqs.txt` with every new environment. Test package commands:
```bash
ve install requests numpy  # In active environment
ve installed               # List packages
ve search pandas           # Opens browser search
```

### Version Management
Use `bumpversion.sh` script (requires Poetry in PATH):
```bash
./bumpversion.sh patch  # Bumps version, commits, pushes
```

## Integration Points

### External Tool Dependencies
- **uv**: Preferred package manager and environment creator (fallback to pip/venv)
- **fzf**: Interactive environment selection (`ve activate` with no args)
- **Poetry**: Version management in `bumpversion.sh`
- **json5**: VS Code settings.json manipulation

### Cross-Platform Considerations
- Shell detection: `$SHELL` environment variable (`zsh` vs bash)
- Path handling: Uses `pathlib.Path` throughout
- Executable finding: `shutil.which()` for tool detection

### VS Code Integration
`ve activate --vscode` updates `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "/path/to/venv/bin/python",
  "python.terminal.activateEnvironment": false
}
```

## Error Handling Patterns

### Graceful Fallbacks
- Tool preference chain: uv → python3 → python → fail
- Config file creation: Create if missing, backup before modification
- Shell integration: Check for existing functions before installation

### User Feedback
Always provide actionable error messages with suggestions:
```python
console.print("❌ Environment name is required", style="red")
console.print("💡 Use: ve create -n myenv", style="cyan")
```

## Testing Strategy

### Manual Testing Commands
```bash
# Test conda compatibility
ve env create -n test python=3.11 requests
ve env list
ve env remove -n test

# Test shell integration
ve install
ve activate myenv  # Should work without manual sourcing
```

### State Verification
Check tracking files after operations:
- Environment creation → `~/.venv_all_env` updated
- Activation → `~/.config/atv_history` updated  
- Deletion → Files cleaned up properly

When modifying core functionality, always test both command syntaxes and verify shell integration works correctly.