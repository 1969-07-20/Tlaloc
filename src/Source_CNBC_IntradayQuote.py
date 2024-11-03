# -*- coding: utf-8 -*-

"""Source_CNBC_IntradayQuote.py:  Implements the class which handles
   intra-trading day queries to CNBC.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

from Source_Generic import Source_Generic

import json
import re
#mport pprint


# BEG Source_CNBC_IntradayQuote.py SPECIFIC
# END Source_CNBC_IntradayQuote.py SPECIFIC


class Source_CNBC_IntradayQuote(Source_Generic):


    #  SUBCLASS OVERRIDE

    def __init__(self):
        self.src_name = "CNBC_Intraday"

        super().__init__()

        self.configure_lvl2()   #  Default specific class configs
        self.configure_lvl3()   #  Override specific class override


    #  SUBCLASS OVERRIDE

    #  CNBC Intraday specific configuration
    def configure_lvl2(self):

        print('Inside Source_CNBC_IntradayQuote::configure_lvl2()')


        self.version = "2024-08-01a"

        self.shuffle_queries = False


        #  Query frequency and batch parameters
        self.delta_quote = 15 * 60

        self.batch_sleep_time = 13

        self.max_batch = 10

        #  Define when the market is open
        if config.runtime_params['production']:
            if not config.runtime_params['offset_mkt_begin']:
                self.mkt_end_time  = 161959
            else:
                self.mkt_end_time  = 161959
        else:
            pass


        self.query_type_src = {'meta': True, 'realtime': True}


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_cnbc_intraday.txt'


        self.id_URL = re.compile('^https://quote.cnbc.com/quote-html-webservice/quote.htm\?noform=1&partnerId=2&fund=1&exthrs=0&output=json&symbols=' + '.*' + '&requestMethod=quick')


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl2']:
            self.dump_src_attributes (2)


    #  SUBCLASS OVERRIDE

    def get_query_types(self):

        return [ 'CI_QUOTE' ]


    #  SUBCLASS OVERRIDE

    def id_quote(self, quote):
        if self.id_URL.match(quote):
            return True
        else:
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

        symbols_str = '|'.join(item['qry_symbol'] for item in batch_list)

        query = 'https://quote.cnbc.com/quote-html-webservice/quote.htm?noform=1&partnerId=2&fund=1&exthrs=0&output=json&symbols=' + symbols_str + '&requestMethod=quick'

        query_sanitized = query


        return query, query_sanitized, batch_list[0]['query_type']


    #  SUBCLASS OVERRIDE

    #  Convert response to dictionary
    def response_to_dictionary(self, query_raw):

        query_json = json.loads(query_raw)


        #  Remove extraneous layers from the JSON
        query_json = query_json["QuickQuoteResult"]["QuickQuote"]


        return query_json


    #  SUBCLASS OVERRIDE

    def symbol_rollcall(self, batch_list, query_json, query):

# TODO
        #  Determine if the number of response symbols equals number of requested symbols
        if len(batch_list) != len(query_json.keys()):
            print("ERROR:  len(batch_list) != len(query_json.keys())  (%d != %d).  HALTING PROCESSING OF URL '%s'" %
                (len(batch_list), len(query_json.keys()), query))

            return True

        return False


    #  SUBCLASS OVERRIDE

    def normalize_query(self, query_raw):
        return self.query_raw_norm.sub(' ', query_raw)


    #  SUBCLASS OVERRIDE

    def get_query_stock(self, qry_symbol, query_json):
        query_stock = None

        if (type(query_json) is dict):
            query_stock = query_json
        else:
            for b_idx in range(0, len(query_json)):
                if qry_symbol == query_json[b_idx]['symbol']:
                    query_stock = query_json[b_idx]
                    break

        return query_stock


    #  SUBCLASS OVERRIDE

    def parse_query_response(self, query_stock, symbol, log_timestamp, query_type, version):

        stock_entry = self.make_stock_entry()

        #  TODO FIXME
        return stock_entry

        #  Populate stock_entry
        #  << TODO >>

        #  Print debug info about result of parse
        quote_string = json.dumps(stock_entry)

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

