# Design and Implementation
The following is a discussion of the design and implementation of Tlaloc.  The target audience of the discussion are developers who are interested in how Tlaloc is implemented in software and possibly modifying or extending Tlaloc.  The discussion does not have information that is necessary to use Tlaloc.

# Goals
From a developer perspective, the following are developer visible attributes built into the program during development.

- Configurable:
    - Maximize the usage of general purpose logic and minimize the amount of logic tied to specific inputs or specific outputs:
        - Sources
        - Ticker symbols
    - All runtime parameters can be manipulated from command line arguments and/or from configuration files
        - Make all command line parameters optional with a reasonable default supplied in the code
        - For the many parameters read from files where a reasonable default exists, provide a default and make specifying them in configuration files optional.
- Normalize output to a standardized format
    - Remove extraneous information
        - Excess digits beyond significant digits
        - No use fields
            - Miscellaneous fields not part of the mathematical model
            - Extraneous fields about source of data
- Transparent operation
    - Repeatable
      - Deterministic response to often non-deterministic input.
      - Provide a playback mode
    - Make actions visible, primarily through extensive logging:
        - Logging enables after the fact reconstruction of program state which is important during post mortem debugging.
        - Log/printout runtime parameters in effect
        - Log/printout configuration parameters read from files
        - Each output is traceable to an input (source, time and data of query)
        - Option to log
            - input data stream
            - output data stream
            - transformations during normalization,
            - model updates during ingest of new information
- Flexible delivery of output
    - Support multiple clients, allowing each to subscribe to its own subset of the output data stream.
    - Minimize constraints put on clients regarding what can be done with the information this program provides them.  Tlaloc collects and distributes the information.
- Support highly asynchronous operation by employing an event driven approach based on a multi-process, multi-threaded architecture
- Minimize load on data sources, especially the free data sources.  This is done by
    - minimizing the number of queries, 
    - throttling the rate at which queries are made,
    - randomizing the order of and delays between queries, and
    - making queries during non-market hours, where possible.

# Processing Outline
The functionality of Tlaloc is implemented as two cooperating processes.  Process 1 makes the queries to the data sources.  The queries for the multiple data sources are time based.  Because of this Process 1's architecture is based on and optimized for event driven operation.

Process 1 performance is maximized when the time between the start of handling an event and when Process 1 becomes available to the next event is minimized.  Process 2 does two things to minimize this time.  First, it quickly creates a new thread to perform the query and second it tries to minimize the total amount of processing it does to handle an event.  This frees up Process 1 as quickly as possible, making it available to make additional queries.

To the extent practical, compute intensive functionality happens in Process 2.  Process 2 is optimized for throughput.  In Process 2, latency is allowed to suffer somewhat in order to maximize the amount of processing per unit time Process is capable of on average.  The processing that occurs in Process 2 is normalization of the incoming data, merging of normalized data into a mathematical model and communicating the changes in the mathematical model to clients.

## Process 1
The following are short explanations of the primary functions performed by Process 1.

### Initialization
Process 1's primary responsibility is to make queries to the data sources at appropriate times.  Since Process 1 forks to create Process 2, it has additional responsibilities related to start-up such as reading runtime parameters.

#### Process Runtime Parameters
At start-up Process 1 assimilates the runtime parameters for the current execution.  Reasonable defaults are hard-coded.  Should the user want to change a run-time parameter to a non-default value, depending on the parameter, the non-default value can be provided to Tlaloc in the form of a command line argument or one of the parameters in a parameter file.

#### Fork
After Process 1 has assimilated the runtime parameters and performed several other initialization tasks, Process 1 will fork into two processes, one of which continues on with Process 1's primary responsibilities, and the other process becomes Process 2 which performs the computationally intensive tasks on the incoming data stream.

#### Schedule
Process 1 generates queries to an arbitrary set of data sources.  Some data sources are queried during market hours and some during non-market hours.  Some types of queries are only made on certain days of the week.  Some sources are queried frequently (e.g. every 15 seconds for IEX Cloud) some much less frequently.  Process 2 accommodates all of these variations via a general purpose scheduling mechanism.

#### Daily Reset
Shortly after each midnight, both Process 1 and 2 close the current quote and ticker logs and open new logs.  (To ensure that the new logs reside in new files the date and time of the creation of the file is incorporated in the file name.)  In addition Process 1 resets any back-off for any data source.

