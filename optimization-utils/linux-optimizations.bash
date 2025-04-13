#!/bin/bash

#########################################################
# Linux System Optimization Script for Video Streaming
#
# This script optimizes Linux systems for video streaming
# by configuring network settings and installing required
# software packages.
#########################################################

# Exit codes
EXIT_SUCCESS=0
EXIT_NOT_ROOT=1
EXIT_UNSUPPORTED_OS=2
EXIT_COMMAND_FAILED=3
EXIT_INVALID_ARGS=4

# Default values
APPLY_CHANGES=false
VERBOSE=false
BACKUP=true
ROLLBACK_ON_ERROR=true
LOG_FILE="/tmp/linux-optimization-$(date +%Y%m%d-%H%M%S).log"
SUPPORTED_DISTROS=("ubuntu" "debian" "centos" "rhel" "fedora")

# Version requirements
REQUIRED_VERSIONS=(
    "nginx:1.18.0"
    "openssl:1.1.1"
    "apache2-utils:2.4.0"
    "httpd-tools:2.4.0"
)

# Temporary files and backups
TMP_DIR="/tmp/linux-optimization-$(date +%Y%m%d-%H%M%S)"
BACKUP_LIST=()

#########################################################
# Functions
#########################################################

# Print usage information
usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --apply-changes       Apply changes (required to make actual changes)
  --no-backup           Skip backup of configuration files
  --verbose             Enable verbose output
  --help                Display this help message
  --log-file=FILE       Specify a custom log file (default: $LOG_FILE)

Example:
  $0 --apply-changes --verbose

This script must be run with root privileges.
EOF
    exit $EXIT_INVALID_ARGS
}

# Log messages
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Log error and exit
fatal() {
    log "ERROR" "$1"
    exit $2
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        fatal "This script must be run as root or with sudo privileges" $EXIT_NOT_ROOT
    fi
    log "INFO" "Root privileges verified"
}

# Detect Linux distribution
detect_os() {
    log "INFO" "Detecting operating system..."

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME=$(echo "$ID" | tr '[:upper:]' '[:lower:]')
        OS_VERSION="$VERSION_ID"
        OS_PRETTY_NAME="$PRETTY_NAME"
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS_NAME=$(echo "$DISTRIB_ID" | tr '[:upper:]' '[:lower:]')
        OS_VERSION="$DISTRIB_RELEASE"
        OS_PRETTY_NAME="$DISTRIB_DESCRIPTION"
    elif [ -f /etc/redhat-release ]; then
        OS_NAME=$(cat /etc/redhat-release | tr '[:upper:]' '[:lower:]')
        if [[ "$OS_NAME" == *"centos"* ]]; then
            OS_NAME="centos"
        elif [[ "$OS_NAME" == *"red hat"* ]]; then
            OS_NAME="rhel"
        fi
        OS_VERSION=$(cat /etc/redhat-release | grep -o '[0-9]\+\.[0-9]\+')
        OS_PRETTY_NAME=$(cat /etc/redhat-release)
    else
        fatal "Unsupported or undetected Linux distribution" $EXIT_UNSUPPORTED_OS
    fi

    # Check if OS is supported
    local supported=false
    for distro in "${SUPPORTED_DISTROS[@]}"; do
        if [[ "$OS_NAME" == *"$distro"* ]]; then
            supported=true
            break
        fi
    done

    if [ "$supported" = false ]; then
        fatal "Unsupported Linux distribution: $OS_PRETTY_NAME" $EXIT_UNSUPPORTED_OS
    fi

    log "INFO" "Detected OS: $OS_PRETTY_NAME"
    return $EXIT_SUCCESS
}

# Backup a file before modifying it
backup_file() {
    local file=$1
    local backup_file="${file}.bak.$(date +%Y%m%d-%H%M%S)"

    if [ "$BACKUP" = true ] && [ -f "$file" ]; then
        log "INFO" "Backing up $file to $backup_file"
        cp "$file" "$backup_file" || fatal "Failed to backup $file" $EXIT_COMMAND_FAILED
    fi
}

# Execute a command with error handling
exec_command() {
    local cmd=$1
    local error_msg=$2
    local exit_code=$3

    if [ "$VERBOSE" = true ]; then
        log "DEBUG" "Executing: $cmd"
    fi

    if [ "$APPLY_CHANGES" = true ]; then
        eval $cmd >> "$LOG_FILE" 2>&1
        local status=$?
        if [ $status -ne 0 ]; then
            fatal "$error_msg (exit code: $status)" $exit_code
        fi
    else
        log "INFO" "[DRY RUN] Would execute: $cmd"
    fi
}

