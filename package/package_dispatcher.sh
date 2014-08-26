#!/bin/bash

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
virtualenv --always-copy $PIXELATED_VIRTUALENV_PATH
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

