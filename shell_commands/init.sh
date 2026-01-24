#!/bin/bash

# Function to get the current script directory
get_script_dir() {
    if [ -n "$BASH_VERSION" ]; then
        echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "$(cd "$(dirname "${(%):-%x}")" && pwd)"
    else
        # Fallback
        echo "$(cd "$(dirname "$0")" && pwd)"
    fi
}

SCRIPT_DIR=$(get_script_dir)

# If running in bash, source scripts directly
if [ -n "$BASH_VERSION" ]; then
    [ -f "$SCRIPT_DIR/git_aliases.sh" ] && source "$SCRIPT_DIR/git_aliases.sh"
    [ -f "$SCRIPT_DIR/git_worktree_tools.sh" ] && source "$SCRIPT_DIR/git_worktree_tools.sh"
    [ -f "$SCRIPT_DIR/git_workflow_tools.sh" ] && source "$SCRIPT_DIR/git_workflow_tools.sh"
    [ -f "$SCRIPT_DIR/python_tools.sh" ] && source "$SCRIPT_DIR/python_tools.sh"
else
    # Running in zsh or other shell - create wrapper functions that run in bash
    # 
    # Scripts can output "__BASH_CD__:/path/to/dir" to signal a directory change
    # that should be applied in the parent shell.
    
    _run_bash_func() {
        local func_name="$1"
        shift
        
        local output
        output=$(bash -c "
            source '$SCRIPT_DIR/git_aliases.sh' 2>/dev/null
            source '$SCRIPT_DIR/git_worktree_tools.sh' 2>/dev/null
            source '$SCRIPT_DIR/git_workflow_tools.sh' 2>/dev/null
            source '$SCRIPT_DIR/python_tools.sh' 2>/dev/null
            $func_name \"\$@\"
        " -- "$@" 2>&1)
        local ret=$?
        
        # Extract cd path if present
        local cd_path
        cd_path=$(echo "$output" | grep "^__BASH_CD__:" | tail -1 | cut -d: -f2-)
        
        # Print output without the marker lines
        echo "$output" | grep -v "^__BASH_CD__:"
        
        # Change directory if requested
        if [ -n "$cd_path" ] && [ -d "$cd_path" ]; then
            cd "$cd_path"
        fi
        
        return $ret
    }
    
    # Git worktree tools (these may cd)
    wt() { _run_bash_func wt "$@"; }
    wta() { _run_bash_func wta "$@"; }
    wtp() { _run_bash_func wtp "$@"; }
    
    # Git workflow tools
    gupdate() { _run_bash_func gupdate "$@"; }
    gmb() { _run_bash_func gmb "$@"; }
    gdiff_out() { _run_bash_func gdiff_out "$@"; }
    gdmb() { _run_bash_func gdmb "$@"; }
    
    # Source git_aliases.sh directly - it only defines simple aliases that work in zsh
    [ -f "$SCRIPT_DIR/git_aliases.sh" ] && source "$SCRIPT_DIR/git_aliases.sh"
    
    # Source python_tools.sh directly if it's zsh-compatible
    [ -f "$SCRIPT_DIR/python_tools.sh" ] && source "$SCRIPT_DIR/python_tools.sh"
fi
