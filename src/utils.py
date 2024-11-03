# -*- coding: utf-8 -*-

"""utils.py:  This file has various utilities that perform useful self-contained
   tasks.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

from datetime import timedelta
from datetime import date


def mkt_open_on_date(day):

    #  Only check for weekends and holidays on production runs
    if not config.runtime_params['production']:
        return True


    #  Market is not open on weekends
    if (5 == day.weekday()) or (6 == day.weekday()):
        return False


    #  Check against holidays
    day_str = "{:02d}-{:02d}-{:02d}".format(day.year % 100, day.month, day.day)

    if day_str in config.runtime_params['market_holidays']:
        return False


    #  It's not a weekend or holiday so the market must be open
    return True


def days_to_next_session (time_zone):

    done = False

    days_to_mkt = 0

    while not done:
        days_to_mkt = days_to_mkt + 1

        day = date.today(time_zone) + timedelta(days = days_to_mkt)

        done = mkt_open_on_date(day)


    return days_to_mkt
