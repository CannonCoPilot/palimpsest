#!/bin/bash
PID=85037
ROOT=projects/originaldr/sources/our-ocr-diplomatic
while kill -0 "$PID" 2>/dev/null; do sleep 300; done
N=$(find "$ROOT" -name '*.json' 2>/dev/null | grep -v _manifest | wc -l | tr -d ' ')
echo "OCR-RUN-ENDED pid=$PID final_pages=$N target~6116 $(date '+%H:%M:%S')"
