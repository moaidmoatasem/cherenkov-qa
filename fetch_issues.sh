#!/bin/bash
for i in 200 201 202 203 204 205 206; do
  echo "=== Issue $i ==="
  gh api repos/moaidmoatasem/cherenkov-qa/issues/$i | jq -r '(.number|tostring) + ": " + .title + "\n" + .body + "\n------------------\n"'
done
