#
# Copyright (c) 2014 ThoughtWorks, Inc.
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
import os

from leap.common import ca_bundle

from pixelated.bitmask_libraries.leap_config import AUTO_DETECT_CA_BUNDLE


def which_bootstrap_CA_bundle(provider):
    return _unicode_to_str(LeapCertificate(provider).auto_detect_ca_bundle())


def which_api_CA_bundle(provider):
    return _unicode_to_str(LeapCertificate(provider).api_ca_bundle())


class LeapCertificate(object):
    def __init__(self, provider):
        self._config = provider.config
        self._provider = provider
        self._server_name = provider.server_name
        self._certs_home = self._config.certs_home

    def auto_detect_ca_bundle(self):
        if self._config.ca_cert_bundle == AUTO_DETECT_CA_BUNDLE:
            local_cert = self._local_server_cert()
            if local_cert:
                return local_cert
            else:
                return ca_bundle.where()
        else:
            return self._config.ca_cert_bundle

    def api_ca_bundle(self):
        cert_file = self._api_cert_file()

        if not os.path.isfile(cert_file):
            self._download_api_ca_bundle(cert_file)

        return cert_file

    def refresh_api_ca_bundle(self):
        cert_file = self._api_cert_file()
        self._download_api_ca_bundle(cert_file)

    def _api_cert_file(self):
        certs_root = self._api_certs_root_path()
        return os.path.join(certs_root, 'api.pem')

    def _api_certs_root_path(self):
        path = os.path.join(self._provider.config.leap_home, 'providers', self._server_name, 'keys', 'client')
        if not os.path.isdir(path):
            os.makedirs(path, 0700)
        return path

    def _download_api_ca_bundle(self, cert_file):
        cert = self._provider.fetch_valid_certificate()

        with open(cert_file, 'w') as file:
            file.write(cert)

    def _local_server_cert(self):
        cert_file = os.path.join(self._certs_home, '%s.ca.crt' % self._server_name)
        if os.path.isfile(cert_file):
            return cert_file
        else:
            return None


def _unicode_to_str(value):
    if isinstance(value, unicode):
        return str(value)
    else:
        return value
