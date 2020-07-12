#!/bin/bash

[ -z "$1" ] && echo "ERROR: first parameter must be the stack to start!" && exit 1

STACK=$1

echo "Bringing up $STACK"

[ -n "$STACK" ] && [ -d ./"$TACK" ] && cd $STACK && docker-compose up -d && cd - && exit 0

exit 1

# remove images who are older than ...
# docker system prune --filter "until=240h"
