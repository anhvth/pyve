#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["rich"]
# ///

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class VenvManager:
    """Virtual Environment Manager class that provides comprehensive venv management."""
    
    def __init__(self):
        self.home = Path.home()
        self.vex_root = self.home / ".vex"
        self.venvs_dir = self.vex_root / "venvs"
        self.global_env_file = self.vex_root / "venv_all_env"
        self.atv_history_file = self.vex_root / "atv_history"
        self.assoc_file = self.vex_root / "venv_pdirs"
        self.last_venv_file = self.vex_root / "last_venv"
        
        # Ensure directories exist
        self.vex_root.mkdir(exist_ok=True)
        self.venvs_dir.mkdir(exist_ok=True)
        self.atv_history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Rich console for beautiful output
        self.console = Console()

    @staticmethod
    def c_red(text: str) -> str:
        """Return red colored text using Rich markup."""
        return f"[red]{text}[/red]"

    @staticmethod
    def c_green(text: str) -> str:
        """Return green colored text using Rich markup."""
        return f"[green]{text}[/green]"

    @staticmethod
    def c_yellow(text: str) -> str:
        """Return yellow colored text using Rich markup."""
        return f"[yellow]{text}[/yellow]"

    @staticmethod
    def c_blue(text: str) -> str:
        """Return blue colored text using Rich markup."""
        return f"[blue]{text}[/blue]"

    def _run_command(self, cmd: List[str], cwd: Optional[str] = None, 
                    capture_output: bool = False) -> Tuple[int, str, str]:
        """Run a shell command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd, 
                capture_output=capture_output, 
                text=True,
                check=False
            )
            return result.returncode, result.stdout or "", result.stderr or ""
        except FileNotFoundError:
            return 1, "", f"Command not found: {cmd[0]}"

    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in PATH."""
        return shutil.which(name)

    def _is_valid_name(self, name: str) -> bool:
        """Check if environment name is valid."""
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))

    def _get_user_input(self, prompt: str) -> str:
        """Get user input with prompt."""
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    def _confirm_action(self, prompt: str) -> bool:
        """Ask user for confirmation."""
        response = self._get_user_input(f"{prompt} [y/N] ")
        return response.lower() in ('y', 'yes')

    def _update_global_tracking(self, env_name: str, activate_script: str):
        """Update the global environment tracking file."""
        self.global_env_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing entry for this environment name
        if self.global_env_file.exists():
            lines = self.global_env_file.read_text().splitlines()
            lines = [line for line in lines if not line.startswith(f"{env_name} ")]
        else:
            lines = []
        
        # Add new entry
        lines.append(f"{env_name} {activate_script}")
        self.global_env_file.write_text("\n".join(lines) + "\n")

    def _remove_from_global_tracking(self, env_name: str):
        """Remove environment from global tracking."""
        if self.global_env_file.exists():
            lines = self.global_env_file.read_text().splitlines()
            lines = [line for line in lines if not line.startswith(f"{env_name} ")]
            self.global_env_file.write_text("\n".join(lines) + "\n")

    def _get_env_from_tracking(self, env_name: str) -> Optional[str]:
        """Get activate script path from global tracking."""
        if not self.global_env_file.exists():
            return None
        
        for line in self.global_env_file.read_text().splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) == 2 and parts[0] == env_name:
                return parts[1]
        return None

    def _update_directory_mapping(self, env_name: str):
        """Update directory to environment mapping."""
        current_dir = str(Path.cwd())
        
        # Update new format (atv_history)
        if self.atv_history_file.exists():
            lines = self.atv_history_file.read_text().splitlines()
            lines = [line for line in lines if not line.startswith(f"{current_dir}:")]
        else:
            lines = []
        
        lines.append(f"{current_dir}:{env_name}")
        self.atv_history_file.write_text("\n".join(lines) + "\n")
        
        # Update old format for backward compatibility
        if self.assoc_file.exists():
            lines = self.assoc_file.read_text().splitlines()
            lines = [line for line in lines if not line.startswith(f"{current_dir}:")]
        else:
            lines = []
        
        lines.append(f"{current_dir}:{env_name}")
        self.assoc_file.write_text("\n".join(lines) + "\n")

    def _get_current_venv(self) -> Optional[str]:
        """Get currently active virtual environment path."""
        return os.environ.get('VIRTUAL_ENV')

    def _set_last_venv(self, env_name: str):
        """Set the last used virtual environment."""
        self.last_venv_file.write_text(env_name)

    def _update_vscode_settings(self, python_path: str):
        """Update .vscode/settings.json with Python interpreter settings."""
        try:
            import json5
        except ImportError:
            self.console.print(self.c_red("json5 not installed. Install with: pip install json5"))
            return False
            
        vscode_dir = Path.cwd() / ".vscode"
        settings_file = vscode_dir / "settings.json"
        
        # Create .vscode directory if it doesn't exist
        vscode_dir.mkdir(exist_ok=True)
        
        # Load existing settings or create empty dict
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json5.load(f)
            except Exception as e:
                self.console.print(self.c_yellow(f"Warning: Could not parse existing settings.json: {e}"))
                settings = {}
        else:
            settings = {}
        
        # Update Python settings
        settings["python.terminal.activateEnvironment"] = False
        settings["python.terminal.activateEnvInCurrentTerminal"] = False
        settings["python.defaultInterpreterPath"] = python_path
        
        # Write back to file
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json5.dump(settings, f, indent=2)
            self.console.print(self.c_green(f"Updated .vscode/settings.json with Python interpreter: {python_path}"))
            return True
        except Exception as e:
            self.console.print(self.c_red(f"Failed to update .vscode/settings.json: {e}"))
            return False

    def _detect_shell_and_config(self) -> Tuple[str, Path]:
        """Detect shell type and return appropriate config file path."""
        # Check for fish-specific environment variables first (most reliable)
        if os.environ.get('FISH_VERSION'):
            config_file = Path.home() / '.config' / 'fish' / 'config.fish'
            return 'fish', config_file
        
        # Use fish_pid to detect if we're in fish shell
        fish_pid = os.environ.get('fish_pid')
        if fish_pid:
            try:
                import subprocess
                result = subprocess.run(['ps', '-p', fish_pid, '-o', 'comm='], 
                                      capture_output=True, text=True, check=True)
                if 'fish' in result.stdout.strip():
                    config_file = Path.home() / '.config' / 'fish' / 'config.fish'
                    return 'fish', config_file
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        # Check SHELL environment variable
        shell = os.environ.get('SHELL', '')
        if 'fish' in shell:
            config_file = Path.home() / '.config' / 'fish' / 'config.fish'
            return 'fish', config_file
        elif 'zsh' in shell:
            config_file = Path.home() / '.zshrc'
            return 'zsh', config_file
        elif 'bash' in shell:
            config_file = Path.home() / '.bashrc'
            return 'bash', config_file
        else:
            # Default to bash
            config_file = Path.home() / '.bashrc'
            return 'bash', config_file

    def _get_auto_activate_command(self, env_name: str) -> str:
        """Generate the auto-activation command for the shell config."""
        # Get the actual activation script path for the environment
        activate_script = self._get_env_from_tracking(env_name)
        if activate_script and Path(activate_script).exists():
            return f"source {activate_script}"
        else:
            # Fallback to the standard pattern if not found in tracking
            activate_script = self.venvs_dir / env_name / "bin" / "activate"
            return f"source {activate_script}"

    def _update_shell_auto_activation(self, env_name: str) -> bool:
        """Update shell config file with auto-activation command."""
        shell, config_file = self._detect_shell_and_config()
        
        if not config_file.exists():
            self.console.print(self.c_yellow(f"Shell config file not found: {config_file}"))
            return False
        
        try:
            # Read current config
            content = config_file.read_text()
            lines = content.splitlines()
            
            # Check for existing auto-activation commands (both ve activate and source commands)
            ve_activate_pattern = re.compile(r'^ve activate \w+')
            source_activate_pattern = re.compile(r'^source .*/bin/activate')
            new_command = self._get_auto_activate_command(env_name)
            
            # Remove existing auto-activation commands
            updated_lines = []
            found_existing = False
            for line in lines:
                line_stripped = line.strip()
                if (ve_activate_pattern.match(line_stripped) or 
                    source_activate_pattern.match(line_stripped)):
                    found_existing = True
                    self.console.print(self.c_blue(f"Found existing auto-activation: {line_stripped}"))
                else:
                    updated_lines.append(line)
            
            # Add new auto-activation command at the end
            updated_lines.append(f"\n# Auto-activate virtual environment: {env_name}")
            updated_lines.append(new_command)
            
            # Write back to file
            config_file.write_text('\n'.join(updated_lines) + '\n')
            
            if found_existing:
                self.console.print(self.c_green(f"Updated auto-activation in {config_file.name}: {new_command}"))
            else:
                self.console.print(self.c_green(f"Added auto-activation to {config_file.name}: {new_command}"))
            
            self.console.print(self.c_blue(f"💡 Run 'source {config_file}' or restart your shell to apply changes"))
            return True
            
        except Exception as e:
            self.console.print(self.c_red(f"Failed to update shell config: {e}"))
            return False

    def install_uv(self) -> bool:
        """Install uv package manager if not already installed."""
        if self._find_executable("uv"):
            self.console.print("uv is already installed")
            return True

        self.console.print("Installing uv...")
        try:
            # Download and run the installer
            import urllib.request
            with urllib.request.urlopen("https://astral.sh/uv/install.sh") as response:
                install_script = response.read().decode('utf-8')
            
            # Run the install script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write(install_script)
                f.flush()
                
                returncode, stdout, stderr = self._run_command(["sh", f.name])
                os.unlink(f.name)
                
                if returncode == 0:
                    # Check if uv is now available
                    if self._find_executable("uv"):
                        self.console.print("uv installed successfully!")
                        return True
                    else:
                        self.console.print("uv installation failed")
                        return False
                else:
                    self.console.print("uv installation failed")
                    return False
        except Exception:
            self.console.print("uv installation failed")
            return False

    def create_venv(self, env_name: str, extra_args: Optional[List[str]] = None) -> bool:
        """Create a new virtual environment."""
        if extra_args is None:
            extra_args = []
            
        auto_yes = "-y" in extra_args
        extra_args = [arg for arg in extra_args if arg != "-y"]
            
        if not env_name:
            self.console.print("Usage: create <name> [--python=3.12]", style="red")
            return False
            
        if not self._is_valid_name(env_name):
            self.console.print(f"Invalid name: {env_name}", style="red")
            return False

        venv_path = self.venvs_dir / env_name

        # Check if venv already exists in ~/.vex/venvs
        if venv_path.exists():
            if not auto_yes and not self._confirm_action(f"Overwrite {venv_path}?"):
                return False
            shutil.rmtree(venv_path)

        # Check if environment name already exists in global tracking
        existing_path = self._get_env_from_tracking(env_name)
        if existing_path:
            if not auto_yes and not self._confirm_action(f"Overwrite tracking for '{env_name}'?"):
                return False
            self._remove_from_global_tracking(env_name)

        # Try uv first
        uv_path = self._find_executable("uv")
        if uv_path:
            cmd = [uv_path, "venv"] + extra_args + [str(venv_path)]
            returncode, stdout, stderr = self._run_command(cmd, capture_output=True)
            
            if returncode == 0:
                activate_script = venv_path / "bin" / "activate"
                self._update_global_tracking(env_name, str(activate_script))
                self.console.print(f"✅ Created venv: {env_name}")
                
                # Install base requirements
                self._install_base_requirements(venv_path)
                
                return True

        # Try python3
        py3_path = self._find_executable("python3")
        if py3_path:
            cmd = [py3_path, "-m", "venv", str(venv_path)]
            returncode, stdout, stderr = self._run_command(cmd, capture_output=True)
            
            if returncode == 0:
                activate_script = venv_path / "bin" / "activate"
                self._update_global_tracking(env_name, str(activate_script))
                self.console.print(f"✅ Created venv: {env_name}")
                
                # Install base requirements
                self._install_base_requirements(venv_path)
                
                return True

        # Try python
        py_path = self._find_executable("python")
        if py_path:
            cmd = [py_path, "-m", "venv", str(venv_path)]
            returncode, stdout, stderr = self._run_command(cmd, capture_output=True)
            
            if returncode == 0:
                activate_script = venv_path / "bin" / "activate"
                self._update_global_tracking(env_name, str(activate_script))
                self.console.print(f"✅ Created venv: {env_name}")
                
                # Install base requirements
                self._install_base_requirements(venv_path)
                
                return True

        self.console.print("Failed to create venv", style="red")
        return False

    def _install_base_requirements(self, venv_path: Path) -> None:
        """Install base requirements from base_reqs.txt into the new virtual environment."""
        base_reqs_file = Path(__file__).parent.parent / "base_reqs.txt"
        if not base_reqs_file.exists():
            return
        
        try:
            with open(base_reqs_file, 'r') as f:
                packages = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
            if not packages:
                return
            
            # Try pip from the new venv first
            pip_path = venv_path / "bin" / "pip"
            if pip_path.exists():
                cmd = [str(pip_path), "install"] + packages
                returncode, stdout, stderr = self._run_command(cmd, capture_output=True)
                if returncode == 0:
                    self.console.print(f"✅ Installed base requirements: {' '.join(packages)}")
                    return
            
            # Try uv pip as fallback
            if self._find_executable("uv"):
                cmd = ["uv", "pip", "install", "--python", str(venv_path / "bin" / "python")] + packages
                returncode, stdout, stderr = self._run_command(cmd, capture_output=True)
                if returncode == 0:
                    self.console.print(f"✅ Installed base requirements: {' '.join(packages)}")
                    return
            
            self.console.print("⚠️  Failed to install base requirements - no pip or uv found", style="yellow")
                
        except Exception as e:
            self.console.print(f"⚠️  Error installing base requirements: {e}", style="yellow")

    def activate_venv(self, name: str, vscode: bool = False, auto: bool = False) -> bool:
        """Activate a virtual environment."""
        if not name:
            self.console.print("Usage: activate <name|path>", style="red")
            self.list_venvs()
            return False

        activate_script = None
        venv_path = None

        # First check if it's a direct path to venv or activate script
        path_obj = Path(name)
        if path_obj.is_dir() and (path_obj / "bin" / "activate").exists():
            venv_path = path_obj.resolve()
            activate_script = venv_path / "bin" / "activate"
        elif path_obj.is_file():
            activate_script = path_obj.resolve()
            venv_path = activate_script.parent.parent
        else:
            # Look up in global tracking file
            tracked_activate = self._get_env_from_tracking(name)
            if tracked_activate and Path(tracked_activate).exists():
                activate_script = Path(tracked_activate)
                venv_path = activate_script.parent.parent
            else:
                # Try ~/.vex/venvs/<name>
                fallback_path = self.venvs_dir / name
                fallback_activate = fallback_path / "bin" / "activate"
                if fallback_path.is_dir() and fallback_activate.exists():
                    venv_path = fallback_path
                    activate_script = fallback_activate
                else:
                    self.console.print(f"Environment '{name}' not found in global tracking or ~/.vex/venvs/{name}", style="red")
                    self.list_venvs()
                    return False

        if not activate_script or not activate_script.exists():
            self.console.print(f"No activate script: {activate_script}", style="red")
            return False

        # Update tracking files
        self._set_last_venv(name)
        self._update_directory_mapping(name)
        
        # Update VS Code settings if requested
        if vscode:
            python_path = venv_path / "bin" / "python"
            if python_path.exists():
                self._update_vscode_settings(str(python_path))
        
        # Update shell auto-activation if requested
        if auto:
            self._update_shell_auto_activation(name)
        
        # Output activation information for shell function to parse
        # This line is parsed by the shell function to get the activation script path
        self.console.print(f"source {activate_script}", style="blue")
        
        return True

    def deactivate_venv(self) -> bool:
        """Deactivate current virtual environment."""
        current_venv = self._get_current_venv()
        if current_venv:
            venv_name = Path(current_venv).name
            self.console.print(self.c_blue("To deactivate current environment, run:"))
            self.console.print("  deactivate")
            self.console.print(self.c_yellow(f"Would deactivate: {venv_name}"))
        else:
            self.console.print(self.c_yellow("No venv active"))
        return True

    def list_venvs_conda_style(self) -> bool:
        """List all virtual environments in conda style."""
        from rich.table import Table
        
        if not self.global_env_file.exists():
            table = Table(title="Virtual Environments")
            table.add_column("Status", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("Command", style="green")
            self.console.print(table)
            return True

        if not self.global_env_file.stat().st_size:
            table = Table(title="Virtual Environments")
            table.add_column("Status", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("Command", style="green")
            self.console.print(table)
            return True

        table = Table(title="Virtual Environments")
        table.add_column("Status", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Command", style="green")
        
        current_venv = self._get_current_venv()
        count = 0
        valid_lines = []
        original_lines = self.global_env_file.read_text().splitlines()

        for line in original_lines:
            parts = line.strip().split(" ", 1)
            if len(parts) != 2:
                continue
            
            env_name, activate_path = parts
            venv_path = Path(activate_path).parent.parent

            # Check if environment still exists
            if Path(activate_path).exists():
                marker = "*" if current_venv and Path(current_venv) == venv_path else " "
                status = "[bold green]*[/bold green]" if marker == "*" else " "
                table.add_row(status, env_name, f"ve activate {env_name}")
                count += 1
                valid_lines.append(line)
            else:
                table.add_row("[dim red]missing[/dim red]", env_name, f"[dim]ve activate {venv_path}[/dim]")

        # Remove missing environments from global tracking
        if len(valid_lines) < len(original_lines):
            self.global_env_file.write_text("\n".join(valid_lines) + "\n")
            removed_count = len(original_lines) - len(valid_lines)
            self.console.print(f"[dim]Cleaned up {removed_count} missing environment(s) from tracking[/dim]")

        self.console.print(table)
        
        if count == 0:
            self.console.print("[dim](no environments)[/dim]")
        return True

    def list_venvs(self) -> bool:
        """List all virtual environments."""
        if not self.global_env_file.exists():
            self.console.print(self.c_yellow(f"No global environment tracking file found: {self.global_env_file}"))
            return True

        if not self.global_env_file.stat().st_size:
            self.console.print(self.c_yellow(f"No virtual environments tracked in {self.global_env_file}"))
            return True

        self.console.print(self.c_blue("Tracked virtual environments:"))
        count = 0
        current_venv = self._get_current_venv()
        valid_lines = []
        original_lines = self.global_env_file.read_text().splitlines()

        for line in original_lines:
            parts = line.strip().split(" ", 1)
            if len(parts) != 2:
                continue
            
            env_name, activate_path = parts
            venv_path = Path(activate_path).parent.parent

            # Check if environment still exists
            if Path(activate_path).exists():
                if current_venv and Path(current_venv) == venv_path:
                    self.console.print(self.c_green(f"* {env_name} (active) - {venv_path}"))
                else:
                    self.console.print(f"  {env_name} - {venv_path}")
                count += 1
                valid_lines.append(line)
            else:
                self.console.print(self.c_yellow(f"  {env_name} - {venv_path} (missing)"))

        # Remove missing environments from global tracking
        if len(valid_lines) < len(original_lines):
            self.global_env_file.write_text("\n".join(valid_lines) + "\n")
            removed_count = len(original_lines) - len(valid_lines)
            self.console.print(self.c_blue(f"Cleaned up {removed_count} missing environment(s) from tracking"))

        if count == 0:
            self.console.print(self.c_yellow("No valid virtual environments found"))
        return True

    def delete_venv(self, env_name: str, auto_yes: bool = False) -> bool:
        """Delete a virtual environment."""
        if not env_name:
            self.console.print(self.c_red("Usage: delete <name>"))
            self.list_venvs()
            return False

        # Find the environment in global tracking
        activate_path = self._get_env_from_tracking(env_name)
        if not activate_path:
            self.console.print(self.c_red(f"Environment '{env_name}' not found in global tracking"))
            self.list_venvs()
            return False

        venv_path = Path(activate_path).parent.parent
        current_venv = self._get_current_venv()

        if current_venv and Path(current_venv) == venv_path:
            self.console.print(self.c_red(f"Cannot delete active venv: {env_name}"))
            return False

        # Safety checks
        if not venv_path or venv_path == Path("/") or venv_path == Path.home():
            self.console.print(self.c_red(f"Refusing to delete unsafe path: '{venv_path}'"))
            return False

        if not venv_path.is_dir() or not Path(activate_path).exists():
            self.console.print(self.c_red(f"Refusing to delete: '{venv_path}' is not a valid venv directory"))
            return False

        if not auto_yes and not self._confirm_action(f"Delete {env_name} at {venv_path}?"):
            return False

        try:
            shutil.rmtree(venv_path)
            self._remove_from_global_tracking(env_name)
            self.console.print(self.c_green(f"Deleted: {env_name}"))
            return True
        except Exception as e:
            self.console.print(self.c_red(f"Failed to delete: {env_name} - {e}"))
            return False

    def info_venv(self) -> bool:
        """Show current virtual environment info."""
        from rich.panel import Panel
        
        current_venv = self._get_current_venv()
        python_path = self._find_executable("python")
        
        try:
            returncode, python_version, _ = self._run_command(
                ["python", "--version"], capture_output=True
            )
            if returncode != 0:
                python_version = "Unknown"
            else:
                python_version = python_version.strip()
        except Exception:
            python_version = "Unknown"

        if current_venv:
            venv_path = Path(current_venv)
            if python_path and python_path.startswith(str(venv_path)):
                info = f"[green]🟢 Active:[/green] {venv_path.name}\n"
                info += f"[blue]📁[/blue] {current_venv}\n"
                info += f"[blue]🐍[/blue] {python_path}\n"
                info += f"[blue]🔢[/blue] {python_version}"
                panel = Panel(info, title="[bold blue]Virtual Environment Status[/bold blue]", border_style="blue")
                self.console.print(panel)
            else:
                info = "[yellow]🟡 VIRTUAL_ENV is set, but Python is not from venv![/yellow]\n"
                info += f"[blue]📁[/blue] {current_venv}\n"
                info += f"[blue]🐍[/blue] {python_path}\n"
                info += f"[blue]🔢[/blue] {python_version}"
                panel = Panel(info, title="[bold yellow]Virtual Environment Status[/bold yellow]", border_style="yellow")
                self.console.print(panel)
        else:
            if python_path and ("venv" in python_path or "env" in python_path):
                info = "[yellow]🟡 Python is from a venv, but VIRTUAL_ENV is not set![/yellow]\n"
                info += f"[blue]🐍[/blue] {python_path}\n"
                info += f"[blue]🔢[/blue] {python_version}"
                panel = Panel(info, title="[bold yellow]Virtual Environment Status[/bold yellow]", border_style="yellow")
                self.console.print(panel)
            else:
                info = "[red]🔴 No venv active.[/red]\n"
                info += f"[blue]🐍[/blue] {python_path}\n"
                info += f"[blue]🔢[/blue] {python_version}"
                panel = Panel(info, title="[bold red]Virtual Environment Status[/bold red]", border_style="red")
                self.console.print(panel)
                self.list_venvs()
        return True

    def which_venv(self, env_name: str) -> bool:
        """Show path to virtual environment."""
        if not env_name:
            self.console.print(self.c_red("Usage: which <name>"))
            return False

        activate_path = self._get_env_from_tracking(env_name)
        if activate_path and Path(activate_path).exists():
            venv_path = Path(activate_path).parent.parent
            self.console.print(self.c_blue(f"Would activate: {venv_path}"))
            return True
        else:
            self.console.print(self.c_red(f"Environment '{env_name}' not found in global tracking"))
            return False

    def install_packages(self, packages: List[str]) -> bool:
        """Install packages in active virtual environment."""
        current_venv = self._get_current_venv()
        if not current_venv:
            self.console.print("No venv active", style="red")
            return False

        if not packages:
            self.console.print("Usage: install <pkg>...", style="red")
            return False

        # Try uv first
        if self._find_executable("uv"):
            cmd = ["uv", "pip", "install"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(f"Installed: {' '.join(packages)}")
                return True

        # Try pip
        if self._find_executable("pip"):
            cmd = ["pip", "install"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(f"Installed: {' '.join(packages)}")
                return True

        self.console.print("No uv or pip found in venv", style="red")
        return False

    def list_packages(self) -> bool:
        """List installed packages in active virtual environment."""
        current_venv = self._get_current_venv()
        if not current_venv:
            self.console.print(self.c_red("No venv active"))
            return False

        # Try uv first
        if self._find_executable("uv"):
            returncode, stdout, stderr = self._run_command(["uv", "pip", "list"])
            if returncode == 0:
                self.console.print(stdout)
                return True

        # Try pip
        if self._find_executable("pip"):
            returncode, stdout, stderr = self._run_command(["pip", "list"])
            if returncode == 0:
                self.console.print(stdout)
                return True

        self.console.print(self.c_red("No uv or pip found in venv"))
        return False

    def uninstall_packages(self, packages: List[str]) -> bool:
        """Uninstall packages from active virtual environment."""
        current_venv = self._get_current_venv()
        if not current_venv:
            self.console.print(self.c_red("No venv active"))
            return False

        if not packages:
            self.console.print(self.c_red("Usage: uninstall <pkg>..."))
            return False

        # Try uv first
        if self._find_executable("uv"):
            cmd = ["uv", "pip", "uninstall"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(f"Uninstalled: {' '.join(packages)}")
                return True

        # Try pip
        if self._find_executable("pip"):
            cmd = ["pip", "uninstall", "-y"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(f"Uninstalled: {' '.join(packages)}")
                return True

        self.console.print(self.c_red("No uv or pip found in venv"))
        return False

    def search_packages(self, package: str) -> bool:
        """Search for packages on PyPI."""
        if not package:
            self.console.print(self.c_red("Usage: search <pkg>"))
            return False

        self.console.print(self.c_blue(f"Opening PyPI search for '{package}' in browser..."))
        
        try:
            import webbrowser
            url = f"https://pypi.org/search/?q={package}"
            webbrowser.open(url)
            return True
        except Exception:
            self.console.print(self.c_yellow("Cannot open browser automatically. Please visit:"))
            self.console.print(self.c_blue(f"https://pypi.org/search/?q={package}"))
            return True

    def update_packages(self, packages: List[str]) -> bool:
        """Update packages in active virtual environment."""
        current_venv = self._get_current_venv()
        if not current_venv:
            self.console.print(self.c_red("No venv active"))
            return False

        if not packages:
            self.console.print(self.c_red("Usage: update <pkg>..."))
            return False

        # Try uv first
        if self._find_executable("uv"):
            cmd = ["uv", "pip", "install", "-U"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(f"Updated: {' '.join(packages)}")
                return True

        # Try pip
        if self._find_executable("pip"):
            cmd = ["pip", "install", "-U"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(f"Updated: {' '.join(packages)}")
                return True

        self.console.print(self.c_red("No uv or pip found in venv"))
        return False

    def run_command(self, command: List[str]) -> bool:
        """Run command in active virtual environment."""
        current_venv = self._get_current_venv()
        if not current_venv:
            self.console.print(self.c_red("No venv active"))
            return False

        if not command:
            self.console.print(self.c_red("Usage: run <cmd>..."))
            return False

        returncode, stdout, stderr = self._run_command(command)
        
        if returncode == 0:
            self.console.print(f"Ran: {' '.join(command)}")
        else:
            self.console.print(f"Failed: {' '.join(command)}")
        
        return returncode == 0

    def show_history(self) -> bool:
        """Show directory -> environment mappings."""
        if not self.atv_history_file.exists():
            self.console.print(self.c_yellow(f"No atv history file found: {self.atv_history_file}"))
            return True

        if not self.atv_history_file.stat().st_size:
            self.console.print(self.c_yellow("atv history is empty"))
            return True

        self.console.print(self.c_blue("Directory -> Environment mappings:"))
        current_dir = str(Path.cwd())
        
        for line in self.atv_history_file.read_text().splitlines():
            if ":" in line:
                dir_path, env_name = line.split(":", 1)
                if dir_path == current_dir:
                    self.console.print(self.c_green(f"* {dir_path} -> {env_name} (current)"))
                else:
                    self.console.print(f"  {dir_path} -> {env_name}")
        return True

    def clear_history(self) -> bool:
        """Clear atv history."""
        if self.atv_history_file.exists():
            self.atv_history_file.unlink()
            self.console.print(self.c_green("Cleared atv history"))
        else:
            self.console.print(self.c_yellow("No atv history file to clear"))
        return True

    def remove_all_except_base(self) -> bool:
        """Remove all environments except 'base'."""
        if not self.global_env_file.exists():
            self.console.print(self.c_yellow("No global environment tracking file found"))
            return True

        envs_to_delete = []
        for line in self.global_env_file.read_text().splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                env_name, activate_path = parts
                if env_name != "base":
                    envs_to_delete.append(env_name)

        if not envs_to_delete:
            self.console.print(self.c_yellow("No environments to delete (only 'base' environments are preserved)"))
            return True

        self.console.print(self.c_blue(f"Will delete {len(envs_to_delete)} environments (preserving 'base'):"))
        for env in envs_to_delete:
            self.console.print(f"  {env}")

        if not self._confirm_action("Continue?"):
            self.console.print(self.c_yellow("Cancelled"))
            return False

        for env in envs_to_delete:
            self.delete_venv(env)
        return True

    def auto_activate_for_directory(self, directory: Optional[str] = None) -> bool:
        """Auto-activate environment for a directory."""
        if directory is None:
            directory = str(Path.cwd())

        current_venv_name = ""
        current_venv = self._get_current_venv()
        if current_venv:
            current_venv_name = Path(current_venv).name

        # Check if there's a known environment for the directory
        if self.atv_history_file.exists():
            for line in self.atv_history_file.read_text().splitlines():
                if ":" in line:
                    dir_path, env_name = line.split(":", 1)
                    if dir_path == directory:
                        # Check if we need to switch environments
                        if current_venv_name != env_name:
                            activate_path = self._get_env_from_tracking(env_name)
                            if activate_path and Path(activate_path).exists():
                                self.console.print(self.c_green(f"[auto] Would switch to venv for {directory}: {env_name}"))
                                self.console.print(self.c_blue(f"Run: source {activate_path}"))
                                return True
                            else:
                                self.console.print(self.c_yellow(f"[auto] Venv not found in global tracking for {env_name} (removing from history)"))
                                # Remove the invalid entry
                                lines = self.atv_history_file.read_text().splitlines()
                                lines = [line for line in lines if not line.startswith(f"{directory}:")]
                                self.atv_history_file.write_text("\n".join(lines) + "\n")
        return True

    def get_auto_activate_env(self, directory: Optional[str] = None) -> Optional[str]:
        """Get environment name that should be auto-activated for a directory."""
        if directory is None:
            directory = str(Path.cwd())

        if self.atv_history_file.exists():
            for line in self.atv_history_file.read_text().splitlines():
                if ":" in line:
                    dir_path, env_name = line.split(":", 1)
                    if dir_path == directory:
                        # Verify environment still exists
                        activate_path = self._get_env_from_tracking(env_name)
                        if activate_path and Path(activate_path).exists():
                            return env_name
        return None

    def install_shell_integration(self) -> bool:
        """Install shell integration for ve commands (similar to conda install zsh)."""
        shell, config_file = self._detect_shell_and_config()
        
        # Determine which shell integration script to use
        if 'zsh' in shell:
            integration_script = Path(__file__).parent / "shell_integration_zsh.sh"
            target_filename = "shell_integration_zsh.sh"
        elif 'fish' in shell:
            integration_script = Path(__file__).parent / "shell_integration_fish.fish"
            target_filename = "shell_integration_fish.fish"
        else:
            integration_script = Path(__file__).parent / "shell_integration_bash.sh"
            target_filename = "shell_integration_bash.sh"
        
        if not integration_script.exists():
            self.console.print(f"Shell integration script not found: {integration_script}")
            return False
        
        # Create the pyve config directory
        pyve_config_dir = Path.home() / '.config' / 'pyve'
        pyve_config_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the shell integration file to the config directory
        target_script = pyve_config_dir / target_filename
        try:
            import shutil
            shutil.copy2(integration_script, target_script)
            self.console.print(f"Copied shell integration to: {target_script}")
        except Exception as e:
            self.console.print(f"Failed to copy integration script: {e}")
            return False
        
        # Check if shell config file exists, create if not
        if not config_file.exists():
            try:
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.touch()
            except Exception as e:
                self.console.print(f"Failed to create config file: {e}")
                return False
        
        # Read current config content
        try:
            current_content = config_file.read_text()
        except Exception as e:
            self.console.print(f"Failed to read config file: {e}")
            return False
        
        # Create the source line
        ve_marker = "# Virtual Environment Manager (ve) Integration"
        source_line = f"source {target_script}"
        
        # Check if ve integration is already installed
        has_ve_function = "ve()" in current_content or "function ve()" in current_content or "function ve" in current_content
        has_source_line = source_line in current_content
        has_marker = ve_marker in current_content
        
        if has_source_line or has_marker:
            self.console.print("ve shell integration already installed")
            return True
        elif has_ve_function:
            self.console.print("ve() function already exists (not installed by pyve)")
            return True
        
        # Add the source line to the config file
        new_content = current_content.rstrip() + "\n\n" + ve_marker + "\n" + source_line + "\n"
        
        try:
            config_file.write_text(new_content)
            self.console.print("ve shell integration installed")
            return True
        except Exception:
            self.console.print("Failed to install shell integration")
            return False

    def help_text(self) -> str:
        """Return help text for the ve command."""
        return """Virtual Environment Management (ve) - Unified Command Interface

Environment Management:
  ve create <name> [options]    Create a new virtual environment
  ve activate <name>            Activate a virtual environment  
  ve deactivate                 Deactivate current virtual environment
  ve list                       List all virtual environments
  ve delete <name>              Delete a virtual environment
  ve info                       Show current virtual environment info

Conda-style Commands:
  ve env create -n <name> [python=VERSION] [packages...]  Create environment (conda-style)
  ve env list                   List environments (conda-style)
  ve env remove -n <name>      Remove environment (conda-style)

Package Management:
  ve install <pkg>...          Install packages in active venv
  ve installed                 List installed packages in active venv
  ve uninstall <pkg>...        Uninstall packages from active venv
  ve search <pkg>              Search for packages on PyPI
  ve update <pkg>...           Update packages in active venv

Utilities:
  ve which <name>              Show path to virtual environment
  ve run <cmd>...              Run command in active venv
  ve history                   Show directory -> environment mappings
  ve clear-history             Clear all directory mappings
  ve help                      Show this help

Directory Auto-Activation:
  When you activate an environment with 've activate <name>', the current directory
  is mapped to that environment. When you 'cd' to that directory later,
  the environment will be automatically suggested for activation.

Examples:
  ve create myproject --python=3.12
  cd /path/to/myproject
  ve activate myproject        # Creates directory mapping
  cd elsewhere
  cd /path/to/myproject        # Auto-suggests myproject activation
  ve history                   # Show all directory mappings
"""


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
                if manager._find_executable("python") and str(manager._find_executable("python")).startswith(str(manager.venvs_dir / env_name)):
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