#!/bin/bash
# Build script for SwiftHAL with optional quiet mode

set -e

QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -q|--quiet)
            QUIET=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-q|--quiet]"
            exit 1
            ;;
    esac
done

if [ "$QUIET" = true ]; then
    # Suppress all build output (including errors)
    # Use with caution - errors won't be visible
    swift build 2>/dev/null
else
    # Normal build with all output
    swift build
fi
