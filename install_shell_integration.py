#!/usr/bin/env python3
"""
Standalone shell integration installer for ve command.
This script doesn't depend on rich or other external libraries.
"""

import os
import sys
from pathlib import Path


def get_shell_and_config():
    """Ask user to select their shell and return appropriate config file path."""
    print("Please select your shell:")
    print("1. fish")
    print("2. zsh") 
    print("3. bash")
    
    while True:
        try:
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == '1' or choice.lower() == 'fish':
                config_file = Path.home() / '.config' / 'fish' / 'config.fish'
                return 'fish', config_file
            elif choice == '2' or choice.lower() == 'zsh':
                config_file = Path.home() / '.zshrc'
                return 'zsh', config_file
            elif choice == '3' or choice.lower() == 'bash':
                config_file = Path.home() / '.bashrc'
                return 'bash', config_file
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3 (or fish, zsh, bash)")
        except KeyboardInterrupt:
            print("\n❌ Installation cancelled")
            sys.exit(1)
        except EOFError:
            print("\n❌ Installation cancelled")
            sys.exit(1)


def install_shell_integration():
    """Install shell integration for ve commands."""
    shell_name, config_file = get_shell_and_config()
    
    # Determine which shell integration script to use
    script_dir = Path(__file__).parent / "pyve"
    if shell_name == 'zsh':
        integration_script = script_dir / "shell_integration_zsh.sh"
        target_filename = "shell_integration_zsh.sh"
    elif shell_name == 'fish':
        integration_script = script_dir / "shell_integration_fish.fish"
        target_filename = "shell_integration_fish.fish"
    else:
        integration_script = script_dir / "shell_integration_bash.sh"
        target_filename = "shell_integration_bash.sh"
    
    if not integration_script.exists():
        print(f"❌ Shell integration script not found: {integration_script}")
        return False
    
    # Create the pyve config directory
    pyve_config_dir = Path.home() / '.config' / 'pyve'
    pyve_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy the shell integration file to the config directory
    target_script = pyve_config_dir / target_filename
    try:
        import shutil
        shutil.copy2(integration_script, target_script)
        print(f"📁 Copied shell integration to: {target_script}")
    except Exception as e:
        print(f"❌ Failed to copy integration script: {e}")
        return False
    
    # Check if shell config file exists, create if not
    if not config_file.exists():
        print(f"📝 Creating shell config file: {config_file}")
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.touch()
        except Exception as e:
            print(f"❌ Failed to create config file: {e}")
            return False
    
    # Read current config content
    try:
        current_content = config_file.read_text()
    except Exception as e:
        print(f"❌ Failed to read config file: {e}")
        return False
    
    # Create the source line based on shell type
    ve_marker = "# Virtual Environment Manager (ve) Integration"
    if shell_name == 'fish':
        source_line = f"source {target_script}"
    else:
        source_line = f"source {target_script}"
    
    # Check if ve integration is already sourced
    has_ve_function = ("ve()" in current_content or 
                      "function ve()" in current_content or 
                      "function ve" in current_content)
    has_source_line = source_line in current_content
    has_marker = ve_marker in current_content
    
    if has_source_line or has_marker:
        print(f"⚠️  ve shell integration already installed in {config_file}")
        response = input("Reinstall shell integration? [y/N] ").strip().lower()
        if response not in ('y', 'yes'):
            print("✅ Shell integration installation skipped")
            return True
        
        # Remove existing integration (both old-style concatenated content and source lines)
        lines = current_content.splitlines()
        new_lines = []
        skip_lines = False
        
        for line in lines:
            line_stripped = line.strip()
            if ve_marker in line:
                # Start skipping lines after marker (old-style installation)
                skip_lines = True
            elif skip_lines and (line_stripped == "" or line_stripped == "end"):
                # End of ve integration block (empty line or 'end' for fish functions)
                skip_lines = False
            elif line_stripped == source_line or str(target_script) in line:
                # Skip source lines pointing to our integration file
                continue
            elif not skip_lines:
                new_lines.append(line)
        
        current_content = "\n".join(new_lines)
    elif has_ve_function:
        print(f"⚠️  ve() function already exists in {config_file} (not installed by pyve)")
        print("A custom ve() function is already defined. Skipping installation.")
        return True
    
    # Add the source line to the config file
    new_content = current_content.rstrip() + "\n\n" + ve_marker + "\n" + source_line + "\n"
    
    try:
        config_file.write_text(new_content)
        print(f"✅ ve shell integration installed to {config_file}")
        print(f"🔄 Run 'source {config_file}' or restart your {shell_name} shell to activate")
        print("💡 After sourcing, you can use 've activate <env>' to properly activate environments")
        return True
    except Exception as e:
        print(f"❌ Failed to write to config file: {e}")
        return False


if __name__ == "__main__":
    print("🔧 Installing ve shell integration...")
    success = install_shell_integration()
    if success:
        print("✅ Shell integration installed successfully!")
        print("💡 Now you can use 've activate <env>' to properly activate environments")
    else:
        print("❌ Failed to install shell integration")
        sys.exit(1)