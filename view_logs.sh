#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${AGENT_LOG_DIR:-$SCRIPT_DIR/.logs}"
AGENT="all"
LINES=100
FOLLOW=true

usage() {
    cat <<'EOF'
Usage: ./view_logs.sh [agent] [-n lines] [--no-follow]

Agents:
  all          Show all agent logs (default)
  lab          Lab Agent, port 8000
  developer    Developer Agent, port 8001
  status       Status Agent, port 8002
  computing    Computing Agent, port 8003
  experiment   Experiment Agent, port 8004 (development)

Options:
  -n, --lines NUMBER  Initial number of lines to show (default: 100)
  --no-follow         Print the current logs and exit
  -h, --help          Show this help

Examples:
  ./view_logs.sh
  ./view_logs.sh lab
  ./view_logs.sh computing -n 200
  ./view_logs.sh all --no-follow
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        all|lab|developer|status|computing|experiment)
            AGENT="$1"
            shift
            ;;
        -n|--lines)
            if [ "$#" -lt 2 ] || ! [[ "$2" =~ ^[1-9][0-9]*$ ]]; then
                echo "Error: --lines requires a positive integer." >&2
                exit 2
            fi
            LINES="$2"
            shift 2
            ;;
        --no-follow)
            FOLLOW=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option or agent '$1'." >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$AGENT" in
    lab) requested_files=("$LOG_DIR/lab.log") ;;
    developer) requested_files=("$LOG_DIR/developer.log") ;;
    status) requested_files=("$LOG_DIR/status.log") ;;
    computing) requested_files=("$LOG_DIR/computing.log") ;;
    experiment) requested_files=("$LOG_DIR/experiment.log") ;;
    all) requested_files=(
        "$LOG_DIR/lab.log"
        "$LOG_DIR/developer.log"
        "$LOG_DIR/status.log"
        "$LOG_DIR/computing.log"
        "$LOG_DIR/experiment.log"
    ) ;;
esac

files=()
for file in "${requested_files[@]}"; do
    if [ -f "$file" ]; then
        files+=("$file")
    elif [ "$AGENT" != "all" ]; then
        echo "No log exists yet for '$AGENT': $file" >&2
        echo "Start the agent with ./start_all.sh or its individual start script." >&2
        exit 1
    fi
done

if [ "${#files[@]}" -eq 0 ]; then
    echo "No agent logs exist yet in $LOG_DIR" >&2
    echo "Start the system with ./start_all.sh first." >&2
    exit 1
fi

echo "Agent logs: $LOG_DIR"
echo "Showing: $AGENT"
if [ "$FOLLOW" = true ]; then
    echo "Following new output. Press Ctrl+C to stop."
    exec tail -n "$LINES" -F "${files[@]}"
else
    exec tail -n "$LINES" "${files[@]}"
fi
