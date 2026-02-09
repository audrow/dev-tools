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
    [ -f "$SCRIPT_DIR/utils.sh" ] && source "$SCRIPT_DIR/utils.sh"
    
    # Source all git tools
    if [ -d "$SCRIPT_DIR/git_tools" ]; then
        for f in "$SCRIPT_DIR/git_tools"/*.sh; do
            [ -f "$f" ] && source "$f"
        done
    fi
    
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
            source '$SCRIPT_DIR/utils.sh' 2>/dev/null
            if [ -d '$SCRIPT_DIR/git_tools' ]; then
                for f in '$SCRIPT_DIR/git_tools'/*.sh; do
                    [ -f \"\$f\" ] && source \"\$f\"
                done
            fi
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
    
    _run_bash_func_interactive() {
        local func_name="$1"
        shift
        
        # For interactive functions, we need to preserve stdin/stdout/stderr
        # Use a temp file to capture the __BASH_CD__ marker
        local temp_file=$(mktemp)
        
        if [ -t 0 ]; then
            bash -c "
            source '$SCRIPT_DIR/utils.sh' 2>/dev/null
            if [ -d '$SCRIPT_DIR/git_tools' ]; then
                for f in '$SCRIPT_DIR/git_tools'/*.sh; do
                    [ -f \"\$f\" ] && source \"\$f\"
                done
            fi
            source '$SCRIPT_DIR/python_tools.sh' 2>/dev/null
            
            # Redirect __BASH_CD__ marker to temp file
            exec 3>'$temp_file'
            
            # Override echo to intercept __BASH_CD__ markers
            echo() {
                if [[ \"\$1\" == __BASH_CD__:* ]]; then
                    builtin echo \"\$@\" >&3
                else
                    builtin echo \"\$@\"
                fi
            }
            
            $func_name \"\$@\"
            exit_code=\$?
            exec 3>&-
            exit \$exit_code
        " -- "$@" </dev/tty
        else
            bash -c "
            source '$SCRIPT_DIR/utils.sh' 2>/dev/null
            if [ -d '$SCRIPT_DIR/git_tools' ]; then
                for f in '$SCRIPT_DIR/git_tools'/*.sh; do
                    [ -f \"\$f\" ] && source \"\$f\"
                done
            fi
            source '$SCRIPT_DIR/python_tools.sh' 2>/dev/null
            
            # Redirect __BASH_CD__ marker to temp file
            exec 3>'$temp_file'
            
            # Override echo to intercept __BASH_CD__ markers
            echo() {
                if [[ \"\$1\" == __BASH_CD__:* ]]; then
                    builtin echo \"\$@\" >&3
                else
                    builtin echo \"\$@\"
                fi
            }
            
            $func_name \"\$@\"
            exit_code=\$?
            exec 3>&-
            exit \$exit_code
        " -- "$@"
        fi
        local ret=$?
        
        # Extract cd path if present
        local cd_path
        if [ -f "$temp_file" ]; then
            cd_path=$(grep "^__BASH_CD__:" "$temp_file" | tail -1 | cut -d: -f2-)
            rm -f "$temp_file"
        fi
        
        # Change directory if requested
        if [ -n "$cd_path" ] && [ -d "$cd_path" ]; then
            cd "$cd_path"
        fi
        
        return $ret
    }
    
    # Git worktree tools (these may cd)
    wt() { _run_bash_func wt "$@"; }
    wta() { _run_bash_func_interactive wta "$@"; }
    wtp() { _run_bash_func_interactive wtp "$@"; }
    wto() { _run_bash_func_interactive wto "$@"; }
    wtlock() { _run_bash_func_interactive wtlock "$@"; }
    wtunlock() { _run_bash_func_interactive wtunlock "$@"; }
    
    # Git workflow tools
    gupdate() { _run_bash_func gupdate "$@"; }
    gmb() { _run_bash_func gmb "$@"; }
    gdiff_out() { _run_bash_func gdiff_out "$@"; }
    gdmbo() { _run_bash_func gdmbo "$@"; }
    gskip() { _run_bash_func_interactive gskip "$@"; }
    gunskip() { _run_bash_func_interactive gunskip "$@"; }
    gskipped() { _run_bash_func gskipped "$@"; }
    gdo() { _run_bash_func gdo "$@"; }
    gexec() { _run_bash_func_interactive gexec "$@"; }
    gexec_mb() { _run_bash_func_interactive gexec_mb "$@"; }
    
    # Source aliases directly - it only defines simple aliases that work in zsh
    [ -f "$SCRIPT_DIR/git_tools/aliases.sh" ] && source "$SCRIPT_DIR/git_tools/aliases.sh"
    
    # Source python_tools.sh directly if it's zsh-compatible
    [ -f "$SCRIPT_DIR/python_tools.sh" ] && source "$SCRIPT_DIR/python_tools.sh"
fi

# Alert if disk usage is over 80% (only in interactive terminals)
_check_disk_usage_startup() {
    # Only check in interactive terminal to avoid breaking scripts/tests
    if [ ! -t 1 ]; then
        return 0
    fi

    local disk_usage
    if command -v df >/dev/null 2>&1; then
        # Use df -P for portability (avoids line wrapping), tail -1 for last line
        disk_usage=$(df -P / | tail -1 | awk '{print $5}' | tr -d '%')
        
        if [ -n "$disk_usage" ] && [ "$disk_usage" -gt 80 ]; then
             printf "\033[1;31m⚠️  WARNING: Disk usage is at %s%%. Run 'bazel clean --expunge' soon!\033[0m\n" "$disk_usage"
        fi
    fi
}
_check_disk_usage_startup
unset -f _check_disk_usage_startup

# Explicitly return true to ensure source init.sh doesn't fail if the last command failed
true