### Query Issuance
- Time of day to issue queries (market hours, non-market hours)
- Frequency to issue queries
- Reissue failed queries

### Response Handling (logging and distribution)
- Log the response
- Basic error checking of response, reissue query if error detected.
- Send to Process 2

## Process 2
When a query response is received by Process 1 of the program, it is logged and then immediately forwarded to Process 2.  Process 2's responsibility is to assimilate the raw response, log the result and then send the digested information on to all clients subscribing to the digested data stream.

The following is an outline of the processing of the raw query stream which takes place in Process 2:
1. Normalize the data query responses to reduce the variability of the forms which the data can take in downstream processing.
2. Merge the data from disparate sources by using the data to update a common standardized mathematical representation of the companies associated with the stock.
3. Make the status of the mathematical models available to clients subscribing to the output.

### Normalization
- Use JSON parser to create Python data structure
- Remove irrelevant information
- Restructure (e.g. struct of arrays to array of structs)
- Local modifications (significant figures, change non-standard units to standard units, etc.)

### Merging Via Mathematical Model (implementation details)
- Add quantity to model if not present already
- Update model quantities when a new value for an existing quantity has been received
- Modify model quantities which depend on quantities which have been received

### Distribution
Data streams:
- Metadata stream
- Model diff stream

# Query Normalization
Normalization of the query responses consists of
- isolating the response for each symbol for those responses which have information for multiple symbols
- parsing the textual response using a JSON processor into Python data structures (hierarchical combinations of lists and dictionaries, numbers and strings)
- removing extraneous information
- reorganizing the data into more convenient forms, e.g. converting dictionary of arrays to an array of dictionaries.
- reformatting as needed, e.g. trimming numbers down to the number of significant digits appropriate for the quantity or changing to standardized units

## Normalization Language Intro
The normalization process for raw queries is performed by applying a series of operations to the data structure made from the raw JSON in the data source's response to this program's query.  These operations are a set of generic operations which can be applied to the response from any data source.  The sequence of operations applied to a given response is specific to the data source the response comes from.  The sequence of operations applied to a given data source is a crude type of program.

To minimize the amount of source-specific logic hardcoded in the actual Tlaloc source code, the sequence of operations to apply to the difference sources is read in at program start-up from a text file.  The use of generic operations and storage of the sequence in a text file minimizes the changes to Tlaloc's source code when the format of the raw data for a data source is changed or a new data source is added.

Given that the sequence of operations applied to the raw data is a type of program, it is appropriate to outline the simple programmer's model.  The operations are applied to the data structure created when JSON parses the response.

## Normalization Language Detail

The following is a list with the operations which can be used during normalization:

- A2D     This operation constructs a dictionary of arrays from an array of dictionaries.
- D2A     This operation constructs an array of dictionaries from a dictionary of arrays.
- ADD     This operation adds a field to the data structure at the specified location.
- DEL     This operation deletes a field from the data structure at the specified location.
- READ    This operation reads the contents at the specified location and stores it in the black board.
- WRITE   This operation writes the specified quantity on the black board to the specified location in the quote.
- RENAME  This operation renames the field at the specified location.
- ROOT    This operation restricts the data structure representing the quote to some subtree of the data structure.
- RCRS    This operation temporarily restricts the data structure being operated on to some subtree.  A specified subsequence of operations is performed on this subtree.  When that sequence of operations is complete, the data structure being operated on is restored to what it was before the RCRS operation.
- ZIP     This operation zips the specified arrays in the black board into an array of dictionaries and stores the result at the specified location in the black board.

The entities that the above operations act on are the data structure created when the JSON formatted response is parsed as well as a "Black Board".  The Black Board is a temporary storage area which can hold sub-data structures extracted from the response data structure.  The Black Board can hold more than one such sub-data structure.  Since it can hold more than one, each one is assigned a name or label which is used to access a particular sub-data structure added to the Black Board.  The Black Board is starts out blank at the beginning of normalization of every response.

The following is the generic format of the sequence of normalization operations it is a JSON parsable array of dictionaries.  (Line numbers, which do not appear in the original, were added to facilitate discussion of the content.)  The following is a very simple processing flow for normalizing responses from the "CI_QUOTE" data source (CNBC Intraday Quotes).  Line 01 is a comment line which is ignored.  Like `'//'` in C/C++ any text from the special strings `'#@!'` to the end of the line is a comment and silently removed from further consideration.

