# Configuration and Control
Tlaloc has an extensive set of runtime parameters which control most aspects of Tlaloc's function.  These runtime parameters are exposed to the user giving the user fine control over Tlaloc.  However, reasonable defaults are provided for all parameters which minimizes the number of runtime parameters the user must specify in order to function as desired.

When the user wishes to tailor some aspect Tlaloc's function to meet their specific needs, the relevant parameter, can be supplied via the command line or via a parameter file.  There are two sets of runtime parameters.  One set controls the overall execution of Tlaloc.  These parameters can be set via the command line or via the configuration file.  The other set control the execution of the classes which query the various sources.  These parameters can be set via the configuration file only.  When the user supplies a value for a runtime parameter via the command line as well as the configuration file, the value on the command line has greater precedence than value provided in the configuration file.

For the classes which query the various data source, Tlaloc has a sophisticated four-step scheme for determining the runtime parameters.
- First, the base class from which all source classes are derived creates most, if not all, data members for a class.  Default values are assigned to all data members.  The default values ensure Tlaloc reasonably with minimum input by the user.
- Second, the base class will override the default values of data members for which new values have been provided for the base class in the configuration file.
- Third, where applicable, the derived class will override the values provided by the base class with default values for the derived class.
- Fourth, when the configuration file has a value specific to a derived class, any previous value is overwritten with the value in the config file specific to that derived class.

## Command Line Arguments
The following is a list of Tlaloc's command line arguments

- `-v, --version` -- Print out version.
- `--cur_dir` -- (string)  Override the current working directory.
- `--log_dir` -- (string)  Override the directory where logs are stored ('~/logs').
- `--config_file` -- (string)  Override the default name of the file with the user-supplied run-time parameters ('config.txt')
- `--cred_file` -- (string)  Override the default name of of the file with the credentials for sources which require authentication ('credentials.txt')
- `--skip_query` -- (boolean)  If true, skip making queries; no queries will be made, no responses, real or fake, will be processed.
- `--dry_run` -- (boolean)  Don't query data sources. Instead respond with a canned response read from a file.  Use case:  test handling of one particular response.
- `--production` -- (boolean)  If run in production mode, normal market open and close times are observed.  If not in production mode, queries will be made without regard to the sources' normal time windows.
- `--playback` -- (boolean)  Run in playback mode.  Query responses read from file called ‘combined.txt'.
- `--skip_first_day` -- (boolean)  Don't make any queries until next calendar day.  Allows restarting program before midnight without exceeding the daily limit on the number of queries of some sources.
- `--offset_begin` -- (boolean)  Offset times queries are made by an hour.  This can be used to run multiple copies of the program without both making the same queries at the same time.
- `--shuffle_queries` -- (boolean)  If true, shuffle the order in which stocks are queried.
- `--enable_ticker` -- (boolean)  Publish results after messaging raw data.
- `--skip_log_quotes` -- (boolean)  Both processes skip logging the raw responses they receive.
- `--skip_log_ticker` -- (boolean)  Skip logging the ticker output produced.
- `--proxies` -- (string)   String with proxy information
- `--ca_cert` -- (string)   String with the location of the file with the certificate for TLS when a proxy is used.
- `--debug` -- (string)   String with comma separated list of debug options.
- `--sources` -- (string)   String with comma separated list of sources.
- `--symbols` -- (string)   String with comma separated list of symbols to query.

## Monitoring and Debugging
The program allows for several types of debug to be turned on and off independently of the others.  The debug options can be controlled from either the command line or the configuration file.  Each type of debug defaults to off.  Inclusion of a type of debug on the command line or in the configuration file activates the respective types of debug.  The final set of debug types is the union of the sets specified on the command line and configuration file.

- `stock` -- Print out the list of stocks involved in each query.
- `query` -- Print a one line summary of every query prior to its being sent over the network.
- `query_raw` -- Print to the console the contents of the raw queries.
- `query_ugly` -- Print to the console the UNFORMATTED JSON structure created from the query response.
- `query_pretty` -- Print to the console the FORMATTED JSON structure created from the query response.
- `query_extract` -- Currently a NoOp.
- `threads` -- Report on the initiation and retirement of threads created to handle queries of the sources.
- `src_attr_lvl0` -- Print out list of attributes for sources after phase 0:  global defaults
- `src_attr_lvl1` -- Print out list of attributes for sources after phase 1:  global overrides
- `src_attr_lvl2` -- Print out list of attributes for sources after phase 2:  source-specific defaults
- `src_attr_lvl3` -- Print out list of attributes for sources after phase 3:  source-specific overrides

## Configuration File
The configuration file is a file in the JSON format.  At the top level the following sections may or may not be present:  "global", "Generic" and zero or more source specific sections ("CNBC_Intraday", "CNBC_Daily", "Yahoo_Intraday", "Yahoo_Daily", "AlphaVantage_Daily", "MarketData_Daily", "IEX_Intraday", and "Reuters_Daily").  The "global" section has runtime parameters affecting the global (i.e. source independent) aspects of Tlaloc execution.  Parameters in "Generic" section impact the value the base class of all the source classes assigns to data members.  Values appearing in the "Generic" section potentially impact all source classes.  Finally, the values in the sections for the individual source classes impact just the corresponding source class.  This offers the user fine-grained control over Tlaloc's runtime behavior.

