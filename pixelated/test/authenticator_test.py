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
import unittest

from mock import MagicMock, patch

from pixelated.exceptions import UserNotExistError
from pixelated.users import Users, UserConfig
from pixelated.authenticator import Authenticator
from pixelated.bitmask_libraries.leap_config import LeapConfig
from pixelated.bitmask_libraries.leap_provider import LeapProvider
from pixelated.bitmask_libraries.leap_srp import LeapAuthException, LeapSRPTLSConfig


class AuthenticatorTest(unittest.TestCase):

    def setUp(self):
        self.users = MagicMock(spec=Users)
        self.provider = MagicMock(spec=LeapProvider)
        self.provider.api_uri = '/1/some/uri'

    def test_create_authenticator(self):
        Authenticator(self.users, self.provider)

    @patch('pixelated.authenticator.random.getrandbits')
    def test_add_credentials(self, getrandbits_mock):
        auth = Authenticator(self.users, self.provider)
        cfg = UserConfig('name', None)
        getrandbits_mock.return_value = 190076495833799431774420846029880681881

        self.users.config.return_value = cfg

        auth.add_credentials('username', 'password')

        expected_salt = '313930303736343935383333373939343331373734343230383436303239383830363831383831'
        expected_hashed_password = '9255ce9b33468968645f2d81a5054b7843ece5212695df9fadab9d26bb249a03a6c4e234bdc901ebbc288f648c26670255ceb55405da8f3589d34d889c8d4371'
        self.assertEqual(expected_salt, cfg['auth.salt'])
        self.assertEqual(expected_hashed_password, cfg['auth.hashed_password'])

        self.users.update_config.assert_called_once_with(cfg)

    def test_authenticate(self):
        cfg = UserConfig('name', None)
        cfg['auth.salt'] = '313930303736343935383333373939343331373734343230383436303239383830363831383831'
        cfg['auth.hashed_password'] = '9255ce9b33468968645f2d81a5054b7843ece5212695df9fadab9d26bb249a03a6c4e234bdc901ebbc288f648c26670255ceb55405da8f3589d34d889c8d4371'
        self.users.config.return_value = cfg

        auth = Authenticator(self.users, self.provider)

        self.assertFalse(auth.authenticate('name', 'invalid'))
        self.assertTrue(auth.authenticate('name', 'password'))

    def test_unicode_passwords_dont_cause_type_error(self):
        cfg = UserConfig('name', None)
        self.users.config.return_value = cfg

        auth = Authenticator(self.users, self.provider)
        auth.add_credentials('name', u'password')

        self.assertTrue(auth.authenticate('name', u'password'))

    def test_authenticate_not_existing_user(self):
        self.users.config.side_effect = UserNotExistError

        auth = Authenticator(self.users, self.provider)

        self.assertFalse(auth.authenticate('name', 'password'))

    @patch('pixelated.authenticator.which_api_CA_bundle')
    @patch('pixelated.authenticator.LeapSecureRemotePassword')
    def test_authenticate_with_leap_user_not_yet_known_locally(self, srp_mock, which_api_CA_bundle_mock):
        # given
        user_config = UserConfig('name', None)
        which_api_CA_bundle_mock.return_value = 'some bundle'
        self.users.has_user_config.return_value = False
        self.users.config.return_value = user_config

        # when
        auth = Authenticator(self.users, self.provider)
        result = auth.authenticate('name', 'password')

        # then
        srp_mock.return_value.authenticate.assert_called_once_with('/1/some/uri', 'name', 'password')
        self.users.add.assert_called_once_with('name')

        srp_mock.assert_called_once_with(tls_config=LeapSRPTLSConfig(ca_bundle='some bundle'))
        srp_mock.return_value.authenticate.assert_called_once_with('/1/some/uri', 'name', 'password')
        self.users.update_config.assert_called_once_with(user_config)
        self.assertTrue(result)

    @patch('pixelated.authenticator.which_api_CA_bundle')
    @patch('pixelated.authenticator.LeapConfig')
    @patch('pixelated.authenticator.LeapProvider')
    @patch('pixelated.authenticator.LeapSecureRemotePassword')
    def test_authenticate_with_leap_does_not_succed_if_login_fails(self, srp_mock, provider_mock, config_mock, which_api_CA_bundle_mock):
        which_api_CA_bundle_mock.return_value = 'some bundle'
        self.users.has_user.return_value = False
        self.users.config.side_effect = UserNotExistError
        provider_mock.return_value.api_uri = '/1/some/uri'
        srp_mock.return_value.authenticate.side_effect = LeapAuthException

        auth = Authenticator(self.users, self.provider)

        result = auth.authenticate('name', 'password')

        self.assertFalse(self.users.add.called)
        self.assertFalse(result)

    @patch('pixelated.authenticator.which_api_CA_bundle')
    @patch('pixelated.authenticator.LeapSecureRemotePassword')
    def test_authenticate_with_missing_user_config(self, srp_mock, which_api_CA_bundle_mock):
        # given
        user_config = UserConfig('name', None)
        which_api_CA_bundle_mock.return_value = 'some bundle'
        self.users.has_user.return_value = True
        self.users.has_user_config.return_value = False
        self.users.config.return_value = user_config

        # when
        auth = Authenticator(self.users, self.provider)
        result = auth.authenticate('name', 'password')

        # then
        srp_mock.return_value.authenticate.assert_called_once_with('/1/some/uri', 'name', 'password')
        self.users.add.assert_called_once_with('name')

        srp_mock.assert_called_once_with(tls_config=LeapSRPTLSConfig(ca_bundle='some bundle'))
        srp_mock.return_value.authenticate.assert_called_once_with('/1/some/uri', 'name', 'password')
        self.users.update_config.assert_called_once_with(user_config)
        self.assertTrue(result)
