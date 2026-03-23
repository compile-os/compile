#!/bin/bash
# Resilient autoresearch wrapper — restarts Claude if it crashes
# Usage: ./autoresearch_wrapper.sh "prompt text" logname [max_retries] [budget]

PROMPT="$1"
LOGNAME="$2"
MAX_RETRIES="${3:-5}"
BUDGET="${4:-15}"
RETRY=0

# IMPORTANT: Set your API key as an environment variable, never hardcode it
# export ANTHROPIC_API_KEY='your-key-here'
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY environment variable not set" >&2
    exit 1
fi

mkdir -p ${RESULTS_DIR:-results}

while [ $RETRY -lt $MAX_RETRIES ]; do
    RETRY=$((RETRY + 1))
    echo "[$(date)] Attempt $RETRY/$MAX_RETRIES starting..." >> ${RESULTS_DIR:-results}/${LOGNAME}_wrapper.log

    claude -p --dangerously-skip-permissions --max-budget-usd $BUDGET --verbose "$PROMPT" \
        >> ${RESULTS_DIR:-results}/${LOGNAME}_output.log 2>&1

    EXIT_CODE=$?
    echo "[$(date)] Claude exited with code $EXIT_CODE" >> ${RESULTS_DIR:-results}/${LOGNAME}_wrapper.log

    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] Completed successfully." >> ${RESULTS_DIR:-results}/${LOGNAME}_wrapper.log
        break
    fi

    echo "[$(date)] Crashed. Waiting 30s before retry..." >> ${RESULTS_DIR:-results}/${LOGNAME}_wrapper.log
    sleep 30
done

echo "[$(date)] Wrapper done after $RETRY attempts." >> ${RESULTS_DIR:-results}/${LOGNAME}_wrapper.log