Line 02 ('`"CI_QUOTE": [`') and 15 ('`],`’) delimit an array of operations to be performed sequentially on responses for the CI_QUOTE source.  The array has two dictionaries, one for each of the two operations in this example.  The operations are "`ROOT`" (lines 03-08)  and "`DEL`" (lines 09-14).

The ROOT operation replaces the data structure being processed with one of its sub-data structure.  The DEL operation removes a field or sub-data structure, the "`cnbcId`" field in this case.  This field is deleted from the data structure because it is a field CNBC added for its own internal use and does not contain meaningful financial information about any stock symbol.

```
01  #@!  CNBC Intraday Quote
02  "CI_QUOTE": [
03      {
04          "op": "ROOT",
05          "args": [
06              "CI_QUOTE::QuickQuoteResult::QuickQuote"
07          ]
08      },
09      {
10          "op": "DEL",
11          "args": [
12              "CI_QUOTE::[*]::cnbcId"
13          ]
14      }
15  ],
```

Each operation in the array is a dictionary with two fields, "`op`" and "`args`".  The value of the "op" field is a string with the name of the operation to be performed, e.g. "DEL" on line 10..  The value of the "args" field is an array of argument strings.  The "DEL" operation needs only one argument - the location of the sub-structure to be deleted, "CI_QUOTE::[*]::cnbcId" in the case of this DEL operation.  The arguments are in a fixed, operation specific order..

The location for the DEL operation above is given as "CI_QUOTE::[*]::cnbcId".  This location is very similar to a string giving the full path to a file in Linux or Windows.  The double colons "::" are delimiters which break up the components of the address, in the same manner "/" does in Linux or "\" does in Windows.  And like a fully qualified file address in Linux or Windows, the paths become more localize as one reads from left to right.

Notice that one component of the address for the DEL operation (Line 12) is “[*]”.  This means that an array is location at this level and that the operation should be applied to every element in the array.  This is very similar to "*" appearing in a path name in Linux.  If a dictionary appeared at this location and the DEL operation should be applied to every field in the dictionary, a "{*}" would appear where "[*]" is used.

## Simple Normalization Example
The following is a before and after example when applying the normalization schema above.  The response is a CNBC intraday response which returns information about two stock symbols, NVDA and TSM.  The ellipses (...) indicate that much of the response has been removed for brevity.

The normalization schema has two operations, ROOT followed by DEL.  Notice that before normalization the quote has two upper layers "QuickQuoteResult" and "QuickQuote".  They are not present in the after quote because the ROOT has replaced the quote with one of its subtrees.  Also notice that the last field before the ellipses is "cnbcId" that is not present in the output of the normalization process.  This field has no information that is relevant to the financials and was eliminated by the DEL operation.

Quote before normalization:
```
{
    "CI_QUOTE": {
        "QuickQuoteResult": {
            "QuickQuote": [
                {
                    "symbol": "NVDA",
                    "last": "383.72",
                    "open": "384.89",
                    "high": "385.10",
                    "low": "383.53",
                    "volume": "801727",
                    "symbolType": "symbol",
                    "cnbcId": "0",
                    ...
                },
                {
                    "symbol": "TSM",
                    "last": "98.74",
                    "open": "98.68",
                    "high": "98.87",
                    "low": "98.60",
                    "volume": "353658",
                    "symbolType": "symbol",
                    "cnbcId": "0",
                    ...
                }
            ]
        }
    }
}
```

Quote after normalization:
```
{
    "CI_QUOTE": [
        {
            "symbol": "NVDA",
            "last": "383.72",
            "open": "384.89",
            "high": "385.10",
            "low": "383.53",
            "volume": "801727",
            "symbolType": "symbol",
            ...
        },
        {
            "symbol": "TSM",
            "last": "98.74",
            "open": "98.68",
            "high": "98.87",
            "low": "98.60",
            "volume": "353658",
            "symbolType": "symbol",
            ...
        }
    ]
}
```

# Implementation

## Architecture Overview

### Python
Tlaloc is written in Python.  Python is easy to write as well as read and provides more than sufficient performance.  Python has a vast array of packages which provide additional functionality beyond the base language.  Tlaloc uses several of these packages.

### Event Driven
The basic operation of the program is event driven.  Programs which handle user interaction with a graphical user interface are the stereotype of event driven software.  In the case of Tlaloc, the irregular input the program is dealing with is not human generated such as key strokes and mouse clicks.  But rather it is the passage of time which triggers events at irregular intervals (in this case time to initiate queries for information) as well as the highly variable delay in receiving of responses from remote web servers.

Tlaloc uses the Twisted framework (https://twisted.org) for the machinery to handle event driven operation and asynchronous communication.  At appropriate times, Twisted's event driven framework initiates a query to a data source by calling the appropriate methods of the class for that data source.  Twisted also handles the communication between the two main Tlaloc processes as well as the communication between Tlaloc and its data clients.

### Multiprocess and Multithreaded
In order to interact with multiple data sources concurrently, the program is highly multithreaded.  The Twisted event driven framework provides the infrastructure used by the program to realize multithreaded network IO.  The program is also multiprocess, dividing the work across two concurrently executing processes.  One process is responsible for making the queries.  When a response to a web query has been received, it is transferred to the second process for processing and further dissemination.

In the second process, the following will be performed on the query.
- normalize data:  remove irrelevant fields, restructure the response (dictionary of arrays to array of dictionaries), normalizing units, etc.
- combine multiple data streams into a single unified model
- communicate state of model to clients:
  - providing clients with a complete model upon start-up or at check-points, and
  - providing clients with ongoing deltas, thereby minimizing bandwidth usage by not resending data which has not changed.
Much of the processing envisioned for the second process is yet to be implemented.

Because the program is highly multithreaded, the program is written to minimize accesses to common resources by multiple threads.  Where access to common resources cannot be avoided, access from multiple threads is serialized by a common lock.

### Data Source Classes
The program is intended to be able to process a set of data sources and accommodate that set evolving over time.  Each data source has its own peculiarities.  The program tries to accommodate the peculiarities of the data source as well as compartmentalize a data source' peculiarities by having a different class for each data source.  In order to impose uniformity of the interfaces of the source-specific classes, they are all derived from a common parent class "Source_Generic".

#### Standard Methods
The classes provide source-specific adapters between the sources and the main part of the program.  The classes have a uniform set of methods.  The program calls these methods to perform standardized operations.  The implementation of these methods perform the specific set of operations applicable to its source in order to accomplish the standard operation.  The methods a class provides come from the base class, Source_Generic, as well as any additional or overridden methods in the derived class.  The standard set of methods a class provides are:

- `def __init__(self)`:  Method specified by the Python standard which is called at object creation.
- `def configure_lvl0(self)`:  (never overridden)  This method sets the data members for the base class.  Derived classes need define few, if any, additional members.
- `def configure_lvl1(self)`:  (never overridden)  This method updates the data members based on command line arguments and values in the configuration file for the base class.
- `def configure_lvl2(self)`:  (always overridden)  All derived classes should override this method and call it during initialization.  To meet the specific needs of the derived class, the values of base data members can be overridden and additional data members in this method.
- `def configure_lvl3(self)`:  (never overridden)  This function overrides the values of derived class data members with values supplied in the configuration file associated specifically with the derived class.
- `def dump_src_attributes(self, level)`:  (never overridden)  Debug function which prints out a list with the names of all data members of the current object and their values.
- `def populate_stock_list(self, stock_list)`:  (never overridden)  During initial configuration this method populates the list of stocks.  Some symbols need special handling for a source such as remapping to a non-standard string or skipping altogether.
- `def make_query_requests(self, batch_list, query, query_sanitized, )`:  (never overridden)  This function queries the remote server using the Python requests module.
- `def make_query_urllib(self, batch_list, query, query_sanitized, )`:  (never overridden)  This function queries the remote server using the Python urllib module.
- `def make_query_custom(self, batch_list, query, query_sanitized, )`:  (sometimes overridden)  When the generic process of generating the URL is insufficient, such as for the Yahoo sources and it large number of queries which can be made, this method can be overridden to make the custom query URLs.
- `def is_work_day(self, day)`:  (sometimes overridden)  Method to determine if object should query source based on day.  Some data sources are queried for information seven days a week, some only on days the market is open.
- `def review_query_list(self, list_in, query_type, num_query_types, time_hack)`:  (sometimes overridden)  Overridden if the source is queried for a subset of the list of stocks in a day (to avoid surpassing daily limits on API calls).  This function determines which stocks the source should be queried today.
- `def reset_backoff(self, backoff_list)`:  (never overridden)  This method resets the back-off state for all symbols for this source.
- `def init_threads_done(self, thread_timestamp, num_threads)`:  (never overridden)  This method sets up the coordination between the initiation of a query and the completion of a query.
- `def expire_threads_done(self, thread_timestamp)`:  (never overridden)  This method tears down the coordination between the initiation of a query and the completion of a query.
- `def mark_thread_running(self, thread_timestamp, thread_num)`:  (never overridden)  This method sets the data member recording the state of a query thread to indicate the query is in progress.
- `def mark_thread_done(self, thread_timestamp, thread_num)`:  (never overridden)  This method sets the data member recording the state of a query thread to indicate the query is has completed.
- `def all_threads_done(self, thread_timestamp)`:  (never overridden)  This method sets the data member recording the state of all query threads to indicate all queries have completed.
- `def threads_done_status(self, thread_timestamp)`:  (never overridden)  This method returns the state of the data member recording the state of a query.
- `def make_query(self, thread_timestamp, thread_num, query_type_src, batch_list, )`:  (never overridden)  This method is the overarching method which performs the execution of a query.  Most importantly, calls make_query_requests(), make_query_urllib() or make_query_custom() as appropriate.
- `def process_query(self, batch_str, query_raw, query, log_timestamp, query_type, version)`:  (never overridden)  This method performs first level processing of responses to queries:  logs the response, converts it to a dictionary, etc.
- `def query_driver_pt1(self)`:  (never overridden)  This method (a) creates list of stocks in query, (b) executes query, and (c) schedules next batch if not all stocks have been processed.
- `def query_driver_pt2(self, thread_timestamp)`:  (never overridden)  This method (a) checks on whether threads are still running, (b) schedule next poll if one or more threads are still running.
- `def run_recurring_query(self)`:  (never overridden)  This method (a) schedules next query, (b) determines if market is open, and (c) initiates query if market is open.
- `def make_batch_list_pt1(self, stock_list)`:  (never overridden)  This method is called by query_driver_pt1() to make the list of stocks to be queried in a single query in batch mode.
- `def make_batch_list_pt2(self, stock_list)`:  (never overridden)  This method is called by process_query() to determine the list of stocks in a single query in batch mode.
- `def get_query_types(self)`:  (always overridden)  Determines which set of queries should be made to this source today.  This allows for the different set of queries to be spread out of multiple days.  Primarily used for Yahoo for which a large number of query types are supported, most of which change very slowly, e.g. balance sheet information, and therefore don't need to be queried every day.
- `def id_quote(self, quote)`:  (always overridden)  Method classes provide to identify whether a test URL has the form of the URLs it uses.
- `def make_stock_entry(self)`:  (always overridden)  Placeholder method intended for use when processing (digesting) the response to a query to a source.
- `def make_query_url(self, batch_list)`:  (always overridden)  Basic method a class provides to construct the URL appropriate for that specific source.
- `def response_to_dictionary(self, query_raw)`:  (always overridden)  Basic method for converting response to a Python dictionary.  This will be the place where much additional logic is added as the normalization process matures.
- `def symbol_rollcall(self, batch_list, query_json, query)`:  (always overridden)  Helper function to ensure that information in the response is in one-to-one correspondence with the stocks for which information was requested.
- `def normalize_query(self, query_raw)`:  (always overridden)  Placeholder function which will see significant expansion in the future.  This function is called to normalize the query to a form with less variability and less useless content.
- `def get_query_stock(self, qry_symbol, query_json)`:  (always overridden)  Helper function which performs first level of extracting the response for a specific stock from the raw response which may have the response for multiple stocks.
- `def parse_query_response(self, query_stock, symbol, log_timestamp, query_type, version)`:  (always overridden)  Method which extracts semantic info from response.  Called after the response has been processed at a syntactic level.
- `def timeWindowCheck(self, time_zone, hhmmss_beg, hhmmss_end)`:  (never overridden)  Method which determines if the source should be making queries at the current time given the configuration of the source.

#### Standard Members
The following are the data members defined in the Generic source from which all actual sources are derived.  The classes for a few data sources define a handful of additional data members to support the specialized functionality that goes with that data source.

- `self.version`
- `self.shuffle_queries`
- `self.mkt_beg_today`
- `self.mkt_end_today`
- `self.delta_quote`
- `self.poll_sleep_time`
- `self.batch_sleep_time`
- `self.max_threads`
- `self.max_batch`
- `self.pause`
- `self.pause_sleep`
- `self.timeout`
- `self.to_backoff`
- `self.map_symbols`
- `self.skip_list`
- `self.mkt_time_zone`
- `self.mkt_beg_time`
- `self.mkt_end_time`
- `self.skip_today`
- `self.query_raw_norm`
- `self.hdr`
- `self.query_type_src`
- `self.dry_run_file`

The following is a list of data members which affect functionality visible to the user and therefore could be of interest to a user of the program for configuring the runtime behavior.  Example values are given for the CNBC Intraday source:
- `self.delta_quote = 15 * 60` -- 'delta_quote' is the time, in seconds, between queries of the full list of symbols.  Said another way, under normal circumstances every symbol is queried every 'delta_quote' seconds.
- `self.poll_sleep_time = 0.25` -- 'poll_sleep_time' is the time the program sleeps prior to every check (poll) whether a query has completed or not.
- `self.batch_sleep_time = 10` -- 'batch_sleep_time' is the time the program waits between issuing a query for another set of stock symbols.  It is good practice to assign different 'delta_quote' times for each daily data source in order to ensure they do not form a systematically repeating load profile.
- `self.max_threads = 10` -- 'max_threads' is the maximum number of active queries a class can have outstanding at the same time.  If this limit is met the class will wait to issue new queries until the number of outstanding queries drops below this maximum.
- `self.max_batch = 10` -- 'max_batch' is the maximum number of symbols included in a single query. Larger values decrease the number of queries made while smaller values makes it easier on the data source to generate the query response.  About half the data sources can only reply to one symbol in a query.  For those sources that can handle multiple symbols in a query, the program uses medium-sized values (10, 20, or 30) to simultaneously reduce the number of queries, but not include so many symbols to make responding to the query cumbersome.
- `self.timeout = 3.5` -- 'timeout' is the starting value for the amount of time the program will wait before it declares a query to have failed and tries again.
- `self.to_backoff = 3.0 / 2.0` -- 'to_backoff' is the ratio of the new value for timeout to the old value when the program is repeatedly reissuing failed queries.  The back-off reduces the frequency, and therefore the load, the program presents to the remote data source when things go wrong.  There are times when the remote data source fails to satisfy a query and there are times the failure is due to events on the local computer.
- `self.map_symbols = { 'FB':   'META', }` -- 'map_symbols' is a list of symbols which have a name unique to the data source.  'map_symbols' is a dictionary which maps the name Tlaloc's uses for a symbol to the specific names used by the source.  Often the renaming that is required is to append the name of an exchange to the symbol name.  However, in the case of Facebook, Facebook changed its ticker symbol from 'FB' to 'META'.  'map_symbols' reflects this change.
- `self.skip_list = []` -- Not all data sources have all symbols.  'skip_list' is a list of symbols for which the current data source does not provide information.
- `self.mkt_beg_time = 93000` and `self.mkt_end_time = 161959` -- 'mkt_beg_time' and 'mkt_end_time' define the time window in which the program will make queries to the data source.  These times are in the time zone specified in `self.mkt_time_zone`.  For intraday data sources, there is a tight coupling between when the market is open and when classes are active.  For the daily classes, the 'market' aspect of the times is not applicable, and this 'mkt_beg_time' and 'mkt_end_time' merely define when the class should make queries to the data source, which in the case of daily sources should be done after the market closes.

## Logging
The program has several types of debug which can be turned on or off.  Typically, the 'query' log option (print one line summary of each query) is turned on and the rest turned off.  This debug goes to the console.  The query responses have the data we desire in raw form.  By default, these responses are logged to a log file.  Because of the volume and the importance of this log stream, it receives special treatment.  Every night a new file is generated a few second after midnight.

A log entry is made for every query which generates a response.  Each entry consists for four lines with a blank line separating each entry.  The first line has key metadata such as which data source being queried, the time of query as well as other key metadata.  The next line has the list of stocks for which the query seeks information.  This is followed by a line with the URL to which the query was made.  If a token or other authentication information was included in the URL, the authentication information is redacted.  The last line is the contents of the response.  The response can be many kilobytes long depending on the query.

## Long Term Running Strategy
This program is intended to run for indefinite periods of time -- weeks if not months.  In this time it is expected to handle many gigabytes of data and it is expected to run reliably.  This mode of operation poses a unique set of challenges with respect to overseeing its operation.  First, by running for such long periods of time the program is subject to being affected by infrequent events such as power and internet outages, both locally as well as remotely at the data sources.  Second, periodic review is needed as it is running to ensure that it is running correctly.

### Power etc.:  systemd
To address the problem of power outages, the Raspberry Pi is configured to start the program as a systemd service automatically at boot time.  The systemd service is configured to automatically restart the program if it is down for more than a minute.  The following is the .service file which configures the systemd service:
```
[unit]
Description=Tlaloc Service
After=graphical.target
Requires=network.target

[Service]
Type=idle
User=pi
ExecStart=/usr/bin/bash  /home/pi/Tlaloc/StartTlaloc.sh
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

The following is the script that systemd runs to start the program:
```
#! /usr/bin/bash

#  Create name of logfile
dateStr=`date "+%Y%m%d"`
timeStr=`date "+%H%M%S"`

logFile="/home/pi/ssLog_${dateStr}_${timeStr}.txt"

echo "logFile='$logFile'"


#  Activate the Miniconda environment
. /home/pi/miniconda3/bin/activate Tlaloc

#  List conda environments
conda info --envs

#  List packages in 'Tlaloc' environment
conda list -n Tlaloc

#  cd to the directory with the Tlaloc script and run it
cd ~/Tlaloc/
/home/pi/miniconda3/bin/python ./tlaloc.py  &> $logFile
```

### Internet Problems
To handle internet outages, the program pays close attention to the success or failure of the queries it makes.  When Tlaloc detects that a query times out or has received an invalid response the program will retry up to four times before declaring the query a failure.  When queries to a data source fails the program will double the time between queries until a query succeeds.  When a query succeeds the wait time between queries returns to normal.

Increasing the time between queries throttles the rate at which queries are made when there is a high probability they will fail under the assumption that the expected time until the query succeeds again is proportional to the time it has been down.

### Monitoring:  integrity checking script
A simple Python program was written to scan the logs to make a basic assessment of the integrity of the data and the correct functioning of the program.  The author's standard operating procedure is to run this script once a day to determine Tlaloc's state of health.  The script cannot detect all possible types problems but it does run a battery of simple integrity checks in an effort to detect most common problems.

Given a start date as well as an end date (if not the current date), the integrity checker determines what queries failed, the number of successful and failed queries of each type, the amount of disk spaced used by the program and the amount of disk space is available in the current file system.

## Dependencies

### Modules:  Python Standard Library and Third-Party
Tlaloc has several dependencies on modules which have become part of the standard Python ecosystem as well as a few third party modules.

The following is a list of the standard Python modules on which Tlaloc depends:
- argparse
- datetime
- http
- json
- logging
- math
- multiprocessing
- os
- pathlib
- pprint
- random
- re
- signal
- sys
- threading
- time
- platform
- urllib

The following are third-party packages on which Tlaloc depends.
- requests
- twisted
- curl_cffi
- yahooquery (locally modified)

### Twisted for multi-processing / multithreading
Twisted (https://twisted.org) is an "event-driven networking engine".  The Twisted framework handles the event-driven aspects of Tlaloc.  This includes much of the mechanical aspects of Tlaloc's asynchronous execution as well as communication between Tlaloc's Process 1 and Process 2.  Twisted has been used in prototypes of Tlaloc's interaction with clients, including authentication as well as securing the communication via TLS as well as handling authentication.

### Yahoo Query
Yahoo is an excellent source of financial information.  It provides an extensive range of information.  The range of calls made by Tlaloc to Yahoo Finance' API is considerably larger than that of any other data source.  To handle this, Tlaloc uses a middle layer called Yahoo Query to harness Yahoo Query's high-level of sophistication in accessing the Yahoo Finance' API.  The version of Yahoo Query which Tlaloc uses is slightly modified from the official distribution of Yahoo Query found on Github (https://github.com/dpguthrie/yahooquery).

# License
Copyright 2024 Tlaloc Labs LLC

This file is part of Tlaloc.

Tlaloc is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
