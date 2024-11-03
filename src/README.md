# Tlaloc Source Code

This directory contains the source code for the Tlaloc program.

- [tlaloc.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/tlaloc.py) is the starting point for Tlaloc as well as hosts executive logic.
- [Source_Generic.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_Generic.py) is the class from which all of the following data source class classes are derived.  Source_Generic provides the logic shared by all source classes such as how to query remote servers, thread management, etc.

- [Source_AlphaVantage_DailySummary.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_AlphaVantage_DailySummary.py) is a data source class which queries AlphaVantage once a day for each stock shortly after the market has closed.
- [Source_CNBC_DailySummary.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_CNBC_DailySummary.py) is a data source class which queries CNBC once a day for each stock shortly after the market has closed.
- [Source_CNBC_IntradayQuote.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_CNBC_IntradayQuote.py) is a data source class which periodically gets delayed quotes from CNBC during market hours.
- [Source_IEX_IntradayQuote.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_IEX_IntradayQuote.py) is a (now defunct) data source class which periodically gets delayed quotes from IEX Cloud during market hours.
- [Source_MarketData_DailySummary.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_MarketData_DailySummary.py) is a data source class which queries MarketData once a day for each stock shortly after the market has closed.
- [Source_Reuters_DailySummary.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_Reuters_DailySummary.py) is a data (now defunct) source which queries Reuters once a day for each stock shortly after the market has closed.
- [Source_Yahoo_DailySummary.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_Yahoo_DailySummary.py) is a data source class which queries Yahoo Finance once a day for each stock shortly after the market has closed.
- [Source_Yahoo_IntradayQuote.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_Yahoo_IntradayQuote.py) is a data source class which periodically gets delayed quotes from Yahoo Finance during market hours.

- [Source_Playback.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/Source_Playback.py) is a data source class which gets reads its information from a file rather than query remote servers, providing a playback capability.

- [config.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/config.py) is a file which initializes Tlaloc's internal data structure in which runtime parameters are stored.
- [utils.py](https://github.com/1969-07-20/Tlaloc/blob/main/src/utils.py) is a file with generic utilities used by the Tlaloc program.

- [StartTlaloc.sh](https://github.com/1969-07-20/Tlaloc/blob/main/src/StartTlaloc.sh) is a file called by systemd to set up the Tlaloc runtime environment and start the program.

- [config.txt](https://github.com/1969-07-20/Tlaloc/blob/main/src/config.txt) is an example configuration which is to be adapted to local needs.
- [credentials.txt](https://github.com/1969-07-20/Tlaloc/blob/main/src/credentials.txt) is an example file for storing credentials.

# License
Copyright 2024 Tlaloc Labs LLC

This file is part of Tlaloc.

Tlaloc is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
