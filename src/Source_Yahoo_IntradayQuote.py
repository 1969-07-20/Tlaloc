# -*- coding: utf-8 -*-

"""Source_Yahoo_IntradayQuote.py:  Implements the class which handles
   intra-trading day queries to Yahoo.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

from Source_Generic import Source_Generic

import json
import re
#mport pprint

from curl_cffi import Session


# BEG Source_Yahoo_IntradayQuote.py SPECIFIC
from yahooquery import Ticker
# END Source_Yahoo_IntradayQuote.py SPECIFIC


class Source_Yahoo_IntradayQuote(Source_Generic):


    #  SUBCLASS OVERRIDE

    def __init__(self):
        self.src_name = "Yahoo_Intraday"

        super().__init__()

        self.configure_lvl2()   #  Default specific class configs
        self.configure_lvl3()   #  Override specific class override


    #  SUBCLASS OVERRIDE

    #  Yahoo Intraday specific configuration
    def configure_lvl2(self):

        print('Inside Source_Yahoo_IntradayQuote::configure_lvl2()')


        self.version = "2024-08-01a"

        self.shuffle_queries = False


        #  Query frequency and batch parameters
        self.delta_quote = 15 * 60

        self.poll_sleep_time = 0.25

        self.batch_sleep_time = 10

        self.max_batch = 10

        #  List missing symbols
        self.map_symbols['BF.B'] = 'BF-B'
        self.map_symbols['BRKB'] = 'BRK-B'


        #  Define when the market is open
        if config.runtime_params['production']:
            if not config.runtime_params['offset_mkt_begin']:
                self.mkt_beg_time  =  90730
                self.mkt_end_time  = 161959
            else:
                self.mkt_beg_time  =  90800
                self.mkt_end_time  = 161959
        else:
            pass


        self.query_type_src = {'meta': True, 'realtime': True}


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_yahoo_intraday.txt'

        #  Yahoo specific parameters
        self.id_URL = re.compile('^https://query2.finance.yahoo.com/v6/finance/quote?lang=en-US&region=US&corsDomain=finance.yahoo.com&symbols=' + '.*')


        self.pseudo_URL = 'https://query2.finance.yahoo.com/v6/finance/quote?lang=en-US&region=US&corsDomain=finance.yahoo.com&symbols=<<YI_QUOTE>>'


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl2']:
            self.dump_src_attributes (2)


    #  SUBCLASS OVERRIDE

    def get_query_types(self):

        return [ 'YI_QUOTE' ]


    def make_query_custom(self, batch_list, query, query_sanitized, ):

        response = ''

        attempt = 1

        try:

            symbols = " ".join([batch_list[idx]['qry_symbol'] for idx in range(len(batch_list)) ])

            session = Session(impersonate="chrome")

            if 0 == len(config.runtime_params['ca_cert']):
                yq_tickers = Ticker(symbols, session=session)
            else:
                yq_tickers = Ticker(symbols, proxies=config.runtime_params['proxies'], verify=config.runtime_params['ca_cert'], session=session)

            loc_symbol = batch_list[0]['loc_symbol']
            print(batch_list[0], flush=True)

            response = yq_tickers.quotes

            '''
            print('BEF(QUOTE)')
#           print(json.dumps(json.loads(response), indent=4, sort_keys=False))
            print(json.dumps(response, indent=4, sort_keys=False))
            print('AFT(QUOTE)')
            '''

            response = json.dumps(response, separators=(',', ':'))

            if '' != response:

                #  Turn off throttling of queries due to error conditions
                self.reset_backoff([entry['loc_symbol'] for entry in batch_list])

                #  Make successful return
                return response, False


        except Exception as e:
            print("ERROR (#" + str(attempt) + ") FETCHING URL '" + query_sanitized + "'")
            print(f"    EXCEPTION MESSAGE:  {str(e)}")
            # e.read().decode("utf8", 'ignore')


        #  All attempts to fetch the URL failed, handle error
        print("ERROR FAILED TO FETCH URL '" + query_sanitized + "'")

        for item in batch_list:    #  TODO:  PROVIDE ABILITY TO SUPPRESS BACK-OFF
            stock = item['loc_symbol']

            self.backoff [stock]['major_cnt'] -= 1

            if 0 >= self.backoff [stock]['major_cnt']:
                self.backoff [stock]['minor_reset'] *= 2   #  TODO:  PROVIDE ABILITY TO IMPOSE MAX BACK-OFF

                self.backoff [stock]['major_cnt'] = self.backoff [stock]['major_reset']

                print(self.src_name + ":  ADJUSTING BACK-OFF '" + stock + "' new back-off:  %d" %
                    (self.backoff [stock]['minor_reset']))

            self.backoff [stock]['minor_cnt'] = self.backoff [stock]['minor_reset']

        return None, True


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

        symbols_str = '<<' + '|'.join(item['qry_symbol'] for item in batch_list) + '>>'

        query = self.pseudo_URL + symbols_str

        query_sanitized = query


        return query, query_sanitized, batch_list[0]['query_type']


    #  SUBCLASS OVERRIDE

    #  Convert response to dictionary
    def response_to_dictionary(self, query_raw):

        query_json = json.loads(query_raw)


        #  Remove extraneous layers from the JSON
#       query_json = query_json["QuickQuoteResult"]["QuickQuote"]


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
