# -*- coding: utf-8 -*-

"""Source_MarketData_DailySummary.py:  Implements the class which handles
   daily queries to MarketData.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

from Source_Generic import Source_Generic

import json
import re
#mport pprint


# BEG Source_MarketData_DailySummary.py SPECIFIC
from datetime import datetime
from datetime import timedelta
# END Source_MarketData_DailySummary.py SPECIFIC


class Source_MarketData_DailySummary(Source_Generic):


    #  SUBCLASS OVERRIDE

    def __init__(self):
        self.src_name = "MarketData_Daily"

        super().__init__()

        self.configure_lvl2()   #  Default specific class configs
        self.configure_lvl3()   #  Override specific class override


    #  SUBCLASS OVERRIDE

    #  MarketData Daily specific configuration
    def configure_lvl2(self):

        print('Inside Source_MarketData_DailySummary::configure_lvl2()')


        self.version = "2024-08-01a"


        #  Query frequency and batch parameters
        self.batch_sleep_time = 23
        self.max_threads = 1

        self.max_batch = 1

        self.timeout    = 5.0
        self.to_backoff = 4.0 / 3.0


        #  List missing symbols
        self.map_symbols['BRKB'] = 'BRK.B'


        #  Define when the market is open

        if config.runtime_params['production']:
            if not config.runtime_params['offset_mkt_begin']:
                self.mkt_beg_time  = 163123
                self.mkt_end_time  = 235959
            else:
                self.mkt_beg_time  = 173123
                self.mkt_end_time  = 235959
        else:
            pass

        self.query_type_src = {'interval': '1m', 'range': '1d'}


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_marketdata_daily.txt'


        #  MarketData specific parameters

        self.id_URL = {
            #                         https://api.marketdata.app/v1/stocks/candles/1/AAPL/?from=2023-10-24&to=2023-11-14&dateformat=timestamp
            'MD_TS0':     re.compile('https://api.marketdata.app/v1/stocks/candles/1/(.+)/\?from=(\d\d\d\d)-(\d\d)-(\d\d)&to=(\d\d\d\d)-(\d\d)-(\d\d)&dateformat=timestamp'),

            #                         https://api.marketdata.app/v1/options/chain/AAPL/?dateformat=timestamp
            'MD_OPT0':    re.compile('https://api.marketdata.app/v1/options/chain/(.+)/\?dateformat=timestamp'),
        }


        #  Credentials
        self.apiToken  = config.runtime_params['credentials'][self.src_name]['apiToken']


        self.max_queries_per_day = 90


        #  Add additional headers as needed for MarketData source
        self.hdr['Host']          = 'api.marketdata.app'
        self.hdr['Accept']        = 'application/json'
        self.hdr['Authorization'] = f'Token {self.apiToken}'


        self.query_type_list = [
            [ 'MD_TS0', ],
            [ 'MD_TS0', ],
            [ 'MD_TS0', ],
            [ 'MD_TS0', ],
            [ 'MD_TS0', ],
            [ 'MD_TS0', ],
            [ 'MD_TS0', ],
        ]

        self.pseudo_URL = {
            #              https://api.marketdata.app/v1/stocks/candles/1/AAPL/?from=2023-10-24&to=2023-11-14&dateformat=timestamp
            'MD_TS0':     'https://api.marketdata.app/v1/stocks/candles/1/<<SYMBOL>>/?from=<<FROM_STR>>&to=<<TO_STR>>&dateformat=timestamp',

            #              https://api.marketdata.app/v1/options/chain/AAPL/?dateformat=timestamp
            'MD_OPT0':    'https://api.marketdata.app/v1/options/chain/<<SYMBOL>>/?dateformat=timestamp',
        }


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl2']:
            self.dump_src_attributes (2)


    #  SUBCLASS OVERRIDE

    def is_work_day(self, day):

#       #  Only check for weekends and holidays on production runs
#       if not config.runtime_params['production']:
#           return True

        return True


    #  SUBCLASS OVERRIDE

    def review_query_helper(self, e):
        return e['ts']

    def review_query_list(self, list_in, query_type, num_query_types, time_hack):

        #  Create a list of stock and time of last query associations
        times = [ {'ts':  self.time_of_last_query[stock][query_type].timestamp(), 'stock': stock } for stock in list_in ]

        #  Sort list based on time
        times.sort(key=self.review_query_helper)

        #  Impose max length on times list
        num_queries = self.max_queries_per_day // num_query_types

        if len(times) > num_queries:
           times = times[:num_queries]

        #  Create output list
        list_out = [ elem['stock'] for elem in times]

        #  Record time of query
        for stock in list_out:
            self.time_of_last_query[stock][query_type] = time_hack

        # print(f'TODO DELETE ME(MarketData_Daily::review_query_list()):  times={times}')
        # print(f'TODO DELETE ME(MarketData_Daily::review_query_list()):  list_out={list_out}')

        #  Return vetted list
        return list_out


    #  SUBCLASS OVERRIDE

    def get_query_types(self):

        #  Return the appropriate type(s) based on the day.
        day = datetime.today().weekday()    #  0 is Monday, Sunday is 6
#       day = 0

        return self.query_type_list[day]


    #  SUBCLASS OVERRIDE

    def id_quote(self, quote):

        for key in self.id_URL.keys():
           id_URL = self.id_URL[key]

           if id_URL.match(quote):
               return True

        return False


    #  SUBCLASS OVERRIDE

    #  This method makes a blank stock entry
    def make_stock_entry(self):

        #  TODO FIXME
        return {
            'quote': {
            }
        }


    #  SUBCLASS OVERRIDE

    def make_query_url(self, batch_list):

        #  TODO:  ENSURE ONLY ONE ITEM IN BATCH LIST

        symbols_str = '|'.join(item['qry_symbol'] for item in batch_list)

        type = batch_list[0]['query_type']

        if type in self.pseudo_URL:

            if 'MD_TS0' == type:
                # 'MD_TS0':  'https://api.marketdata.app/v1/stocks/candles/1/<<SYMBOL>>/?from=<<FROM_STR>>&to=<<TO_STR>>'

                from_date = datetime.now() - timedelta(days = 7)
                to_date   = datetime.now() + timedelta(days = 1)

                from_str = from_date.strftime('%Y-%m-%d')
                to_str   = to_date.strftime('%Y-%m-%d')


                query = self.pseudo_URL[type]

                query = query.replace('<<SYMBOL>>',   symbols_str)
                query = query.replace('<<FROM_STR>>', from_str)
                query = query.replace('<<TO_STR>>',   to_str)
#           elif 'MD_OPT0' == type:
            else:
                # 'MD_OPT0':    'https://api.marketdata.app/v1/options/chain/<<SYMBOL>>/?dateformat=timestamp'

                query = self.pseudo_URL[type]

                query = query.replace('<<SYMBOL>>', symbols_str)


        else:

            #  TODO:  COME UP WITH A BETTER NULL RESPONSE

            from_date = datetime.now() - timedelta(days = 7)
            to_date   = datetime.now() + timedelta(days = 1)

            from_str = from_date.strftime('%Y-%m-%d')
            to_str   = to_date.strftime('%Y-%m-%d')

            query = 'https://api.marketdata.app/v1/stocks/candles/1/' + symbols_str + '/?from=' + from_str + '&to=' + to_str + 'dateformat=timestamp'

        query_sanitized = query


        return query, query_sanitized, batch_list[0]['query_type']


    #  SUBCLASS OVERRIDE

    #  Convert response to dictionary
    def response_to_dictionary(self, query_raw):

        query_json = json.loads(query_raw)


        #  Remove extraneous layers from the JSON
#       query_json = query_json["market_data"]


        return query_json


    #  SUBCLASS OVERRIDE

    def symbol_rollcall(self, batch_list, query_json, query):

        #  Determine if the number of response symbols equals number of requested symbols
        if len(batch_list) != len(query_json.keys()):
            print("ERROR:  len(batch_list) != len(query_json.keys())  (%d != %d).  HALTING PROCESSING OF URL '%s'" %
                (len(batch_list), len(query_json.keys()), query))

            return True

        return False


    #  SUBCLASS OVERRIDE

    def normalize_query(self, query_raw):
        #  TODO FIXME:  Tailor handling to type of query.
        return self.query_raw_norm.sub(' ', query_raw)


    #  SUBCLASS OVERRIDE

    def get_query_stock(self, qry_symbol, query_json):
        query_stock = None

        query_stock = query_json

        return query_stock


    #  SUBCLASS OVERRIDE

    def parse_query_response(self, query_stock, symbol, log_timestamp, query_type, version):

        stock_entry = self.make_stock_entry()

        #  TODO FIXME
        return stock_entry

        #  Populate stock_entry
        #  << TODO >>

        ticker_msg_head = ("ENTRY[%s]:  ID=%s:" + self.src_name + ":quote  TIME=%s") % ('%06d', symbol, log_timestamp)

        ticker_msg_body = quote_string

        with config.log_t_lock:
            ticker_msg_head = ticker_msg_head % (config.tk_entry_idx)
            config.tk_entry_idx += 1

            ticker_msg = "\n\n" + ticker_msg_head + "\n"+ ticker_msg_body + "\n"

            if config.log_ticker is not None:
                config.log_ticker.write(ticker_msg)
                config.log_ticker.flush()

            quoteToTwistedEvent_step1 (symbol, ticker_msg)
