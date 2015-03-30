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

from behave import given
from .page_objects import LoginPage


@given('I login as "{user}" with password "{password}" to an organization install of pixelated')
def impl(context, user, password):
    context.pixelated_email = user + '@try.pixelated-project.org'
    login_page = LoginPage(context)
    login_page.enter_username(user).enter_password(password).login()
    login_page.wait_intersitial_page()