Unlike JSON, the format of Tlaloc's configuration file does support comments, both in the form of line comments as well as block comments.  Both types of comments are activated by an appropriate character sequence.  Line comments start with the three character sequence "\#\@\!" and go all the way to the next newline character.  Block comments begin with the triplet of characters "\#\@\>" and end with the next "\<\@\#".  Block comments can encompass multiple lines of the configuration file.  Comments are removed prior to the contents of the config file are parsed by the JSON parser.

To make things easier, a template config file is provided in the directory with Tlaloc's source code.  This template config file has all the sections and all the variables recognized in each section.  However, most of the config file is commented out.  To activate some aspect of the config, the line(s) realizing that aspect need to be uncommented.

Since the configuration file is in the JSON format it is parsed using a JSON parser.  One implication of this is that the file must be valid JSON.  The JSON format provides many benefits.  But it also has some demanding constraints.  An example is JSON is much pickier than Python about the placement of commas in lists and dictionaries.  In order to ensure the configuration file is valid JSON prior to Tlaloc runs, a simple Python program is provided which will ingest the configuration file and report whether it succeeded or not.  This utility program is called `config_validator.py` and is located in the `etc` directory.

The parameters in the "global" section control the overall execution of Tlaloc independent of all data sources.  The parameters in this section are in one-to-one correspondence with the command line parameters.  The following is a list of parameters in the "global" section along with a nominal default value.  Following the notional value is a very brief description.  More information can be obtained by referring to the corresponding command-line parameter and the example 'config.txt' file for the syntax.

- `"cur_dir":  "."` --   Make this the current working directory.
- `"log_dir":  "."` --   Store log files in this directory.
- `"config_file":  "config.txt"` --   Name of file with configuration parameters.
- `"creds_file":   "credentials.txt"` --   Name of file with the credentials for sources that require authentication.
- `"skip_query":  false` --   Preprocess only, don't make queries.
- `"dry_run":  false` --   Dry run.
- `"production":  true` --   Don't observe normal market times.
- `"playback": false` --   Run in playback mode.
- `"skip_first_day":  false` --   Skip the first day.
- `"offset_mkt_begin":  false` --   Offset hours by one hour.
- `"shuffle_queries":  true` --   Shuffle order of symbols when making queries.
- `"enable_ticker":  false` --   Enable the ticker.
- `"skip_log_quotes":  false` --   Skip logging messages received from the data sources.
- `"skip_log_ticker":  false` --   Skip logging messages sent over the ticker.
- `"proxies": {}` --   Dictionary with proxy configuration.
- `"ca_cert": ""` --   Name of file with certificate when using proxy.
- `"debug_options": {}` --   Dictionary with debug options
- `"source_list": {` --   Dictionary with list of sources to be used.
- `"symbols": [ "AAPL" ]` --   List with symbols for which data sources are queried.
- `"market_holidays": [ "24-09-02", "24-11-28", "24-12-25" ]` --   List of holidays for which the market is closed.

The parameters in the "generic" section are override the data members of the base class from which the classes for all sources are derived.  Parameters appearing in the "generic" section will be made available to all source classes.  Since the source classes are derived from the Generic base class, these parameters can be appear in the section for a specific source (e.g. "CNBC_Intraday") and only affect that derived class.

- `"batch_sleep_time": 13` --   Sleep time between batches of queries
- `"delta_quote": 900` --   Time between queries for the same symbol.
- `"dry_run_file": "exampleJSON_generic.txt"` --   Name of file to provide inputs in dry run
- `"pause_sleep": 10` --   Time between polls for resume while in the paused state
- `"hdr":  'Mozilla/5.0 (X11; Ubuntu..."` --   User agent string to add to header of queries
- `"map_symbols": {"FB": "META"}` --   Mapping from common symbol names to names recognized by this source
- `"max_batch": 10` --   Maximum number of symbols in one query to source
- `"max_threads": 10` --   Maximum number of concurrent queries
- `"mkt_beg_time": 1` --   Time in seconds since midnight for the time window to query this source opens
- `"mkt_end_time": 360000` --   Time in seconds since midnight for the time window to query this source closes
- `"mkt_time_zone": "America/New_York"` --   Time zone of markets
- `"poll_sleep_time": 0.25` --   Time in seconds a thread should sleep before polling if the las query completes
- `"query_raw_norm": " *\n *"` --   Regex used to normalize raw query
- `"shuffle_queries": False` --   Shuffle the order of the symbols in which this source is queried
- `"timeout": 3.5` --   Baseline time for a query to timeout.
- `"to_backoff": 1.5` --   The ratio which the time between retries of queries is backed off for failed queries.

# License
Copyright 2024 Tlaloc Labs LLC

This file is part of Tlaloc.

Tlaloc is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
