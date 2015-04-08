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
import random
import binascii
import scrypt

from pixelated.exceptions import UserNotExistError

from pixelated.bitmask_libraries.leap_config import LeapConfig
from pixelated.bitmask_libraries.leap_provider import LeapProvider
from pixelated.bitmask_libraries.leap_srp import LeapSecureRemotePassword, LeapAuthException, LeapSRPTLSConfig
from pixelated.bitmask_libraries.leap_certs import which_api_CA_bundle

from pixelated.common import logger


def str_password(password):
    return password if type(password) != unicode else password.encode('utf8')


class Authenticator(object):

    __slots__ = ('_users', 'provider')

    SALT_HASH_LENGHT = 128

    def __init__(self, users, provider):
        self._users = users
        self.provider = provider

    def add_credentials(self, username, password):
        salt = binascii.hexlify(str(random.getrandbits(128)))
        bytes = binascii.hexlify(scrypt.hash(str_password(password), salt))

        cfg = self._users.config(username)
        cfg['auth.salt'] = salt
        cfg['auth.hashed_password'] = bytes

        self._users.update_config(cfg)

    def authenticate(self, username, password):
        if self._users.has_user_config(username):
            return self._is_valid_credentials(username, password)
        else:
            if self._can_authorize_with_leap_provider(username, password):
                self._users.add(username)
                self.add_credentials(username, password)
                return True
            else:
                return False

    def _is_valid_credentials(self, username, password):
        try:
            cfg = self._users.config(username)
            salt = cfg['auth.salt']
            hashed_password = binascii.hexlify(scrypt.hash(str_password(password), salt))
            return hashed_password == cfg['auth.hashed_password']
        except UserNotExistError:
            return False

    def _can_authorize_with_leap_provider(self, username, password):
        tls_config = LeapSRPTLSConfig(ca_bundle=which_api_CA_bundle(self.provider))
        srp = LeapSecureRemotePassword(tls_config=tls_config)

        try:
            srp.authenticate(self.provider.api_uri, username, password)
            return True
        except LeapAuthException, e:
            logger.error('Failure while authenticating with LEAP: %s' % e)
            return False
