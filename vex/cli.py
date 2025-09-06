"""
Command-line interface for the virtual environment manager.
"""

import sys
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .manager import VenvManager


def run_command(cmd, capture_output=False):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def has_fzf():
    """Check if fzf is available."""
    return run_command("which fzf", capture_output=True)[0]


def get_available_commands():
    """Get list of available commands."""
    return [
        'create', 'activate', 'deactivate', 'list', 'delete', 'remove',
        'info', 'which', 'install', 'installed', 'uninstall', 'search',
        'update', 'run', 'history', 'clear-history', 'remove-all-except-base'
    ]


def suggest_command(partial_cmd):
    """Suggest commands based on partial input."""
    available = get_available_commands()
    suggestions = [cmd for cmd in available if cmd.startswith(partial_cmd)]
    return suggestions


def interactive_env_selection():
    """Use fzf to interactively select an environment."""
    if not has_fzf():
        console = Console()
        console.print("fzf not found. Install fzf for interactive selection: https://github.com/junegunn/fzf")
        return None
    
    manager = VenvManager()
    
    # Get list of environments
    envs = []
    if manager.global_env_file.exists():
        for line in manager.global_env_file.read_text().splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                env_name, activate_path = parts
                if manager._find_executable("python") and str(manager._find_executable("python")).startswith(str(manager.home / ".venvs" / env_name)):
                    envs.append(f"{env_name} (active)")
                else:
                    envs.append(env_name)
    
    if not envs:
        console = Console()
        console.print("No environments found to select from.")
        return None
    
    # Use fzf for selection
    env_list = "\n".join(envs)
    try:
        result = subprocess.run(
            ["fzf", "--height=10", "--border", "--prompt=Select environment: "],
            input=env_list,
            text=True,
            capture_output=True
        )
        if result.returncode == 0 and result.stdout.strip():
            selected = result.stdout.strip()
            # Remove (active) suffix if present
            env_name = selected.replace(" (active)", "")
            return env_name
    except Exception as e:
        console = Console()
        console.print(f"Error with fzf selection: {e}")
    
    return None


def show_help_suggestions(console: Console, partial_cmd=""):
    """Show help with command suggestions."""
    manager = VenvManager()
    
    if partial_cmd:
        suggestions = suggest_command(partial_cmd)
        if suggestions:
            console.print(f"💡 Did you mean: {' | '.join(suggestions)}", style="cyan")
        else:
            console.print(f"❌ Unknown command: '{partial_cmd}'", style="red")
    
    # Create a beautiful help table
    table = Table(title="[bold blue]Virtual Environment Manager (ve)[/bold blue]", box=None)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    
    commands = {
        "[bold green]Environment Management[/bold green]": [
            ("create [-n NAME] [--python VERSION] [packages...]", "Create a new virtual environment"),
            ("activate <name> [--vscode] [--auto]", "Activate a virtual environment"),
            ("deactivate", "Deactivate current virtual environment"),
            ("list", "List all virtual environments"),
            ("delete <name>", "Delete a virtual environment"),
            ("info", "Show current virtual environment info"),
        ],
        "[bold yellow]Conda-style Commands[/bold yellow]": [
            ("env create -n <name> [python=VERSION] [packages...]", "Create environment (conda-style)"),
            ("env list", "List environments (conda-style)"),
            ("env remove -n <name>", "Remove environment (conda-style)"),
        ],
        "[bold magenta]Package Management[/bold magenta]": [
            ("install", "Install shell integration (enables proper activation)"),
            ("install <pkg>...", "Install packages in active venv"),
            ("installed", "List installed packages"),
            ("uninstall <pkg>...", "Uninstall packages"),
            ("update <pkg>...", "Update packages"),
            ("search <pkg>", "Search for packages on PyPI"),
        ],
        "[bold blue]Utilities[/bold blue]": [
            ("which <name>", "Show path to virtual environment"),
            ("run <cmd>...", "Run command in active venv"),
            ("history", "Show directory mappings"),
            ("clear-history", "Clear all mappings"),
        ]
    }
    
    for category, cmds in commands.items():
        table.add_row("", "")  # Empty row for spacing
        table.add_row(f"[bold]{category}[/bold]", "")
        for cmd, desc in cmds:
            table.add_row(f"  ve {cmd}", desc)
    
    console.print(table)
    
    # Quick start examples in a panel
    examples = """[bold]Quick Start Examples:[/bold]
  [green]# First-time setup[/green]
  ve install                 [dim]# Install shell integration (like conda install zsh)[/dim]
  source ~/.zshrc            [dim]# Reload shell config[/dim]
  
  [green]# Create environments[/green]
  ve create myproject --python=3.12
  ve env create -n myenv python=3.11 numpy pandas
  
  [green]# Activate and use[/green]
  ve activate myproject      [dim]# Now works properly with shell integration![/dim]
  ve install requests flask
  
  [green]# List and manage[/green]
  ve list                    [dim]# or ve env list[/dim]
  ve info                    [dim]# show current environment[/dim]
  ve delete myproject"""
    
    panel = Panel(examples, title="[bold blue]🚀 Quick Start[/bold blue]", border_style="blue")
    console.print(panel)
    
    console.print("\n[dim]Help for specific commands: ve create --help, ve env create --help, ve activate --help[/dim]")
    
    console.print("\n[bold cyan]Auto-Activation:[/bold cyan]")
    console.print("When you activate an environment, the current directory is mapped")
    console.print("to that environment for future auto-activation when you cd back.")


