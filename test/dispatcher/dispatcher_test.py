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
import Cookie
import urllib

from mock import MagicMock
from tornado.testing import AsyncHTTPTestCase

from client.multipile import PixelatedHTTPError
from dispatcher import Dispatcher


__author__ = 'fbernitt'


class DispatcherTest(AsyncHTTPTestCase):
    def setUp(self):
        self.client = MagicMock()
        self.cookies = Cookie.SimpleCookie()
        super(DispatcherTest, self).setUp()

    def get_app(self):
        return Dispatcher(self.client).create_app()

    def _method(self, method, url, payload=None, auto_xsrf=True, **kwargs):
        if auto_xsrf and method == 'POST':
            self.cookies['_xsrf'] = '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'
            if payload and '_xsrf' not in payload:
                payload['_xsrf'] = '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'
            else:
                payload = {'_xsrf': '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'}

        payload = urllib.urlencode(payload) if payload else None
        headers = {
            'Cookie': self.cookies.output(header='').strip()
        }

        self.http_client.fetch(self.get_url(url), self.stop, follow_redirects=False, method=method, headers=headers,
                               body=payload)
        return self.wait()

    def _get(self, url, **kwargs):
        return self._method('GET', url, **kwargs)

    def _post(self, url, **kwargs):
        return self._method('POST', url, **kwargs)

    def test_redirect_to_login(self):
        response = self._get('/', follow_redirects=False)

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?next=%2F', response.headers['Location'])

    def test_invalid_login(self):
        self.client.get_agent.return_value = {}
        self.client.authenticate.side_effect = PixelatedHTTPError
        payload = {
            'username': 'tester',
            'password': 'invalid'
        }

        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?error=Invalid+credentials', response.headers['Location'])

    def test_invalid_agent(self):
        self.client.get_agent.side_effect = PixelatedHTTPError()
        payload = {
            'username': 'invalid_agent',
            'password': 'test',
            }
        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?error=Invalid+credentials', response.headers['Location'])

    def test_successful_login(self):
        self.client.get_agent.return_value = {}
        payload = {
            'username': 'tester',
            'password': 'test',
            }
        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/', response.headers['Location'])
        cookies = Cookie.SimpleCookie()
        cookies.load(response.headers['Set-Cookie'])
        self.assertTrue('pixelated_user' in cookies)

    def test_missing_xsrf_token_cookie(self):
        self.client.get_agent.return_value = {}
        payload = {
            'username': 'tester',
            'password': 'test',
            '_xsrf': '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'
        }

        response = self._post('/auth/login', payload=payload, auto_xsrf=False)

        self.assertEqual(403, response.code)

    def test_get_503_if_agent_not_running(self):
        self.client.get_agent_runtime.return_value = {'state': 'stopped'}

        self.cookies['pixelated_user'] = '2|1:0|10:1407749446|14:pixelated_user|12:InRlc3RlciI=|5ddd4ea06420119d9487c04cb1e83fa6665a9f42644b5969157d93abb2a6ed87'#;expires=Wed, 10 Sep 2014 09:30:46 GMT; Path=/'

        response = self._get('/some/url')

        self.assertEqual(503, response.code)
        self.assertEqual('Sorry, your agent is down', response.body)



