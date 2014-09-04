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

set -e

git-dch -a -S
python setup.py sdist

TEMP_DIR=$(mktemp -d)

cp dist/pixelated-dispatcher*.tar.gz $TEMP_DIR/

pushd $TEMP_DIR
cp pixelated-dispatcher*.tar.gz pixelated-dispatcher_0.1.orig.tar.gz
tar -xzf pixelated-dispatcher-0.1.tar.gz
cd pixelated*

dpkg-buildpackage -rfakeroot -uc -us

# manual build
#mkdir pkg-root
#python setup.py install --root=pkg-root --install-layout=deb
#fakeroot dpkg --build pkg-root ../python-pixelated-dispatcher_0.1-1_all.deb

cp $TEMP_DIR/python-pixelated-dispatcher*all.deb /tmp/

popd
rm -Rf $TEMP_DIR

