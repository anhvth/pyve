#!/usr/bin/env python3
"""
Clean up duplicate ve integrations from .zshrc file
"""
import re
from pathlib import Path

def clean_zshrc():
    zshrc_path = Path.home() / '.zshrc'
    
    if not zshrc_path.exists():
        print("No .zshrc file found")
        return
    
    content = zshrc_path.read_text()
    lines = content.splitlines()
    
    new_lines = []
    in_ve_section = False
    in_ve_function = False
    brace_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for ve integration markers
        if ("Virtual Environment Manager" in line or 
            "This enables proper activation of virtual environments" in line or
            line.strip().startswith("# Virtual Environment Manager (ve) Integration")):
            in_ve_section = True
            i += 1
            continue
        
        # Check for ve function definitions
        if (("ve()" in line or "function ve()" in line) and 
            not line.strip().startswith("#")):
            in_ve_function = True
            brace_count = 0
            # Count braces on the current line
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
        if in_ve_section:
            # Look for lines that indicate we might be at the end
            if ("_ve_auto_activate" in line or 
                "add-zsh-hook" in line or
                line.strip().startswith("fi")):
                # Continue in section until we find a clear end
                i += 1
                continue
            elif (line.strip() == "" and 
                  i + 1 < len(lines) and 
                  lines[i + 1].strip() != "" and 
                  not lines[i + 1].strip().startswith("#") and
                  "ve" not in lines[i + 1] and
                  "_ve_auto_activate" not in lines[i + 1]):
                # This looks like the end of the section
                in_ve_section = False
                new_lines.append(line)  # Keep the spacing
                i += 1
                continue
            else:
                # Still in ve section
                i += 1
                continue
        
        # Keep lines that are not part of ve integration
        new_lines.append(line)
        i += 1
    
    # Write the cleaned content
    cleaned_content = "\n".join(new_lines)
    zshrc_path.write_text(cleaned_content)
    
    print(f"Cleaned .zshrc file. Removed ve integrations.")
    
    # Count remaining ve() functions
    remaining_ve_count = cleaned_content.count("ve()")
    if remaining_ve_count > 0:
        print(f"Warning: {remaining_ve_count} ve() function(s) still remain")

if __name__ == "__main__":
    clean_zshrc()