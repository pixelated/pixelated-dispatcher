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

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By


class BasePageObject(object):
    def __init__(self, context, timeout=10):
        self.context = context
        self.timeout = timeout

    def _find_element_by_locator(self, locator, timeout=None, dom_context=None):
        locator_tuple = (By.CSS_SELECTOR, locator)
        self._wait_until(EC.visibility_of_element_located(locator_tuple), timeout or self.timeout)
        context = dom_context or self.context.browser
        return context.find_element_by_css_selector(locator)

    def _find_elements_by_locator(self, locator, timeout=None):
        locator_tuple = (By.CSS_SELECTOR, locator)
        self._wait_until(EC.visibility_of_element_located(locator_tuple), timeout or self.timeout)
        return self.context.browser.find_elements_by_css_selector(locator)

    def _find_elements_by_xpath(self, xpath, timeout=None):
        locator_tuple = (By.XPATH, xpath)
        self._wait_until(EC.visibility_of_element_located(locator_tuple), timeout or self.timeout)
        return self.context.browser.find_elements_by_xpath(xpath)

    def _wait_element_to_be_removed(self, locator, timeout=None):
        locator_tuple = (By.CSS_SELECTOR, locator)
        self._wait_until(EC.invisibility_of_element_located(locator_tuple), timeout or self.timeout)

    def _wait_element_to_be_removed_by_xpath(self, xpath, timeout=None):
        locator_tuple = (By.XPATH, xpath)
        self._wait_until(EC.invisibility_of_element_located(locator_tuple), timeout or self.timeout)

    def _wait_until(self, condition_function, timeout=None):
        wait = WebDriverWait(self.context.browser, timeout or self.timeout)
        wait.until(condition_function)
