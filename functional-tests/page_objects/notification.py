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


class Notification(BasePageObject):
    def __init__(self, context, timeout=10):
        self._locators = {
            'message_sent': '#user-alerts:contains("Your message was sent!")'
        }
        super(Notification, self).__init__(context, timeout)

    def wait_for_mail_sent_notification(self):
        print "Waiting for message sent notification"
        self._find_element_by_locator(self._locators['message_sent'])
        print "Notification found"
        return self
