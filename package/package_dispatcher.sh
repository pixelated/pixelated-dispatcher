#!/bin/bash
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

PACKAGE_VERSION="$1"
BUILD_PATH="/tmp/pixelated-dispatcher-build"

PIXELATED_LIB_PATH=$BUILD_PATH/var/lib/pixelated
PIXELATED_VIRTUALENV_PATH=$PIXELATED_LIB_PATH/virtualenv
BIN_PATH=$BUILD_PATH/usr/local/bin

# create build folder
[[ ! -d "$BUILD_PATH" ]] && mkdir $BUILD_PATH
rm -rf $BUILD_PATH/*

# create internal folders
mkdir -p $BIN_PATH
mkdir -p $PIXELATED_LIB_PATH
mkdir -p $BUILD_PATH

cp -rf ./ $PIXELATED_LIB_PATH

# build virtualenv
virtualenv $PIXELATED_VIRTUALENV_PATH
. $PIXELATED_VIRTUALENV_PATH/bin/activate
pip install --upgrade pip
pip install --upgrade setuptools
python setup.py install

rm $PIXELATED_VIRTUALENV_PATH/bin/pixelated-dispatcher
deactivate
cd $PIXELATED_VIRTUALENV_PATH
for FILE in $(grep -l '/tmp/pixelated-dispatcher-build' bin/*); do
    echo "Found file $FILE"
    sed -i 's|/tmp/pixelated-dispatcher-build||' $FILE
done
cd -

cp package/pixelated-dispatcher $BIN_PATH

cd $BUILD_PATH
[[ ! -f '/tmp/gems/bin/fpm' ]] && GEM_HOME=/tmp/gems gem install fpm
GEM_HOME=/tmp/gems /tmp/gems/bin/fpm -s dir -v ${PACKAGE_VERSION} -t deb -n pixelated-dispatcher -C . .

