# Virtual Environment Manager (ve) Shell Integration for Fish
# This enables proper activation of virtual environments from the shell

# Define the ve function that wraps the ve command and handles activation
function ve
    set -l cmd $argv[1]
    set -e argv[1]

    if test "$cmd" = "activate" -a (count $argv) -ge 1
        set -l env_name $argv[1]
        set -e argv[1]
        set -l extra_args $argv

        # Get activation script path from ve command
        set -l ve_output (python3 -m pyve.cli activate "$env_name" $extra_args 2>&1)
        set -l ve_exit_code $status

        # Print the ve command output first
        echo "$ve_output"

        # If ve command succeeded, try to extract and source the activation script
        if test $ve_exit_code -eq 0
            # Extract the activation script path from the output
            set -l activate_script (echo "$ve_output" | grep "source " | sed 's/.*source \([^ ]*\).*/\1/')

            # If we found an activation script, set up the environment manually for fish
            if test -n "$activate_script" -a -f "$activate_script"
                # Extract the venv path from the activate script
                set -l venv_path (dirname (dirname "$activate_script"))

                # Set VIRTUAL_ENV
                set -gx VIRTUAL_ENV "$venv_path"

                # Add the bin directory to PATH
                set -l bin_path "$venv_path/bin"
                if not contains $bin_path $PATH
                    set -gx PATH $bin_path $PATH
                end

                # Set PYTHONHOME to empty if it exists
                set -e PYTHONHOME

                echo "✅ Environment activated: $env_name"
            end
        end

        return $ve_exit_code
    else if test "$cmd" = "deactivate"
        # Handle deactivation
        if test -n "$VIRTUAL_ENV"
            set -l env_name (basename "$VIRTUAL_ENV")
            # Remove venv bin from PATH
            set -l venv_bin "$VIRTUAL_ENV/bin"
            set -l new_path
            for path in $PATH
                if test "$path" != "$venv_bin"
                    set new_path $new_path $path
                end
            end
            set -gx PATH $new_path
            set -e VIRTUAL_ENV
            echo "✅ Environment deactivated: $env_name"
        else
            echo "❌ No active virtual environment to deactivate"
        end
        return 0
    else
        # For all other commands, just pass through to the original ve command
        python3 -m pyve.cli $cmd $argv
    end
end

# Auto-activate venv when changing directories
function _ve_auto_activate
    set -l current_env (python3 -c "
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

    if test -n "$current_env"
        set -l current_venv_name ""
        if test -n "$VIRTUAL_ENV"
            set current_venv_name (basename "$VIRTUAL_ENV")
        end

        if test "$current_venv_name" != "$current_env"
            echo "💡 Suggestion: activate environment '$current_env' for this directory"
            echo "   Run: ve activate $current_env"
        end
    end
end

# Set up directory change hook for fish
function _ve_cd_hook --on-variable PWD
    _ve_auto_activate
end

# Also check on shell startup
_ve_auto_activate