# Virtual Environment Manager (ve) Shell Integration for Zsh
# This enables proper activation of virtual environments from the shell

# Define the ve function that wraps the ve command and handles activation
ve() {
    local cmd="$1"
    shift
    
    if [[ "$cmd" == "activate" && $# -ge 1 ]]; then
        local env_name="$1"
        shift
        local extra_args=("$@")
        
        # Get activation script path from ve command
        local ve_output=$(command ve activate "$env_name" "${extra_args[@]}" 2>&1)
        local ve_exit_code=$?
        
        # If ve command succeeded, try to extract and source the activation script
        if [[ $ve_exit_code -eq 0 ]]; then
            # Extract the activation script path from the output
            local activate_script=$(echo "$ve_output" | grep "source " | sed 's/.*source \([^ ]*\).*/\1/')
            
            # If we found an activation script, source it
            if [[ -n "$activate_script" && -f "$activate_script" ]]; then
                source "$activate_script"
                echo "✅ $env_name"
            else
                # Fallback: show the original output if we can't parse it
                echo "$ve_output"
            fi
        else
            # Show error output
            echo "$ve_output"
        fi
        
        return $ve_exit_code
    elif [[ "$cmd" == "deactivate" ]]; then
        # Handle deactivation
        if [[ -n "$VIRTUAL_ENV" ]]; then
            local env_name=$(basename "$VIRTUAL_ENV")
            deactivate 2>/dev/null || true
            echo "✅ deactivated $env_name"
        else
            echo "❌ No active virtual environment"
        fi
        return 0
    else
        # For all other commands, just pass through to the original ve command
        command ve "$cmd" "$@"
    fi
}

# Auto-activate venv when changing directories
_ve_auto_activate() {
    local current_env=$(python3 -c "
import os
from pathlib import Path
try:
    from pyve import VenvManager
    manager = VenvManager()
    env = manager.get_auto_activate_env()
    if env:
        print(env)
except:
    pass
" 2>/dev/null)
    
    if [[ -n "$current_env" ]]; then
        local current_venv_name=""
        if [[ -n "$VIRTUAL_ENV" ]]; then
            current_venv_name=$(basename "$VIRTUAL_ENV")
        fi
        
        if [[ "$current_venv_name" != "$current_env" ]]; then
            echo "💡 ve activate $current_env"
        fi
    fi
}

# Set up directory change hook for zsh
if [[ -n "$ZSH_VERSION" ]]; then
    autoload -U add-zsh-hook
    add-zsh-hook chpwd _ve_auto_activate
    
    # Also check on shell startup
    _ve_auto_activate
fi