def check_help_flag(args):
    """Check if help flag is present in args and return remaining args."""
    help_flags = ['-h', '--help', 'help']
    for flag in help_flags:
        if flag in args:
            return True, [arg for arg in args if arg != flag]
    return False, args

def show_command_help(command, subcommand=None):
    """Show help for specific commands."""
    console = Console()
    
    if command == 'create':
        console.print("🐍 Create Virtual Environment")
        console.print("=" * 40)
        console.print("Usage:")
        console.print("  ve create <name> [--python VERSION] [packages...]")
        console.print("  ve create -n <name> [--python VERSION] [packages...]")
        console.print("")
        console.print("Arguments:")
        console.print("  name                    Environment name (required)")
        console.print("  -n NAME                 Environment name (conda-style)")
        console.print("  --python VERSION        Python version to use (e.g., 3.11, 3.12)")
        console.print("  packages...             Additional packages to install")
        console.print("")
        console.print("Examples:")
        console.print("  ve create myproject")
        console.print("  ve create myproject --python=3.11")
        console.print("  ve create -n myenv --python=3.11 requests flask")
        console.print("  ve create dataproject python=3.11 numpy pandas matplotlib")
        console.print("")
        console.print("Conda-style equivalents:")
        console.print("  ve env create -n myenv → ve create -n myenv")
        console.print("  ve env create -n myenv python=3.11 → ve create -n myenv python=3.11")
        
    elif command == 'env' and subcommand == 'create':
        console.print("🐍 Create Virtual Environment (Conda-style)")
        console.print("=" * 45)
        console.print("Usage:")
        console.print("  ve env create -n <name> [python=VERSION] [packages...]")
        console.print("")
        console.print("Arguments:")
        console.print("  -n NAME                 Environment name (required)")
        console.print("  python=VERSION          Python version specification")
        console.print("  packages...             Package specifications")
        console.print("")
        console.print("Examples:")
        console.print("  ve env create -n myenv")
        console.print("  ve env create -n myenv python=3.11")
        console.print("  ve env create -n dataenv python=3.11 numpy pandas matplotlib")
        console.print("  ve env create -n webdev python=3.12 flask requests")
        console.print("")
        console.print("Note: This is fully compatible with conda syntax")
        
    elif command == 'activate':
        console.print("🔄 Activate Virtual Environment")
        console.print("=" * 35)
        console.print("Usage:")
        console.print("  ve activate <name> [--vscode] [--auto]")
        console.print("")
        console.print("Arguments:")
        console.print("  name                   Environment name to activate")
        console.print("  --vscode               Update .vscode/settings.json with Python interpreter path")
        console.print("  --auto                 Add auto-activation to shell config (~/.zshrc or ~/.bashrc)")
        console.print("")
        console.print("Features:")
        console.print("  - Maps current directory to environment for auto-activation")
        console.print("  - Use fzf for interactive selection if no name provided")
        console.print("  - Shows activation command to run")
        console.print("  - With --vscode: Updates VS Code settings for Python interpreter")
        console.print("  - With --auto: Adds auto-activation to shell config")
        console.print("")
        console.print("Examples:")
        console.print("  ve activate myproject")
        console.print("  ve activate myproject --vscode")
        console.print("  ve activate myproject --auto")
        console.print("  ve activate myproject --vscode --auto")
        console.print("  ve activate                    # Interactive selection with fzf")
        
    elif command == 'env' and subcommand == 'list':
        console.print("📋 List Virtual Environments (Conda-style)")
        console.print("=" * 45)
        console.print("Usage:")
        console.print("  ve env list")
        console.print("")
        console.print("Output format:")
        console.print("  # conda environments:")
        console.print("  #")
        console.print("  * myenv      /path/to/myenv     (active)")
        console.print("    otherenv   /path/to/otherenv")
        console.print("")
        console.print("Legend:")
        console.print("  *  Currently active environment")
        console.print("     Available environment")
        
    elif command == 'install':
        console.print("📦 Install Shell Integration or Packages")
        console.print("=" * 45)
        console.print("Usage:")
        console.print("  ve install                     # Install ve shell integration")
        console.print("  ve install <package>...        # Install packages in active venv")
        console.print("")
        console.print("Shell Integration:")
        console.print("  ve install                     Sets up shell functions in ~/.zshrc or ~/.bashrc")
        console.print("                                 This enables proper 've activate' functionality")
        console.print("                                 (Similar to 'conda install zsh')")
        console.print("")
        console.print("Package Installation:")
        console.print("  ve install requests            Install single package")
        console.print("  ve install numpy pandas        Install multiple packages")
        console.print("")
        console.print("Examples:")
        console.print("  ve install                     # Set up shell integration first")
        console.print("  ve install requests flask      # Then install packages")
        console.print("")
        console.print("Note: Run 've install' first to enable proper environment activation")
        
    elif command == 'list':
        console.print("📋 List Environments or Packages")
        console.print("=" * 35)
        console.print("Usage:")
        console.print("  ve list                        # List environments")
        console.print("  ve env list                    # List environments (conda-style)")
        console.print("  ve installed                   # List installed packages")
        console.print("")
        console.print("For package listing, use 've installed'")
        
    elif command == 'env' and subcommand == 'list':
        console.print("📋 List Virtual Environments (Conda-style)")
        console.print("=" * 45)
        console.print("Usage:")
        console.print("  ve env list")
        console.print("")
        console.print("Output format:")
        console.print("  # conda environments:")
        console.print("  #")
        console.print("  * myenv      /path/to/myenv     (active)")
        console.print("    otherenv   /path/to/otherenv")
        console.print("")
        console.print("Legend:")
        console.print("  *  Currently active environment")
        console.print("     Available environment")
        
    else:
        console.print(f"No detailed help available for: {command}")
        if subcommand:
            console.print(f"Subcommand: {subcommand}")
        console.print("Use 've --help' for general help")

