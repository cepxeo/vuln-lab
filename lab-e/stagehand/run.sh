#!/bin/sh
# Keeps the API answering. It is one Node process: a template loop sent to the
# signature preview (E14) blocks it for good, and a crash ends it. When the
# site has not answered for 30 s, or the process ended, it starts again, fresh:
# a restart re-seeds the data, as a container restart does.
cd /app
while :; do
  node server.js &
  pid=$!
  misses=0
  sleep 5
  while kill -0 "$pid" 2>/dev/null; do
    if wget -q -T 5 -O /dev/null "http://127.0.0.1:${PORT:-5050}/"; then
      misses=0
    else
      misses=$((misses + 1))
    fi
    if [ "$misses" -ge 3 ]; then
      echo "stagehand: no answer for 30 s, restarting the API"
      kill -9 "$pid" 2>/dev/null
      break
    fi
    sleep 10
  done
  wait "$pid" 2>/dev/null
  sleep 1
done
