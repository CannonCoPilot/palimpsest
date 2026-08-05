#!/bin/bash
# Notify when the first post-relaunch batch writes pages (ot1 climbs above 821) or run ends.
PID=85037
D=projects/originaldr/sources/our-ocr-diplomatic/archive-ot1-1609
base=821
until n=$(find "$D" -name '*.json' 2>/dev/null | grep -v manifest | wc -l | tr -d ' '); [ "$n" -gt "$base" ] || ! kill -0 "$PID" 2>/dev/null; do sleep 30; done
tot=$(find projects/originaldr/sources/our-ocr-diplomatic -name '*.json' 2>/dev/null | grep -v manifest | wc -l | tr -d ' ')
echo "FIRST-BACKFILL-CONFIRMED ot1=$n (was 821) total=$tot/6116 $(date '+%H:%M:%S')"