# Configure network settings
configure_network() {
    log "INFO" "Configuring network settings..."

    # TCP optimizations
    exec_command "sysctl -w net.core.rmem_max=16777216" "Failed to set net.core.rmem_max" $EXIT_COMMAND_FAILED
    exec_command "sysctl -w net.core.wmem_max=16777216" "Failed to set net.core.wmem_max" $EXIT_COMMAND_FAILED
    exec_command "sysctl -w net.ipv4.tcp_rmem=\"4096 87380 16777216\"" "Failed to set net.ipv4.tcp_rmem" $EXIT_COMMAND_FAILED
    exec_command "sysctl -w net.ipv4.tcp_wmem=\"4096 65536 16777216\"" "Failed to set net.ipv4.tcp_wmem" $EXIT_COMMAND_FAILED
    exec_command "sysctl -w net.ipv4.tcp_window_scaling=1" "Failed to set net.ipv4.tcp_window_scaling" $EXIT_COMMAND_FAILED
    exec_command "sysctl -w net.ipv4.tcp_max_syn_backlog=8192" "Failed to set net.ipv4.tcp_max_syn_backlog" $EXIT_COMMAND_FAILED
    exec_command "sysctl -w net.ipv4.tcp_syncookies=1" "Failed to set net.ipv4.tcp_syncookies" $EXIT_COMMAND_FAILED

    # Make changes permanent
    if [ "$APPLY_CHANGES" = true ]; then
        backup_file "/etc/sysctl.conf"

        log "INFO" "Making network changes permanent in /etc/sysctl.conf"
        cat <<EOF > /tmp/sysctl_append.conf
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_window_scaling=1
net.ipv4.tcp_max_syn_backlog=8192
net.ipv4.tcp_syncookies=1
EOF
        exec_command "cat /tmp/sysctl_append.conf >> /etc/sysctl.conf" "Failed to update /etc/sysctl.conf" $EXIT_COMMAND_FAILED
        exec_command "rm /tmp/sysctl_append.conf" "Failed to remove temporary file" $EXIT_COMMAND_FAILED

        # Apply changes
        exec_command "sysctl -p" "Failed to apply sysctl changes" $EXIT_COMMAND_FAILED
    else
        log "INFO" "[DRY RUN] Would update /etc/sysctl.conf and apply changes"
    fi
}

# Install required software
install_software() {
    log "INFO" "Installing required software..."

    # Determine package manager and install command based on OS
    local install_cmd=""
    local update_cmd=""
    local packages="nginx"

    case "$OS_NAME" in
        ubuntu|debian)
            update_cmd="apt update"
            install_cmd="apt install -y"
            packages="$packages apache2-utils"
            ;;
        centos|rhel)
            update_cmd="yum check-update"
            install_cmd="yum install -y"
            packages="$packages httpd-tools"
            ;;
        fedora)
            update_cmd="dnf check-update"
            install_cmd="dnf install -y"
            packages="$packages httpd-tools"
            ;;
        *)
            fatal "Unsupported package manager for $OS_NAME" $EXIT_UNSUPPORTED_OS
            ;;
    esac

    # Update package lists
    exec_command "$update_cmd" "Failed to update package lists" $EXIT_COMMAND_FAILED

    # Install packages
    exec_command "$install_cmd $packages" "Failed to install required packages" $EXIT_COMMAND_FAILED
}

# Check system requirements
check_system_requirements() {
    log "INFO" "Checking system requirements..."

    # Check for required commands
    local required_commands=("sysctl" "grep" "sed" "tee")
    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            fatal "Required command '$cmd' not found" $EXIT_COMMAND_FAILED
        fi
    done

    # Check available memory
    local total_mem=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$total_mem" -lt 1024 ]; then
        log "WARNING" "System has less than 1GB of RAM ($total_mem MB). Performance may be affected."
    else
        log "INFO" "System has $total_mem MB of RAM"
    fi

    # Check available disk space
    local root_space=$(df -m / | awk 'NR==2 {print $4}')
    if [ "$root_space" -lt 1024 ]; then
        log "WARNING" "System has less than 1GB of free disk space ($root_space MB). Performance may be affected."
    else
        log "INFO" "System has $root_space MB of free disk space"
    fi
}

# Print summary
print_summary() {
    log "INFO" "Optimization completed successfully"
    log "INFO" "Log file: $LOG_FILE"

    if [ "$APPLY_CHANGES" = false ]; then
        log "WARNING" "This was a dry run. No changes were applied."
        log "INFO" "Run with --apply-changes to apply the changes."
    fi

    cat <<EOF

=================================================================
                  OPTIMIZATION SUMMARY
=================================================================
Operating System: $OS_PRETTY_NAME
Changes Applied: $([ "$APPLY_CHANGES" = true ] && echo "Yes" || echo "No (dry run)")
Log File: $LOG_FILE

Recommendations:
1. Consider configuring HTTPS for secure video delivery
2. Monitor server performance after changes
3. Adjust cache durations based on your specific content update frequency

You may need to restart the server for all changes to take full effect.
=================================================================
EOF
}

#########################################################
# Main Script
#########################################################

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --apply-changes)
            APPLY_CHANGES=true
            ;;
        --no-backup)
            BACKUP=false
            ;;
        --verbose)
            VERBOSE=true
            ;;
        --log-file=*)
            LOG_FILE="${1#*=}"
            ;;
        --help)
            usage
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            ;;
    esac
    shift
done

# Initialize log file
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
log "INFO" "Starting Linux optimization script"
log "INFO" "Log file: $LOG_FILE"

# Check if running as root
check_root

# Detect OS
detect_os

# Check system requirements
check_system_requirements

# Configure network settings
configure_network

# Install required software
install_software

# Print summary
print_summary

exit $EXIT_SUCCESS