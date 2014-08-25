#
# Copyright 2014 ThoughtWorks Deutschland GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import gnupg

__author__ = 'fbernitt'


class GnuPGInitializer(object):
    """ Initializes GnuPG and generates a keypair
        see: https://www.gnupg.org/documentation/manuals/gnupg-devel/Unattended-GPG-key-generation.html
    """

    def create_key_pair(self, gnupg_home, email, name_real, keytype='RSA', key_length='2048', expire_date=0):
        gpg = gnupg.GPG(gnupghome=gnupg_home, verbose=True)

        data = {
            'name_email': email,
            'name_real': name_real,
            'key_type': keytype,
            'key_length': key_length,
            'expire_date': expire_date
        }

        input_data = gpg.gen_key_input(**data)
        print input_data
        key = gpg.gen_key(input_data)

        print 'Created key for email: %s' % key
