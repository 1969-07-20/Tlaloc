# -*- coding: utf-8 -*-

"""Source_Reuters_DailySummary.py:  Implements the class which handles
   daily queries to Reuters.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

from Source_Generic import Source_Generic

import json
import re
#mport pprint


# BEG Source_Reuters_DailySummary.py SPECIFIC
# END Source_Reuters_DailySummary.py SPECIFIC


class Source_Reuters_DailySummary(Source_Generic):


    #  SUBCLASS OVERRIDE

    def __init__(self):
        self.src_name = "Reuters_Daily"

        super().__init__()

        self.configure_lvl2()   #  Default specific class configs
        self.configure_lvl3()   #  Override specific class override


    #  SUBCLASS OVERRIDE

    #  Reuters Daily specific configuration
    def configure_lvl2(self):

        print('Inside Source_Reuters_DailySummary::configure_lvl2()')


        self.version = "2024-08-01a"


        #  Query frequency and batch parameters
        self.batch_sleep_time = 11
        self.max_threads = 1

        self.max_batch = 1

        #  List missing symbols
        self.map_symbols['AAPL' ] = 'AAPl.OQ'
        self.map_symbols['ABBV' ] = 'ABBV.N'
        self.map_symbols['ABNB' ] = 'ABNB.OQ'
        self.map_symbols['ADBE' ] = 'ADBE.OQ'
        self.map_symbols['ADP'  ] = 'ADP.OQ'
        self.map_symbols['AKAM' ] = 'AKAM.OQ'
        self.map_symbols['AMD'  ] = 'AMD.OQ'
        self.map_symbols['AMZN' ] = 'AMZN.OQ'
        self.map_symbols['APA'  ] = 'APA.N'
        self.map_symbols['ATSG' ] = 'ATSG.OQ'
        self.map_symbols['BABA' ] = 'BABA.N'
        self.map_symbols['BASFY'] = 'BASFY.PK'
        self.map_symbols['BF.B' ] = 'BFb.N'
        self.map_symbols['BIDU' ] = 'BIDU.OQ'
        self.map_symbols['BKNG' ] = 'BKNG.OQ'
        self.map_symbols['BKR'  ] = 'BKR.N'
        self.map_symbols['CINF' ] = 'CINF.OQ'
        self.map_symbols['CME'  ] = 'CME.OQ'
        self.map_symbols['COST' ] = 'COST.OQ'
        self.map_symbols['CSCO' ] = 'CSCO.OQ'
        self.map_symbols['CSX'  ] = 'CSX.OQ'
        self.map_symbols['DASH' ] = 'DASH.V'
        self.map_symbols['EADSY'] = 'EADSY.PQ'
        self.map_symbols['EXC'  ] = 'EXC.OQ'
        self.map_symbols['FSLY' ] = 'FSLY.N'
        self.map_symbols['GOOG' ] = 'GOOG.O'
        self.map_symbols['HIMX' ] = 'HIMX.OQ'
        self.map_symbols['INTC' ] = 'INTC.OQ'
        self.map_symbols['KMTUY'] = 'KMTUY.PK'
        self.map_symbols['MAR'  ] = 'MAR.OQ'
        self.map_symbols['MSFT' ] = 'MSFT.OQ',
        self.map_symbols['NFLX' ] = 'NFLX.OQ'
        self.map_symbols['PEP'  ] = 'PEP.OQ'
        self.map_symbols['SBUX' ] = 'SBUX.OQ',
        self.map_symbols['TSLA' ] = 'TSLA.OQ'
        self.map_symbols['V'    ] = 'V.N'

        self.skip_list.append('EADSY')
        self.skip_list.append('PEG')
        self.skip_list.append('DASH')
        self.skip_list.append('ARKG')
        self.skip_list.append('ARKW')
        self.skip_list.append('OPEN')
        self.skip_list.append('PLTR')
        self.skip_list.append('SFTBY')
        self.skip_list.append('U')
        self.skip_list.append('VDE')
        self.skip_list.append('VOO')


        if config.runtime_params['production']:
            if not config.runtime_params['offset_mkt_begin']:
                self.mkt_beg_time  = 163130
                self.mkt_end_time  = 235959
            else:
                self.mkt_beg_time  = 173130
                self.mkt_end_time  = 235959
        else:
            pass


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_reuters_daily.txt'

        #  Reuters specific parameters
        self.id_URL = re.compile('https://www.reuters.com/companies/api/getFetchCompanyProfile/' + '.*')


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl2']:
            self.dump_src_attributes (2)


    #  SUBCLASS OVERRIDE

    def get_query_types(self):

        return [ 'RS_QUOTE' ]


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

        query = 'https://www.reuters.com/companies/api/getFetchCompanyProfile/' + symbols_str

        query_sanitized = query


        return query, query_sanitized, batch_list[0]['query_type']


    #  SUBCLASS OVERRIDE

    #  Convert response to dictionary
    def response_to_dictionary(self, query_raw):

        query_json = json.loads(query_raw)


        #  Remove extraneous layers from the JSON
        query_json = query_json["market_data"]


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
