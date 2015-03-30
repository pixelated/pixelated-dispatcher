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


class ComposeBox(BasePageObject):
    def __init__(self, context, timeout=10):
        self._locators = {
            'subject': 'input#subject',
            'body': 'textarea#text-box',
            'to': 'input.tt-input',
            'send_button': 'button#send-button',
            'compose_box': 'div#compose-box'
        }
        super(ComposeBox, self).__init__(context, timeout)

    def enter_body(self, body):
        self._body_field().send_keys(body)
        return self

    def enter_subject(self, subject):
        self._subject_field().send_keys(subject)
        return self

    def enter_recipients(self, recipients):
        if type(recipients) is list:
            for recipient in recipients:
                self.enter_recipient(recipient)
        else:
            self.enter_recipient(recipients)
        return self

    def enter_recipient(self, recipient):
        self._to_field().send_keys(recipient)
        self._to_field().send_keys('\n')
        return self

    def send_mail(self):
        self._send_mail_button().click()

    def wait_compose_box_to_disapear(self):
        self._wait_element_to_be_removed(self._locators['compose_box'], 30)

    def _subject_field(self):
        return self._find_element_by_locator(self._locators['subject'])

    def _body_field(self):
        return self._find_element_by_locator(self._locators['body'])

    def _to_field(self):
        return self._find_element_by_locator(self._locators['to'])

    def _send_mail_button(self):
        return self._find_element_by_locator(self._locators['send_button'])
