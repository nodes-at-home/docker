#!/bin/bash

# junand 06.05.2023
# https://stackoverflow.com/questions/42660690/is-it-possible-to-shut-down-the-host-machine-by-executing-a-command-on-one-of-it
# install inotify-tools before

SIGNAL_FILE=/var/tmp/shutdown_signal

touch ${SIGNAL_FILE}
chgrp pi ${SIGNAL_FILE}
chmod 664 ${SIGNAL_FILE}

echo "waiting" > ${SIGNAL_FILE}
while inotifywait -e close_write ${SIGNAL_FILE}; do 
  signal=$(cat ${SIGNAL_FILE})
  if [ "$signal" == "shutdown" ]; then 
    echo "done" > ${SIGNAL_FILE}
    logger "shutting down because of ups shutdown signal from home assistant"
    shutdown -h now
  fi
done