def main():
    """Main entry point for the ve command."""
    console = Console()
    
    # Check for help flags at the top level
    if len(sys.argv) >= 2 and sys.argv[1] in ('help', '-h', '--help'):
        show_help_suggestions(console)
        return
    
    manager = VenvManager()
    
    if len(sys.argv) < 2:
        show_help_suggestions(console)
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    # Handle help commands
    if command in ('help', '-h', '--help'):
        show_help_suggestions(console)
        return
    
    
    # Handle conda-style commands (env subcommands)
    if command == 'env':
        if not args:
            console.print("❌ Usage: ve env <subcommand> [options]", style="red")
            console.print("💡 Conda-style environment management:", style="cyan")
            console.print("   ve env create -n myenv python=3.11", style="blue")
            console.print("   ve env list", style="blue")
            console.print("   ve env remove -n myenv", style="blue")
            return
        
        subcommand = args[0]
        sub_args = args[1:]
        
        # Check for help flags in env subcommands
        needs_help, cleaned_sub_args = check_help_flag(sub_args)
        if needs_help:
            show_command_help('env', subcommand)
            return
        
        if subcommand == 'create':
            # Handle conda-style create
            env_name = None
            python_version = None
            packages = []
            
            i = 0
            while i < len(cleaned_sub_args):
                arg = cleaned_sub_args[i]
                if arg == '-n' and i + 1 < len(cleaned_sub_args):
                    env_name = cleaned_sub_args[i + 1]
                    i += 2
                elif arg.startswith('--python='):
                    python_version = arg.split('=', 1)[1]
                    i += 1
                elif arg == 'python' and i + 1 < len(cleaned_sub_args) and cleaned_sub_args[i + 1].startswith('='):
                    # Handle "python=3.11" format
                    python_version = cleaned_sub_args[i + 1][1:]  # Remove the '='
                    i += 2
                elif '=' in arg:
                    # Handle package=version format
                    if arg.startswith('python='):
                        python_version = arg.split('=', 1)[1]
                    else:
                        pkg_spec = arg.split('=', 1)
                        packages.append(pkg_spec[0])
                    i += 1
                else:
                    if env_name is None:
                        env_name = arg
                    else:
                        packages.append(arg)
                    i += 1
            
            if not env_name:
                console.print("❌ Environment name is required", style="red")
                console.print("💡 Use: ve env create -n myenv", style="cyan")
                return
            
            # Build extra args for venv creation
            extra_args = []
            if python_version:
                extra_args.extend(['--python', python_version])
            
            console.print(f"🐍 Creating environment: {env_name}", style="blue")
            if python_version:
                console.print(f"   Python version: {python_version}", style="blue")
            if packages:
                console.print(f"   Installing packages: {', '.join(packages)}", style="blue")
            
            success = manager.create_venv(env_name, extra_args)
            if success:
                console.print(f"✅ Environment '{env_name}' created successfully!", style="green")
                
                # Install additional packages if specified
                if packages:
                    console.print(f"📦 Installing packages in {env_name}...", style="blue")
                    manager.install_packages(packages)
                    console.print("✅ Packages installed!", style="green")
                
                console.print("\n🚀 To activate:", style="green")
                console.print(f"   ve activate {env_name}", style="bold cyan")
            else:
                console.print(f"❌ Failed to create environment '{env_name}'", style="red")
            return
        elif subcommand == 'list':
            manager.list_venvs_conda_style()
        elif subcommand == 'remove':
            if not cleaned_sub_args or cleaned_sub_args[0] != '-n' or len(cleaned_sub_args) < 2:
                print("❌ Usage: ve env remove -n <name>")
                return
            env_name = cleaned_sub_args[1]
            manager.delete_venv(env_name)
        else:
            print(f"❌ Unknown env subcommand: {subcommand}")
        return
    
    elif command == 'activate':
        # Check for help flags
        needs_help, cleaned_args = check_help_flag(args)
        if needs_help:
            show_command_help('activate')
            return
        
        # Parse --vscode and --auto flags
        vscode_flag = False
        auto_flag = False
        filtered_args = []
        for arg in cleaned_args:
            if arg == '--vscode':
                vscode_flag = True
            elif arg == '--auto':
                auto_flag = True
            else:
                filtered_args.append(arg)
        
        if not filtered_args:
            console.print("❌ Usage: ve activate <name> [--vscode] [--auto]", style="red")
            console.print("💡 Tip: You can also use 'atv <name>' for activation with directory mapping", style="cyan")
            
            # Offer interactive selection if fzf is available
            if has_fzf():
                console.print("🔍 Select environment interactively:", style="yellow")
                selected_env = interactive_env_selection()
                if selected_env:
                    console.print(f"✅ Selected: {selected_env}", style="green")
                    success = manager.activate_venv(selected_env, vscode=vscode_flag, auto=auto_flag)
                    if success:
                        console.print("💡 To activate, run the command shown above", style="cyan")
                    return
            else:
                console.print("📦 Install fzf for interactive selection: https://github.com/junegunn/fzf", style="blue")
                manager.list_venvs_conda_style()
            return
        manager.activate_venv(filtered_args[0], vscode=vscode_flag, auto=auto_flag)
    
    elif command == 'create':
        # Check for help flags first
        needs_help, cleaned_args = check_help_flag(args)
        if needs_help:
            show_command_help('create')
            return
        
        if not cleaned_args:
            console.print("❌ Usage: ve create [-n NAME] [--python VERSION] [packages...]", style="red")
            console.print("💡 Conda-style: ve create -n myenv python=3.11 numpy pandas", style="cyan")
            console.print("💡 Or simple:   ve create myenv --python=3.11", style="cyan")
            return
        
        # Parse conda-style arguments
        env_name = None
        python_version = None
        packages = []
        auto_yes = False
        
        i = 0
        while i < len(cleaned_args):
            arg = cleaned_args[i]
            if arg == '-n' and i + 1 < len(cleaned_args):
                env_name = cleaned_args[i + 1]
                i += 2
            elif arg == '-y':
                auto_yes = True
                i += 1
            elif arg.startswith('--python='):
                python_version = arg.split('=', 1)[1]
                i += 1
            elif arg == 'python' and i + 1 < len(cleaned_args) and cleaned_args[i + 1].startswith('='):
                # Handle "python=3.11" format
                python_version = cleaned_args[i + 1][1:]  # Remove the '='
                i += 2
            elif '=' in arg:
                # Handle package=version format
                if arg.startswith('python='):
                    python_version = arg.split('=', 1)[1]
                else:
                    pkg_spec = arg.split('=', 1)
                    packages.append(pkg_spec[0])
                i += 1
            else:
                if env_name is None:
                    env_name = arg
                else:
                    packages.append(arg)
                i += 1
        
        if not env_name:
            console.print("❌ Environment name is required", style="red")
            console.print("💡 Use: ve create -n myenv", style="cyan")
            return
        
        # Build extra args for venv creation
        extra_args = []
        if python_version:
            extra_args.extend(['--python', python_version])
        if auto_yes:
            extra_args.append('-y')
        
        success = manager.create_venv(env_name, extra_args)
        if success and packages:
            manager.install_packages(packages)
    
    elif command == 'deactivate':
        manager.deactivate_venv()
    
    elif command == 'list':
        manager.list_venvs_conda_style()
    
    elif command in ('delete', 'remove', 'rm'):
        if not args:
            console.print("❌ Usage: ve delete <name>", style="red")
            # Offer interactive selection for deletion
            if has_fzf():
                console.print("🔍 Select environment to delete:", style="yellow")
                selected_env = interactive_env_selection()
                if selected_env:
                    console.print(f"⚠️  Selected for deletion: {selected_env}", style="yellow")
                    if input("Are you sure? (y/N): ").lower() == 'y':
                        manager.delete_venv(selected_env)
                    else:
                        console.print("❌ Cancelled", style="red")
                    return
            manager.list_venvs()
            return
        
        # Check for -y flag
        env_name = args[0]
        auto_yes = '-y' in args
        
        manager.delete_venv(env_name, auto_yes)
    
    elif command == 'info':
        manager.info_venv()
    
    elif command == 'which':
        if not args:
            console.print("❌ Usage: ve which <name>", style="red")
            return
        manager.which_venv(args[0])
    
    elif command == 'install':
        # Check for help flags
        needs_help, cleaned_args = check_help_flag(args)
        if needs_help:
            show_command_help('install')
            return
        
        # Check if this is shell integration install (no packages specified)
        if not cleaned_args:
            # This is 've install' (like 'conda install zsh') - install shell integration
            console.print("🔧 Installing ve shell integration...", style="blue")
            
            # Use os.system to run the standalone installer to avoid import issues
            import os
            from pathlib import Path
            script_path = Path(__file__).parent.parent / "install_shell_integration.py"
            exit_code = os.system(f'python3 "{script_path}"')
            
            if exit_code == 0:
                console.print("✅ Shell integration installed successfully!", style="green")
                console.print("💡 Now you can use 've activate <env>' to properly activate environments", style="cyan")
                return
            else:
                console.print("❌ Failed to install shell integration", style="red")
                return
        else:
            # This is package installation
            manager.install_packages(cleaned_args)
    
    elif command == 'installed':
        manager.list_packages()
    
    elif command == 'uninstall':
        if not args:
            console.print("❌ Usage: ve uninstall <pkg>...", style="red")
            console.print("💡 Example: ve uninstall requests", style="cyan")
            return
        manager.uninstall_packages(args)
    
    elif command == 'search':
        if not args:
            console.print("❌ Usage: ve search <pkg>", style="red")
            console.print("💡 Example: ve search requests", style="cyan")
            return
        manager.search_packages(args[0])
    
    elif command == 'update':
        if not args:
            console.print("❌ Usage: ve update <pkg>...", style="red")
            console.print("💡 Example: ve update requests", style="cyan")
            return
        manager.update_packages(args)
    
    elif command == 'run':
        if not args:
            console.print("❌ Usage: ve run <cmd>...", style="red")
            console.print("💡 Example: ve run python --version", style="cyan")
            return
        manager.run_command(args)
    
    elif command == 'history':
        manager.show_history()
    
    elif command == 'clear-history':
        manager.clear_history()
    
    elif command == 'remove-all-except-base':
        manager.remove_all_except_base()
    
    else:
        console.print(f"Unknown command: {command}", style="red")
        show_help_suggestions(console, command)


if __name__ == '__main__':
    main()