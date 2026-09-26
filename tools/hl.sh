#!/bin/sh
# Usage: ./hl.sh "cmd1" "cmd2" ...   -> runs hlbc commands on extracted/hlboot.dat
D="$(dirname "$0")"
{ for c in "$@"; do echo "$c"; done; echo exit; } | "$D/hlbc.exe" "$D/../extracted/hlboot.dat" 2>&1 | sed 's/^\(> \)*//'
