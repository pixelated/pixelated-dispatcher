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

from compose_box import ComposeBox
from maillist_actions import MailListActions
from mail_list import MailList
from tag_list import TagList


class PixelatedPage(object):
    def __init__(self, context, timeout=10):
        self.maillist_actions = MailListActions(context)
        self.compose_box = ComposeBox(context)
        self.mail_list = MailList(context)
        self.tag_list = TagList(context)

    def compose_and_send_email(self, mail_fields):
        self.maillist_actions.open_compose_box()
        self.compose_box.enter_subject(mail_fields['subject']).enter_body(mail_fields['body']).enter_recipients(mail_fields['recipients'])
        self.compose_box.send_mail()
        self.compose_box.wait_compose_box_to_disapear()
        return self

    def delete_mail(self, sender, subject, timeout=None):
        self.mail_list.select_mail(sender, subject, timeout)
        self.maillist_actions.delete_selected_mails()
        assert(self.mail_list.is_mail_not_on_the_list(sender, subject))
        return self

    def is_mail_on_list(self, sender, subject, timeout=None):
        assert(self.mail_list.is_mail_on_list(sender, subject, timeout))

    def go_to_trash(self):
        self.tag_list.go_to_trash()
