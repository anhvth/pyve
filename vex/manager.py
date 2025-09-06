"""
Core virtual environment management functionality.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from rich.console import Console


class VenvManager:
    """Virtual Environment Manager class that provides comprehensive venv management."""
    
    def __init__(self):
        self.home = Path.home()
        self.venvs_dir = self.home / ".venvs"
        self.global_env_file = self.home / ".venv_all_env"
        self.atv_history_file = self.home / ".config" / "atv_history"
        self.assoc_file = self.home / ".venv_pdirs"
        self.last_venv_file = self.home / ".last_venv"
        
        # Ensure directories exist
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
        shell = os.environ.get('SHELL', '')
        if 'zsh' in shell:
            config_file = Path.home() / '.zshrc'
        else:
            # Default to bash
            config_file = Path.home() / '.bashrc'
        return shell, config_file

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
            returncode, stdout, stderr = self._run_command(["uv", "--version"], capture_output=True)
            if returncode == 0:
                self.console.print(stdout.strip())
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
                        returncode, stdout, stderr = self._run_command(["uv", "--version"], capture_output=True)
                        if returncode == 0:
                            self.console.print(stdout.strip())
                        return True
                    else:
                        self.console.print("uv installation completed, but command not found in PATH.")
                        self.console.print("You may need to restart your shell or run: source ~/.zshrc")
                        self.console.print("uv is typically installed to ~/.cargo/bin/uv")
                        return False
                else:
                    self.console.print(f"uv installation failed: {stderr}")
                    return False
        except Exception as e:
            self.console.print(f"Error installing uv: {e}")
            return False

    def create_venv(self, env_name: str, extra_args: Optional[List[str]] = None) -> bool:
        """Create a new virtual environment."""
        if extra_args is None:
            extra_args = []
            
        if not env_name:
            self.console.print("Usage: create <name> [--python=3.12]", style="red")
            return False
            
        if not self._is_valid_name(env_name):
            self.console.print(f"Invalid name: {env_name}", style="red")
            return False

        venv_path = self.venvs_dir / env_name

        # Check if venv already exists in ~/.venvs
        if venv_path.exists():
            self.console.print(f"Virtual environment already exists: {venv_path}", style="yellow")
            if not self._confirm_action(f"Overwrite {venv_path}?"):
                self.console.print("Cancelled. Not overwriting.", style="yellow")
                return False
            shutil.rmtree(venv_path)

        # Check if environment name already exists in global tracking
        existing_path = self._get_env_from_tracking(env_name)
        if existing_path:
            existing_venv_dir = Path(existing_path).parent.parent
            self.console.print(f"Environment name '{env_name}' already tracked at: {existing_venv_dir}", style="yellow")
            if not self._confirm_action(f"Overwrite tracking for '{env_name}'?"):
                self.console.print("Cancelled. Environment name already in use.", style="yellow")
                return False
            self._remove_from_global_tracking(env_name)

        self.console.print(f"Creating venv: {env_name} at {venv_path} {' '.join(extra_args)}", style="blue")

        # Try uv first
        uv_path = self._find_executable("uv")
        if uv_path:
            self.console.print("Found uv, attempting to create venv...", style="blue")
            cmd = [uv_path, "venv"] + extra_args + [str(venv_path)]
            returncode, stdout, stderr = self._run_command(cmd)
            
            if returncode == 0:
                self.console.print(f"Created with uv: {venv_path}", style="green")
                activate_script = venv_path / "bin" / "activate"
                self._update_global_tracking(env_name, str(activate_script))
                self.console.print(f"Registered {env_name} in global tracking", style="blue")
                self.activate_venv(env_name)
                return True
            else:
                self.console.print("uv failed, trying to install Python and retry...", style="yellow")
                install_cmd = [uv_path, "python", "install"]
                returncode, _, _ = self._run_command(install_cmd)
                if returncode == 0:
                    returncode, stdout, stderr = self._run_command(cmd)
                    if returncode == 0:
                        self.console.print(f"Created with uv (after Python install): {venv_path}", style="green")
                        activate_script = venv_path / "bin" / "activate"
                        self._update_global_tracking(env_name, str(activate_script))
                        self.console.print(f"Registered {env_name} in global tracking", style="blue")
                        self.activate_venv(env_name)
                        return True

        # Try python3
        py3_path = self._find_executable("python3")
        if py3_path:
            self.console.print("Found python3, attempting to create venv...", style="blue")
            if extra_args:
                self.console.print(f"Extra args ignored for python3: {' '.join(extra_args)}", style="yellow")
            
            cmd = [py3_path, "-m", "venv", str(venv_path)]
            returncode, stdout, stderr = self._run_command(cmd)
            
            if returncode == 0:
                self.console.print(f"Created with python3: {venv_path}", style="green")
                activate_script = venv_path / "bin" / "activate"
                self._update_global_tracking(env_name, str(activate_script))
                self.console.print(f"Registered {env_name} in global tracking", style="blue")
                self.activate_venv(env_name)
                return True

        # Try python
        py_path = self._find_executable("python")
        if py_path:
            self.console.print("Found python, attempting to create venv...", style="blue")
            if extra_args:
                self.console.print(f"Extra args ignored for python: {' '.join(extra_args)}", style="yellow")
            
            cmd = [py_path, "-m", "venv", str(venv_path)]
            returncode, stdout, stderr = self._run_command(cmd)
            
            if returncode == 0:
                self.console.print(f"Created with python: {venv_path}", style="green")
                activate_script = venv_path / "bin" / "activate"
                self._update_global_tracking(env_name, str(activate_script))
                self.console.print(f"Registered {env_name} in global tracking", style="blue")
                self.activate_venv(env_name)
                return True

        self.console.print("No Python/uv found or all attempts failed. Run install_uv or install Python.", style="red")
        return False

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
                # Try ~/.venvs/<name>
                fallback_path = self.venvs_dir / name
                fallback_activate = fallback_path / "bin" / "activate"
                if fallback_path.is_dir() and fallback_activate.exists():
                    venv_path = fallback_path
                    activate_script = fallback_activate
                else:
                    self.console.print(f"Environment '{name}' not found in global tracking or ~/.venvs/{name}", style="red")
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
            else:
                self.console.print(f"Warning: Python executable not found at {python_path}", style="yellow")
        
        # Update shell auto-activation if requested
        if auto:
            self._update_shell_auto_activation(name)
        
        # Output activation information for shell function to parse
        self.console.print(f"Activating: {venv_path.name}", style="green")
        
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
                table.add_row(status, env_name, f"ve activate {venv_path}")
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

    def delete_venv(self, env_name: str) -> bool:
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

        if not self._confirm_action(f"Delete {env_name} at {venv_path}?"):
            self.console.print(self.c_yellow("Cancelled"))
            return False

        try:
            shutil.rmtree(venv_path)
            self._remove_from_global_tracking(env_name)
            self.console.print(self.c_green(f"Deleted: {env_name} ({venv_path})"))
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
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        current_venv = self._get_current_venv()
        if not current_venv:
            self.console.print("No venv active", style="red")
            return False

        if not packages:
            self.console.print("Usage: install <pkg>...", style="red")
            return False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Installing: {' '.join(packages)}", total=None)

            # Try uv first
            if self._find_executable("uv"):
                cmd = ["uv", "pip", "install"] + packages
                returncode, stdout, stderr = self._run_command(cmd)
                if returncode == 0:
                    progress.update(task, description="[green]Installed with uv[/green]")
                    return True

            # Try pip
            if self._find_executable("pip"):
                cmd = ["pip", "install"] + packages
                returncode, stdout, stderr = self._run_command(cmd)
                if returncode == 0:
                    progress.update(task, description="[green]Installed with pip[/green]")
                    return True

            progress.update(task, description="[red]No uv or pip found in venv[/red]")
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

        self.console.print(self.c_blue(f"Uninstalling: {' '.join(packages)}"))

        # Try uv first
        if self._find_executable("uv"):
            cmd = ["uv", "pip", "uninstall"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(self.c_green("Uninstalled with uv"))
                return True

        # Try pip
        if self._find_executable("pip"):
            cmd = ["pip", "uninstall", "-y"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(self.c_green("Uninstalled with pip"))
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

        self.console.print(self.c_blue(f"Updating: {' '.join(packages)}"))

        # Try uv first
        if self._find_executable("uv"):
            cmd = ["uv", "pip", "install", "-U"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(self.c_green("Updated with uv"))
                return True

        # Try pip
        if self._find_executable("pip"):
            cmd = ["pip", "install", "-U"] + packages
            returncode, stdout, stderr = self._run_command(cmd)
            if returncode == 0:
                self.console.print(self.c_green("Updated with pip"))
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

        self.console.print(self.c_blue(f"Running in venv: {' '.join(command)}"))
        returncode, stdout, stderr = self._run_command(command)
        
        if stdout:
            self.console.print(stdout)
        if stderr:
            self.console.print(stderr)
        
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
            shell_name = "zsh"
        else:
            integration_script = Path(__file__).parent / "shell_integration_bash.sh" 
            shell_name = "bash"
        
        if not integration_script.exists():
            print(f"Shell integration script not found: {integration_script}")
            return False
        
        # Read the integration script content
        try:
            integration_content = integration_script.read_text()
        except Exception as e:
            print(f"Failed to read integration script: {e}")
            return False
        
        # Check if shell config file exists, create if not
        if not config_file.exists():
            print(f"Creating shell config file: {config_file}")
            try:
                config_file.touch()
            except Exception as e:
                print(f"Failed to create config file: {e}")
                return False
        
        # Read current config content
        try:
            current_content = config_file.read_text()
        except Exception as e:
            print(f"Failed to read config file: {e}")
            return False
        
        # Check if ve integration is already installed (either by marker or ve function)
        ve_marker = "# Virtual Environment Manager (ve) Integration"
        has_ve_function = "ve()" in current_content or "function ve()" in current_content
        
        if ve_marker in current_content or has_ve_function:
            if has_ve_function and ve_marker not in current_content:
                print(f"ve() function already exists in {config_file} (not installed by ve)")
                response = input("Remove existing ve() function and reinstall? [y/N] ").strip().lower()
                if response not in ('y', 'yes'):
                    print("Skipping installation to preserve existing ve() function.")
                    return True
            else:
                print(f"ve shell integration already installed in {config_file}")
                response = input("Reinstall shell integration? [y/N] ").strip().lower()
                if response not in ('y', 'yes'):
                    return True
            
            # Remove ALL existing ve integrations (both marked and unmarked)
            lines = current_content.splitlines()
            new_lines = []
            in_ve_integration = False
            in_ve_function = False
            brace_count = 0
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check for ve integration markers
                if (ve_marker in line or 
                    "# Virtual Environment Manager" in line or
                    line.strip().startswith("# This enables proper activation of virtual environments")):
                    in_ve_integration = True
                    i += 1
                    continue
                
                # Check for ve function definitions
                if (("ve()" in line or "function ve()" in line) and 
                    not line.strip().startswith("#")):
                    in_ve_function = True
                    brace_count = 0
                    # Count braces on the same line
                    brace_count += line.count("{") - line.count("}")
                    i += 1
                    continue
                
                # Handle ve function body
                if in_ve_function:
                    brace_count += line.count("{") - line.count("}")
                    if brace_count <= 0:
                        in_ve_function = False
                    i += 1
                    continue
                
                # Handle ve integration sections
                if in_ve_integration:
                    # Look for end of integration (empty line followed by non-comment/non-ve content)
                    if (line.strip() == "" and 
                        i + 1 < len(lines) and 
                        lines[i + 1].strip() != "" and 
                        not lines[i + 1].strip().startswith("#") and
                        "ve()" not in lines[i + 1] and
                        "function ve()" not in lines[i + 1] and
                        "_ve_auto_activate" not in lines[i + 1] and
                        "add-zsh-hook" not in lines[i + 1]):
                        in_ve_integration = False
                        # Don't skip this line, it might be important spacing
                        new_lines.append(line)
                    i += 1
                    continue
                
                # Keep lines that are not part of ve integration
                new_lines.append(line)
                i += 1
            
            current_content = "\n".join(new_lines)
        
        # Add the integration
        new_content = current_content.rstrip() + "\n\n" + ve_marker + "\n" + integration_content + "\n"
        
        try:
            config_file.write_text(new_content)
            print(f"✅ ve shell integration installed to {config_file}")
            print(f"🔄 Run 'source {config_file}' or restart your {shell_name} shell to activate")
            print("💡 After sourcing, you can use 've activate <env>' to properly activate environments")
            return True
        except Exception as e:
            print(f"Failed to write to config file: {e}")
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