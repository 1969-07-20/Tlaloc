<img src="https://github.com/1969-07-20/Tlaloc/blob/main/img/TlalocLogo01.jpg" width="512" height="512" />

# Tlaloc

The Tlaloc repository is structured as follows:
- [docs](https://github.com/1969-07-20/Tlaloc/blob/main/docs/) is the sub-directory with additional documentation.
- [src](https://github.com/1969-07-20/Tlaloc/blob/main/src/) is the sub-directory the Tlaloc source code.
- [etc](https://github.com/1969-07-20/Tlaloc/blob/main/etc/) is the sub-directory with miscellaneous utilities.
- [yahooquery](https://github.com/1969-07-20/Tlaloc/blob/main/yahooquery/) is the sub-directory with a locally modified version of [Yahoo Query](https://github.com/dpguthrie/yahooquery).

Additional documentation on Tlaloc and its operation is available at the following links:.
- [Tlaloc Configuration and Control](https://github.com/1969-07-20/Tlaloc/blob/main/docs/configuration.md)
- [Tlaloc Software Implementation](https://github.com/1969-07-20/Tlaloc/blob/main/docs/implementation.md)

# Introduction
Tlaloc is software in development.  It acquires financial and market data related to a list of stocks from multiple sources, integrates the multiple data streams into a single coherent model of the markets' perception of each stock and then provides the state of the model to one or more clients programs.  Client programs can use this information as they see fit, most likely for the purpose of researching stocks and executing trades based on that research.

The target audience for Tlaloc is small individual investors.  With that in mind an effort is made to minimize the costs by using free and low-cost data sources as well as running on cheap hardware using free and open source software.  (Development has been taking place on Raspberry Pi, with hardware costs less than $250.  Raspberry Pi class hardware will continue to be the target platform for the program for the foreseeable future.)

## Summary
From an end user perspective, the following are the primary features of Tlaloc.

1. Obtain information from multiple sources.  Multiple sources provide a wider array of information than can be obtained economically from a single data source.  Multiple sources also provide redundancy which allows one data source to fill in when another data source is unavailable.
2. Provide a comprehensive view of the companies being followed.  The three main categories of information are:
   - current transaction information including current prices, and the order book (near real-time to timely)
   - current expectations of the market of the future price of the stocks as embodied by the price of options (updated daily)
   - current and historical state of the company via information in the three primary financial statements:  cash flow statement, income statement, balance sheet (updated weekly)
3. Support stock investing with time horizons of months or years.  As a result, no emphasis is put on obtaining truly realtime data or reducing latencies to the absolute minimum.
4. Run continuously and autonomously for long periods of time.  As of the time of writing (2024-07) the program has been running effectively 24/7 for about three years.
5. Is highly configurable.  The program is extremely versatile.  Its wide range of functions can be tailored by the user through configuration files and command line parameters.  The plan is to eventually support dynamic reconfiguration without requiring restarting the program.
6. Is very robust.  Continuing effort has gone into making the program work reliably, fail gracefully when problems are encountered and recover and continue operating  when possible.  The following measures are taken in an effort to fail and recover gracefully.
   - Retry failed queries with systematically increasing delay back-off between retries.
   - Perform extensive validation of information received.
   - Build in extensive error recovery to return to a state which enables continued operation.

## Current Status
Currently Tlaloc has gotten to the point where it reliably queries multiple data sources for information.  It does this in a robust and reliable manner which is capable of baseline "production" operation.  Few features envisioned for the query phase have yet to be implemented.  This data is logged and can be used in playback to support future development.

The responses received from the data sources are transformed by a JSON parser into Python data structures used by the program internally.  These data structures are then normalized to standard forms that are easier to work with later.  Recent work has focused on the first phase of normalization, i.e. at a syntax level.

A prototype of a normalization language has been developed and implemented in software.  The normalization language and the implementation in software are not feature complete.  Most notably, they lack the desired capability to format the data, e.g. enforce significant figures in the floating point numbers etc.

Specifying the normalization process in a language enables using a common normalization engine for all data sources.  The normalization process for each data source exists as a specification read in from a file.  This minimizes the logic that is specific to a source and enables adapting to changes in data received from a source without changing the program.

Preliminary investigations have been made into the form and implementation of the mathematical model used for representing the state of a company.  The definitions and formulas of GAAP (Generally Accepted Accounting Principles from the The Financial Accounting Standards Bureau) have been identified as a source from which a mathematical model of the financial state of a company can be extracted.  The model elements extracted from GAAP will be augmented with a model which takes market information into account (e.g. transaction history, order book and option prices) to represent how the market is pricing the company.

These are broad outlines of what is planned for the mathematical model but the implementation has only been prototyped at a very rudimentary level.  Most detailed design and implementation are yet to be done.

The mechanics of the communication of clients with Tlaloc, including authentication, (at roughly a session layer in the OSI networking model) have been prototyped at an extremely rudimentary level.  This was done using a middleware.  Fleshing out the design and implementation of the client connection is TBD.

# Overview of Operation
At start-up Tlaloc reads configuration information from the command line arguments and from configuration files and performs initialization based on this information.  As part of the start-up process the program forks into two processes.  Process 1 is responsible for querying the data sources.  The responses generated by the data sources are passed on to Process 2 for processing.

Because the data sources respond with information organized in a variety of ways, the first processing step Process 2 does with a response is to normalize the response so that the information of interest can be accessed with simpler, standardized logic in the second processing step.  The second processing step merges the data from the multiple streams into a coherent set of data.

The actual data received from the multiple data sources partially overlaps each other.  Some data is available from multiple sources, some from just one source.  The program does more than just aggregate all the diverse data into one large unstructured set.  The method the program uses to merge the multiple streams of data is to use the data streams to update a running mathematical model of the company behind each stock and the market's perceptions of the stock.  There are three types of input into this model:

- financial statements and SEC filings
- transaction history and order book
- option prices

The basis of the mathematical model of the company's business status are the quantities and formulas codified in the GAAP accounting standards.  The GAAP accounting standards have evolved over decades of wide-spread use in US businesses.  While this is a novel application of GAAP, the author considers the GAAP accounting standards to be a highly (if organically) evolved model of businesses, and therefore worthy of serving as the basis for the mathematical model of businesses used in this program.  Much of this information is found in a business's financial statements (balance sheet, cash flow statement and income statement) as well as in SEC filings.

Regarding the market's perception of the value of a stock, over short term horizons the current state of the order book and the transaction history quantify the market's perceptions of the market's perceptions of the value of a stock.  Option prices do the same for time horizons of days, weeks or months.

Once the multiple data streams have been merged into the mathematical models for the individual companies, Process 2 communicates the current status of the models which have changed state to the clients which subscribe to those models.  The  clients then use that info for their own purposes.

Tlaloc will communicate the status of the model of a company in two ways.  Upon request from the client, Tlaloc will provide the state of the entire mathematical model.  This is a "pull" type information transfer.  More typically Tlaloc will just "push" the changes to individual states at the time they change.

Transmissions of the complete state of the model for a company will be sent to the client upon the client's request, nominally upon first connection to Tlaloc and then very occasionally (such as once every several hours) thereafter.  However, since the model will be very extensive with hundreds of variables most of which change very slowly, Tlaloc will push the new values at the time of change when the few model variables which do change.

It is assumed that the program runs on a dedicated computer, in effect more of a low-cost market data serving appliance than general purpose computer.  While the program requires very modest resources (CPU, network, memory) it makes no attempt to "play nicely" with other programs or users on the same machine.  With these goals in mind the program targets a Raspberry Pi.  Dedicating such a modest computer to the program is a very modest burden to place on the target end user, individual small investors.

# Data Sources
The following are data sources from which Tlaloc currently or has previously obtained data.

- IEX Cloud (https://iexcloud.io)
- Yahoo (https://finance.yahoo.com)
- CNBC (https://www.cnbc.com)
- AlphaVantage (https://www.alphavantage.co)
- Market Data (https://www.marketdata.app)
- Reuters (https://www.reuters.com)
- Google (https://www.google.com/finance/)

IEX Cloud was an excellent data source.  IEX Cloud was a service of the IEX exchange. For a very reasonable cost it provided the best data on current market status.  From IEX Cloud Tlaloc obtained a) the current order book for the requested symbols on the IEX Exchange, b) recent transactions for the requested symbols on the IEX Exchange, c) detailed quotes for the requested symbols.  For years Tlaloc queried IEX Cloud for approximately 90 symbols every 15 seconds.  All this for approximately $10 per month.  In early 2024 IEX Cloud raised their prices dramatically.  Then in early June 2024 IEX announced they will shut down their API at the end of August.

Yahoo Finance is another excellent data source, and it is free.  A wide range of data is available from the Yahoo Finance API, everything from delayed quotes to options prices to detailed company financials.

Yahoo Finance' API achieved wide renown, deservedly so.  A whole cottage industry has grown up around the Yahoo Finance API with numerous open source software packages being written for it.  I like Yahoo Query best (https://github.com/dpguthrie/yahooquery) and use it in Tlaloc to query the Yahoo API.

In 2018 or so Yahoo officially withdrew its API from public usage.  But it still continues to work in an unofficial fashion.  Tlaloc obtains company financials and options data from Yahoo Finance.  Since Yahoo Finance is Tlaloc's sole source for this data, I try to have a light footprint on Yahoo Finance.  For example, I do not have Tlaloc query Yahoo Finance for price data during market hours even though it is available from Yahoo Finance.

CNBC is a good free source but not as in the same league as IEX Cloud or Yahoo Finance.  Tlaloc obtains delayed quotes from CNBC every 15 minutes during trading hours and a more detailed quotes for the list of symbols once every day shortly after the trading day has ended.

AlphaVantage and MarketData are pay APIs which offer a highly restrictive free tier. AlphaVantage used to be fairly generous with 400 API calls per day in their free tier.  This has been reduced to 25 API calls per day.  Tlaloc queries these sites for recent intraday price data as a backup in case there is a problem with the primary data sources.

Reuters used to be a good source of quotes.  However, Reuters API changed to using web sockets for its communication mechanism.  Google also uses web sockets.  At this time Tlaloc is not capable of making queries using web sockets and these two data sources are not currently data sources for Tlaloc.

(Limited market information can be obtained from Google via Google Sheets.  The author has developed the ability to obtain market information via this route.  However, due to its limited nature the information obtained via Google Sheets is not sufficiently compelling to warrant adding Google Sheets as a data source for Tlaloc.)

Some sources are queried for one type of information only.  While other sources are queried for multiple types of information, the most prominent being Yahoo Finance. There are two main types of queries, "quotes" and "general information".

Quotes provide price data and often miscellaneous information about the company.  Tlaloc makes two types of quote queries:  "intraday" and "daily".  Intraday quotes come from IEX Cloud and CNBC and are intended to provide near real time data about the price of stocks throughout the day.  The daily quotes are obtained after the markets have closed and are intended to obtain either a) summary information, such as metrics, or b) download full day price histories with one query to fill in the historical record of the price of the list of stocks.

The "general information" category is a catch-all for queries which are not quote oriented.  Currently, these are made up of the several diverse categories of information from Yahoo Finance such as options and company financials.  In the future, other data sources may result in queries in the "general information" category.

Tlaloc has a name for each type of response.  The following is a list of the names of the various types along with the data source and the content

- II_QUOTE - IEX Cloud, intraday quote
- CI_QUOTE - CNBC, intraday quote
- CD_QUOTE - CNBC, daily quote
- MD_TS0   - MarketData, daily quote
- AD_QUOTE - AlphaVantage, daily quote
- YD_OPT   - Yahoo Finance, options
- YD_S+D   - Yahoo Finance, events (stock splits, distributions, etc.)
- YD_MISC0 - Yahoo Finance, miscellaneous
- YD_MISC1 - Yahoo Finance, miscellaneous
- YD_MISC2 - Yahoo Finance, miscellaneous
- YD_FIN0  - Yahoo Finance, financials
- YD_FIN1  - Yahoo Finance, financials
- YD_MOD0  - Yahoo Finance, modules
- YD_MOD1  - Yahoo Finance, modules

# Overview of Mathematical Model
The core of Tlaloc's approach to merging the data from the several data sources is to combine the data into a single coherent mathematical model of the company.  The strategy for Tlaloc is more ambitious than merely aggregating all the disparate types of data the sources supply.

This program goes a step further in that it creates a mathematical model from the varied, yet fragmentary data.  The mathematical model goes beyond mere aggregating data in the following ways:
- By imposing mathematical relationships among the various quantities (e.g. profit equals income minus expenses).
- By inferring quantities which are not be present in the stream of input data.
- By treating some input as noisy and outputting a "de-noised" estimate of a quantity rather than a direct copy of the values it receives.

As a starting point, the mathematical relationships among quantities that the model imposes will be derived from established sources.  Initially the primary source will come from GAAP (Generally Accepted Accounting Principles).  The definitions and relationships used by GAAP are expected to be relevant for the following reasons
- minimal transformation is expected because much of the data is generated by entities using GAAP in their business operations
- GAAP has withstood the test of time in usage in a major economy.  This is empirical evidence that it appropriate for the task at hand, serving as a common language for representing the financial state and activities of diverse businesses.

The mathematical model is not limited to GAAP.  The mathematical model will include elements beyond GAAP.  For example, GAAP was not meant to capture how the market prices a company's shares.  The inputs to this portion of the mathematical model will be the current order book, transaction history and current prices of options expiring at various times in the future.

There is a data exchange format called the Extensible Business Reporting Language, more commonly known as XBRL.  XBRL defines an extension to XML for representing business information in a manner that is easily generated and read in an automated fashion by computers and yet is still "readable" by humans.  The SEC mandates many key reports that publicly traded business are required to submit (such as 10-Q) be in the XBRL format.

XBRL is a general purpose language.  Schemas have been defined to tailor XBRL to specific classes of business reports such as GAAP (as mentioned earlier) IFRS (International Financial Reporting Standards), etc. Along with schemas, XBRL is implemented by multiple softwares, including an open source library called Arelle.  Should Tlaloc choose to include XBRL as part of the machinery for representing the mathematical model, it is likely that it will use Arelle as the middleware.

The mathematical model of a stock is maintained over extended periods of time.  New information causes the model to be updated.  Due to the mathematical relationships being maintained, an update typically causes multiple quantities of the model to also be updated.  When changes occur in the model, messages are sent to the clients of the model informing them of what has changed.  This enables the clients to keep their local copy of the model consistent with the master copy maintained by Tlaloc.  An established client may request the full state of the model periodically in order to ensure that it is consistent with the master model maintained by Tlaloc.

# Clients
Tlaloc is designed to obtain financial data from online sources for a list of stocks, turn raw data into a dynamic mathematical models, one for each stock, and then communicate the state of the models to one or more clients which subscribe to the models for one or more stocks.

Tlaloc provides clients with a quality model of stocks.  While Tlaloc does not impose restrictions on what the clients do with the model, it is expected that clients will either use the model to inform investors about possible investments or even be used as input to an algorithmic stock trading program which makes the investment decisions and executes them autonomously.

Tlaloc supports multiple clients.  Any one client can subscribe to the model of any of the stocks being modeled.  By communicating with clients using network connections, Tlaloc imposes no restriction of where clients are located.  The clients may be on the same machine or may be at some remote location on the internet.

Tlaloc acts as a server in the network connections.  For security purposes, Tlaloc requires clients to have an account with Tlaloc and provide valid authentication credentials when establishing a connection to Tlaloc.  Tlaloc supports the clients connecting and disconnecting at arbitrary times.  After a client authenticates itself to Tlaloc, it informs Tlaloc which symbol(s) it wants to subscribe to.  Tlaloc then provides the complete current state of the model for the symbol(s) to the client.  This synchronizes the instances of the model for the stock held by Tlaloc and the client.

Once Tlaloc and the client have a synchronized the models for the stock Tlaloc will communicate just the changes to the model.  Doing so avoids wasting compute cycles and bandwidth communicating those aspects which have not changed.  In order to ensure that the model stays synchronized for long running connections, Tlaloc supports the client to periodically request the complete model to be resent.  The client should do this infrequently, on the order of once an hour during market hours and once or twice a day outside market hours.

# License
Copyright 2024 Tlaloc Labs LLC

This file is part of Tlaloc.

Tlaloc is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
