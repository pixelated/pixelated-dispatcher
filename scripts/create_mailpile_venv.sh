#!/bin/sh
#
# Copyright (c) 2014 ThoughtWorks Deutschland GmbH
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

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
