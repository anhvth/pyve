#!/usr/bin/env python3
"""
Standalone shell integration installer for ve command.
This script doesn't depend on rich or other external libraries.
"""

import os
import sys
from pathlib import Path


def detect_shell_and_config():
    """Detect shell type and return appropriate config file path."""
    shell = os.environ.get('SHELL', '')
    if 'zsh' in shell:
        config_file = Path.home() / '.zshrc'
        shell_name = 'zsh'
    else:
        # Default to bash
        config_file = Path.home() / '.bashrc'
        shell_name = 'bash'
    return shell_name, config_file


def install_shell_integration():
    """Install shell integration for ve commands."""
    shell_name, config_file = detect_shell_and_config()
    
    # Determine which shell integration script to use
    script_dir = Path(__file__).parent / "vex"
    if shell_name == 'zsh':
        integration_script = script_dir / "shell_integration_zsh.sh"
    else:
        integration_script = script_dir / "shell_integration_bash.sh"
    
    if not integration_script.exists():
        print(f"❌ Shell integration script not found: {integration_script}")
        return False
    
    # Read the integration script content
    try:
        integration_content = integration_script.read_text()
    except Exception as e:
        print(f"❌ Failed to read integration script: {e}")
        return False
    
    # Check if shell config file exists, create if not
    if not config_file.exists():
        print(f"📝 Creating shell config file: {config_file}")
        try:
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
    
    # Check if ve integration is already installed (either by marker or ve function)
    ve_marker = "# Virtual Environment Manager (ve) Integration"
    has_ve_function = "ve()" in current_content or "function ve()" in current_content
    
    if ve_marker in current_content or has_ve_function:
        if has_ve_function and ve_marker not in current_content:
            print(f"⚠️  ve() function already exists in {config_file} (not installed by ve)")
            print("A custom ve() function is already defined. Skipping installation.")
            return True
        else:
            print(f"⚠️  ve shell integration already installed in {config_file}")
            response = input("Reinstall shell integration? [y/N] ").strip().lower()
            if response not in ('y', 'yes'):
                print("✅ Shell integration installation skipped")
                return True
            
            # Remove existing integration
            lines = current_content.splitlines()
            new_lines = []
            skip_lines = False
            
            for line in lines:
                if ve_marker in line:
                    skip_lines = True
                elif skip_lines and line.strip() == "" and len(new_lines) > 0:
                    # End of ve integration block (empty line after)
                    skip_lines = False
                elif not skip_lines:
                    new_lines.append(line)
            
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