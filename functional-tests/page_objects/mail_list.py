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


class MailList(BasePageObject):
    def __init__(self, context, timeout=10):
        self._locators = {
            'mail_items': '//li[contains(., "{sender}") and contains(., "{subject}")]'
        }
        super(MailList, self).__init__(context, timeout)

    def is_mail_on_list(self, sender, subject, timeout=None):
        try:
            self._find_first_mail(sender, subject, timeout)
            return True
        except TimeoutException:
            return False

    def is_mail_not_on_the_list(self, sender, subject):
        try:
            xpath = self._locators['mail_items'].format(
                sender=sender,
                subject=subject)
            self._wait_element_to_be_removed_by_xpath(xpath)
            return True
        except TimeoutException:
            return False

    def select_mail(self, sender, subject, timeout=None):
        mail = self._find_first_mail(sender, subject, timeout)
        self._find_element_by_locator('input', dom_context=mail).click()

    def _find_first_mail(self, sender, subject, timeout=None):
        xpath = self._locators['mail_items'].format(
            sender=sender,
            subject=subject)
        return self._find_elements_by_xpath(xpath, timeout)[0]
