#!/bin/bash

python setup.py sdist

TEMP_DIR=$(mktemp -d)

cp dist/pixelated-dispatcher*.tar.gz $TEMP_DIR/

pushd $TEMP_DIR
cp pixelated-dispatcher-0.1.tar.gz pixelated-dispatcher_0.1.orig.tar.gz
tar -xzf pixelated-dispatcher-0.1.tar.gz
cd pixelated*
dpkg-buildpackage -rfakeroot -uc -us

cp $TEMP_DIR/python-pixelated-dispatcher_0.1-1_all.deb /tmp/

popd
rm -Rf $TEMP_DIR

