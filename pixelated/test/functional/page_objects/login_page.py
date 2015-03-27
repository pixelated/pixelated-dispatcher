#
# Copyright (c) 2015 ThoughtWorks, Inc.
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

from base_page_object import BasePageObject
from selenium.common.exceptions import TimeoutException


class LoginPage(BasePageObject):
    def __init__(self, context, timeout=10):
        self._locators = {
            'username': 'input#email',
            'password': 'input#password',
            'login_button': 'input[type=submit]',
            'hive_svg': 'svg#hive'
        }
        super(LoginPage, self).__init__(context, timeout)

    def enter_username(self, username):
        self._username_field().send_keys(username)
        return self

    def enter_password(self, password):
        self._password_field().send_keys(password)
        return self

    def login(self):
        self._login_button().click()
        return self

    def _username_field(self):
        return self._find_element_by_locator(self._locators['username'])

    def _password_field(self):
        return self._find_element_by_locator(self._locators['password'])

    def _login_button(self):
        return self._find_element_by_locator(self._locators['login_button'])

    def wait_intersitial_page(self, time=60):
        if self._is_intersitial_page_displayed():
            self._wait_element_to_be_removed(self._locators['hive_svg'], time)

    def _is_intersitial_page_displayed(self):
        try:
            self._find_element_by_locator(self._locators['hive_svg'], 2)
            return True
        except TimeoutException:
            return False
