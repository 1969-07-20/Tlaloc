<img src="https://github.com/1969-07-20/Tlaloc/blob/main/img/TlalocLogo03.jpg" width="512" height="512" />

# Miscellaneous Utilities

This directory contains miscellaneous utilities that support the main Tlaloc program.

- [config_validator.py](https://github.com/1969-07-20/Tlaloc/blob/main/etc/config_validator.py) is a utility that detects JSON syntax errors in the configuration file.  It is intended to be run on the configuration file when changes are made.  When this is done prior to running Tlaloc it can save avoid runs of Tlaloc due to syntax errors in the configuration file.
- [daily_checker.py](https://github.com/1969-07-20/Tlaloc/blob/main/etc/daily_checker.py) is a utility that is intended to be run periodically, typically every day, to summarize the data that has been gathered that day and to report any errors detected.
- [monthly.sh](https://github.com/1969-07-20/Tlaloc/blob/main/etc/monthly.sh) is a bash script which combines the daily logs for a month into a single Tar+Gzip file.
- [tlaloc_aggregator.py](https://github.com/1969-07-20/Tlaloc/blob/main/etc/tlaloc_aggregator.py) is a utility that is intended to be run on the output of [monthly.sh](https://github.com/1969-07-20/Tlaloc/blob/main/etc/monthly.sh) to combine a month's worth of daily logs into a single log.

# License
Copyright 2024 Tlaloc Labs LLC

This file is part of Tlaloc.

Tlaloc is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
