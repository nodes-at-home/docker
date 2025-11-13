#!/bin/bash

if [ -x /usr/bin/docker-compose ]
then
    COMPOSE=docker-compose
else
    COMPOSE="docker compose"
fi

[ -z "$1" ] && echo "ERROR: first parameter must bee the app to execute!" && exit

find_stack () {

    echo $( grep "$1:$" ./*/docker-compose.yaml | cut -d/ -f2 )

}

platform () {

    result="$(uname -n)"

    case "${result}" in
        andreas-book4*)    result=wsl2;;
    esac

    echo ${result}

}

CONTAINER_SHELL=bash
[ ! -z "$2" ] && CONTAINER_SHELL=$2

pushd "$HOME/docker/docker"

APP=$1

STACK=$(find_stack "$APP")
# echo "step 1 STACK=${STACK}"

if [ -z "$STACK" ]
then
    APP="${APP}-$(platform)"
    STACK=$(find_stack "$APP")
    # echo "step 2 STACK=${STACK}"
fi

if [ -z "$STACK" ]
then
    echo "ERROR: could not find stack for app '$APP'"
    popd
    exit 1
fi

echo "Executing $APP in $STACK"

[ -n "$APP" ] && [ -n "$STACK" ] && [ -d ./"$STACK" ] && cd $STACK && $COMPOSE exec $APP $CONTAINER_SHELL && cd -

popd

# remove images who are older than ...
# docker system prune --filter "until=240h"
