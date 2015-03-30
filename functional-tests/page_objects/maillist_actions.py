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


class MailListActions(BasePageObject):
    def __init__(self, context, timeout=10):
        self._locators = {
            'compose_mail_button': 'div#compose-mails-trigger',
            'delete_selected_button': 'input#delete-selected',
            'delete_successful_message': '//span[contains("Your messages were moved to trash!")]'
        }
        super(MailListActions, self).__init__(context, timeout)

    def open_compose_box(self):
        self._compose_mail_button().click()

    def delete_selected_mails(self):
        self._delete_selected_button().click()

    def wait_delete_confirmation(self):
        self._delete_successful_message()

    def _compose_mail_button(self):
        return self._find_element_by_locator(self._locators['compose_mail_button'])

    def _delete_selected_button(self):
        return self._find_element_by_locator(self._locators['delete_selected_button'])

    def _delete_successful_message(self):
        return self._find_elements_by_xpath(self._locators['delete_successful_message'])
