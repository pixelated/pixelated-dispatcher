
import random
import binascii
import scrypt

from pixelated.exceptions import UserNotExistError

from pixelated.provider.leap_config import LeapConfig
from pixelated.provider.leap_provider import LeapProvider
from pixelated.provider.leap_srp import LeapSecureRemotePassword, LeapAuthException
from pixelated.provider.leap_certs import which_bundle


def str_password(password):
    return password if type(password) != unicode else password.encode('utf8')


class Authenticator(object):

    __slots__ = ('_users', '_leap_provider_hostname', '_leap_provider_ca')

    SALT_HASH_LENGHT = 128

    def __init__(self, users, leap_provider_hostname=None, leap_provider_ca=True):
        self._users = users
        self._leap_provider_hostname = leap_provider_hostname
        self._leap_provider_ca = leap_provider_ca

    def add_credentials(self, username, password):
        salt = binascii.hexlify(str(random.getrandbits(128)))
        bytes = binascii.hexlify(scrypt.hash(str_password(password), salt))

        cfg = self._users.config(username)
        cfg['auth.salt'] = salt
        cfg['auth.hashed_password'] = bytes

        self._users.update_config(cfg)

    def authenticate(self, username, password):
        if self._users.has_user(username):
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
        config = LeapConfig(ca_cert_bundle=self._leap_provider_ca)
        provider = LeapProvider(self._leap_provider_hostname, config)
        srp = LeapSecureRemotePassword(ca_bundle=which_bundle(provider))

        try:
            srp.authenticate(provider.api_uri, username, password)
            return True
        except LeapAuthException:
            return False
