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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

CSR_FILE="server.csr"
CFG_FILE="server.cnf"
CRT_FILE="server.crt"
KEY_FILE="server.key"

UTIL_DIR=$(dirname $0)

echo "Util dir is [$UTIL_DIR] derived from $0"

pushd $UTIL_DIR

# create the csr
openssl req -new -key $KEY_FILE -out $CSR_FILE -config $CFG_FILE

# self sign the request
openssl x509 -req -days 365 -in $CSR_FILE -signkey $KEY_FILE -out $CRT_FILE -extensions v3_req -extfile $CFG_FILE -sha256


openssl x509 -in $CRT_FILE -text -noout

popd

