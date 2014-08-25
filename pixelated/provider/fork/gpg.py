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
