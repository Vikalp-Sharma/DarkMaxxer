#!/usr/bin/env bash
# ============================================================================
# DarkMaxxer Boot Autostart Wrapper (startup.sh)
# Forwards directly to RPI/startup.sh to configure boot autostart.
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/RPI/startup.sh" ]; then
    bash "$SCRIPT_DIR/RPI/startup.sh" "$@"
else
    echo " [ERROR] RPI/startup.sh not found inside $SCRIPT_DIR/RPI"
    exit 1
fi
