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

from behave import when
from .page_objects import PixelatedPage


@when('I send an email to myself')
def impl(context):
    pixelated_page = PixelatedPage(context)
    pixelated_page.compose_and_send_email({
        'subject': 'Automated test, TBD (To Be Deleted)',
        'body': 'This is an automated test of Pixelated. Please do not delete this, it will be deleted automatically.',
        'recipients': context.pixelated_email
    })
