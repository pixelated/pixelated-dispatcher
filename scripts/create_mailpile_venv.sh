#!/bin/sh

VENV_PATH="$1"

if [ -z "$VENV_PATH" ] ; then
    echo "Specify target path for virtualenv"
    exit 1
fi

if [ -f "$VENV_PATH/bin/activate" ] ; then
    exit 0
fi

virtualenv "$VENV_PATH"

source "$VENV_PATH/bin/activate"

TMP_DIR=$(mktemp -d -t mailpile)
MAILPILE_DIR="$TMP_DIR/Mailpile.git"

git clone https://github.com/pagekite/Mailpile.git "$MAILPILE_DIR"
cd $MAILPILE_DIR

python setup.py install

rm -Rf "$TMP_DIR"

exit 0
