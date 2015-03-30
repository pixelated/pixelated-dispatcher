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

Feature: login and send mail

  Scenario Outline: user logs in, composes and send an email, then deletes it
    Given I login as "<user>" with password "<password>" to an organization install of pixelated
    When I send an email to myself
    Then I see the email on the mail list
    Then I delete the email
    Then I see it in the trash box
    And I delete it permanently

    Examples:
    | user  | password   |
    | alice | WuSh3ohse4 |
    | eve   | Voh0ohghai |
    | bob   | quuojoo1Su |
