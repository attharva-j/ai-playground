#!/bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [[ $(uname) == Darwin ]]; then
    echo $SCRIPT_DIR
    security find-certificate -c 'Zscaler Root CA' -p > "$SCRIPT_DIR/zsroot.crt"
elif [[ $(uname) == Linux ]]; then
    if [[ ! -f "$SCRIPT_DIR/zsroot.crt" ]]; then
        echo "[ERROR] Please place the Zscaler Root CA in $SCRIPT_DIR/zsroot.crt"
        exit 1
    fi
fi

GITIGNORE_ENTRY="# local copy of Zscaler Root CA for devcontainer\nzsroot.crt"
GITIGNORE_FILE="$SCRIPT_DIR/../.gitignore"
if ! grep -qF "zsroot.crt" "$GITIGNORE_FILE" 2>/dev/null; then
    echo -e "$GITIGNORE_ENTRY" >> "$GITIGNORE_FILE"
fi
