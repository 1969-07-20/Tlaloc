# -*- coding: utf-8 -*-

"""Source_Yahoo_DailySummary.py:  Implements the class which handles
   daily queries to Yahoo.

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


# BEG Source_Yahoo_DailySummary.py SPECIFIC
from datetime import datetime

import math

from yahooquery import Ticker
# END Source_Yahoo_DailySummary.py SPECIFIC


class Source_Yahoo_DailySummary(Source_Generic):


    #  SUBCLASS OVERRIDE

    def __init__(self):
        self.src_name = "Yahoo_Daily"

        super().__init__()

        self.configure_lvl2()   #  Default specific class configs
        self.configure_lvl3()   #  Override specific class override


    #  SUBCLASS OVERRIDE

    #  Yahoo Daily specific configuration
    def configure_lvl2(self):

        print('Inside Source_Yahoo_DailySummary::configure_lvl2()')


        self.version = "2024-08-01a"


        #  Query frequency and batch parameters
        self.batch_sleep_time = 19
        self.max_threads = 1

        self.max_batch = 1

        #  List missing symbols
        self.map_symbols['BF.B'] = 'BF-B'
        self.map_symbols['BRKB'] = 'BRK-B'


        #  Define when the market is open
        if config.runtime_params['production']:
            if not config.runtime_params['offset_mkt_begin']:
                self.mkt_beg_time  = 163135
                self.mkt_end_time  = 235959
            else:
                self.mkt_beg_time  = 173135
                self.mkt_end_time  = 235959
        else:
            pass

        self.query_type_src = {'interval': '1m', 'range': '1d'}


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_yahoo_daily.txt'

        #  Yahoo specific parameters
        self.id_URL = {
            'YD_S+D':     re.compile('https://query2.finance.yahoo.com/v8/finance/chart/'),
            'YD_OPT':     re.compile('https://query2.finance.yahoo.com/v7/finance/options/'),
            'YD_MISC0':   re.compile('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
            'YD_MISC1':   re.compile('https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/'),
            'YD_MISC2':   re.compile('https://query2.finance.yahoo.com/ws/insights/v2/finance/insights?lang=en-US&region=US&corsDomain=finance.yahoo.com&symbol='),
            'YD_TS0':     re.compile('https://query2.finance.yahoo.com/v8/finance/chart/'),
            'YD_TS1':     re.compile('https://query2.finance.yahoo.com/v8/finance/chart/'),
            'YD_TS2':     re.compile('https://query2.finance.yahoo.com/v8/finance/chart/'),
            'YD_MOD':     re.compile('https://query(2|1).finance.yahoo.com/(v6|v10|v8)/finance/(quoteSummary|chart)/'),
            'YD_MOD0':    re.compile('https://query(2|1).finance.yahoo.com/(v6|v10|v8)/finance/(quoteSummary|chart)/'),
            'YD_MOD1':    re.compile('https://query(2|1).finance.yahoo.com/(v6|v10|v8)/finance/(quoteSummary|chart)/'),
            'YD_MOD2':    re.compile('https://query(2|1).finance.yahoo.com/(v6|v10|v8)/finance/(quoteSummary|chart)/'),
            'YD_FIN':     re.compile('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
            'YD_FIN0':    re.compile('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
            'YD_FIN1':    re.compile('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
            'YD_FIN2':    re.compile('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
            'YD_FIN3':    re.compile('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
        }


        self.query_type_list = [
#           [ 'YD_OPT', 'YD_MISC0', 'YD_MISC1', 'YD_MISC2', 'YD_MOD0', 'YD_MOD1', 'YD_MOD2', 'YD_FIN0','YD_FIN1', 'YD_FIN2', 'YD_FIN3', 'YD_S+D', 'YD_TS1', ],
            [ 'YD_OPT', 'YD_MISC1', 'YD_MISC2', ],
            [ 'YD_OPT', 'YD_FIN0',  'YD_MOD0',  ],
            [ 'YD_OPT', 'YD_FIN1',  'YD_MOD1',  ],
            [ 'YD_OPT', 'YD_FIN2',  'YD_MOD2',  ],
            [ 'YD_OPT', 'YD_FIN3',  'YD_S+D',   ],
            [ 'YD_OPT', 'YD_TS1',   ],
            [ 'YD_OPT', 'YD_MISC0', ],
        ]

        self.pseudo_URL = {
            'YD_S+D':     'https://query2.finance.yahoo.com/v8/finance/chart/<<YD_S+D>>',
            'YD_OPT':     'https://query2.finance.yahoo.com/v7/finance/options/<<YD_OPT>>',
            'YD_MISC0':   'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/<<YD_MISC0>>',
            'YD_MISC1':   'https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/<<YD_MISC1>>',
            'YD_MISC2':   'https://query2.finance.yahoo.com/ws/insights/v2/finance/insights?lang=en-US&region=US&corsDomain=finance.yahoo.com&symbol=<<YD_MISC2>>',
            'YD_TS0':     'https://query2.finance.yahoo.com/v8/finance/chart/<<YD_TS0>>',
            'YD_TS1':     'https://query2.finance.yahoo.com/v8/finance/chart/<<YD_TS1>>',
            'YD_TS2':     'https://query2.finance.yahoo.com/v8/finance/chart/<<YD_TS2>>',
            'YD_MOD':     'https://query2.finance.yahoo.com/v6/finance/quoteSummary/<<YD_MOD>>',
            'YD_MOD0':    'https://query2.finance.yahoo.com/v6/finance/quoteSummary/<<YD_MOD0>>',
            'YD_MOD1':    'https://query2.finance.yahoo.com/v6/finance/quoteSummary/<<YD_MOD1>>',
            'YD_MOD2':    'https://query2.finance.yahoo.com/v6/finance/quoteSummary/<<YD_MOD2>>',
            'YD_FIN':     'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/<<YD_FIN>>',
            'YD_FIN0':    'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/<<YD_FIN0>>',
            'YD_FIN1':    'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/<<YD_FIN1>>',
            'YD_FIN2':    'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/<<YD_FIN2>>',
            'YD_FIN3':    'https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/<<YD_FIN3>>',
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

    def get_query_types(self):

        #  Return the appropriate type(s) based on the day.
        day = datetime.today().weekday()    #  0 is Monday, Sunday is 6
#       day = 0

        return self.query_type_list[day]


#   query_raw, url_fetch_failed = self.make_query_custom(batch_list, query, query_sanitized, )

    def make_query_custom(self, batch_list, query, query_sanitized, ):

        #  FIXME:  Enforce len batch_list == 1

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

            if batch_list[0]['query_type'] == 'YD_S+D':
                response = yq_tickers.history_LOC(period='max', interval = '3mo', adj_ohlc=True)

                '''
                print('BEF(YD_S+D)')
#               print(json.dumps(json.loads(response), indent=4, sort_keys=False))
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_S+D)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_OPT':
                response = yq_tickers.option_chain_LOC()

                '''
                print('BEF(YD_OPT)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_OPT)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_MISC0':
                response = yq_tickers.corporate_events_LOC()

                '''
                print('BEF(YD_MISC0)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_MISC0)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_MISC1':
                response = yq_tickers.recommendations_LOC()

                '''
                print('BEF(YD_MISC1)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_MISC1)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_MISC2':
                response = yq_tickers.technical_insights_LOC()

                '''
                print('BEF(YD_MISC2)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_MISC2)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_FIN':
                response = yq_tickers.all_financial_data_LOC()

                '''
                print('BEF(YD_FIN)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_FIN)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_FIN0':
                response = yq_tickers.balance_sheet_LOC()

                '''
                print('BEF(YD_FIN0)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_FIN0)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_FIN1':
                response = yq_tickers.cash_flow_LOC()

                '''
                print('BEF(YD_FIN1)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_FIN1)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_FIN2':
                response = yq_tickers.income_statement_LOC()

                '''
                print('BEF(YD_FIN2)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_FIN2)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_FIN3':
                response = yq_tickers.valuation_measures_LOC()

                '''
                print('BEF(YD_FIN3)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_FIN3)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_TS0':
                response = yq_tickers.history_LOC(period='1d', interval = '1m', adj_ohlc=False)

                '''
                print('BEF(YD_TS0)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_TS0)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_TS1':
                response = yq_tickers.history_LOC(period='7d', interval = '1m', adj_ohlc=False)

                '''
                print('BEF(YD_TS1)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_TS1)')
                '''

                response = json.dumps(response, separators=(',', ':'))


            elif batch_list[0]['query_type'] =='YD_TS2':
                response = yq_tickers.history_LOC(period='1mo', interval = '1m', adj_ohlc=False)

                '''
                print('BEF(YD_TS2)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_TS2)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif batch_list[0]['query_type'] =='YD_MOD':
                response = yq_tickers.all_modules

                '''
                print('BEF(YD_MOD)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_MOD)')
                '''

                response = json.dumps(response, separators=(',', ':'))

            elif (m := re.match('YD_MOD(\d+)', batch_list[0]['query_type'])):
                idx_mod = int(m.group(1))

                yahoo_modules = [
                    "assetProfile",
                    "balanceSheetHistory",
                    "balanceSheetHistoryQuarterly",
                    "calendarEvents",
                    "cashflowStatementHistory",
                    "cashflowStatementHistoryQuarterly",
                    "defaultKeyStatistics",
                    "earnings",
                    "earningsHistory",
                    "earningsTrend",
                    "esgScores",
                    "financialData",
                    "fundOwnership",
                    "fundPerformance",
                    "fundProfile",
                    "indexTrend",
                    "incomeStatementHistory",
                    "incomeStatementHistoryQuarterly",
                    "industryTrend",
                    "insiderHolders",
                    "insiderTransactions",
                    "institutionOwnership",
                    "majorHoldersBreakdown",
                    "pageViews",
                    "price",
                    "quoteType",
                    "recommendationTrend",
                    "secFilings",
                    "netSharePurchaseActivity",
                    "sectorTrend",
                    "summaryDetail",
                    "summaryProfile",
                    "topHoldings",
                    "upgradeDowngradeHistory",
                ]

                num_module_segs = 3

                len_seg_c = math.ceil(len(yahoo_modules) / num_module_segs)
                len_seg_f = math.floor(len(yahoo_modules) / num_module_segs)

                len_seg = len_seg_c

                idx0 = len(yahoo_modules) % num_module_segs

                idx = 0

                idx_beg = -len_seg
                idx_end = 0

                while idx <= idx_mod:
                   idx_beg = idx_end
                   idx_end = idx_end + len_seg

                   idx += 1

                   if idx == idx0:
                       len_seg = len_seg_f

#                  print(f"QQQ:  idx={idx}  idx_mod={idx_mod}  idx0={idx0}  len_seg={len_seg}  idx_beg:idx_end={idx_beg}:{idx_end}")


#               print(f"idx_beg:idx_end={idx_beg}:{idx_end}")
                response = yq_tickers.get_modules(yahoo_modules[idx_beg:idx_end])

                '''
                print('BEF(YD_MODx)')
                print(json.dumps(response, indent=4, sort_keys=False))
                print('AFT(YD_MODx)')
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

        symbols_str = '<<' + ','.join(item['qry_symbol'] for item in batch_list) + '>>'

        type = batch_list[0]['query_type']

        if type in self.pseudo_URL:
            query = self.pseudo_URL[type] + symbols_str
        else:
            query = 'https://query2.finance.yahoo.com/v8/finance/chart/<<UNKNOWN>>' + symbols_str

        query_sanitized = query


        return query, query_sanitized, batch_list[0]['query_type']


    #  SUBCLASS OVERRIDE

    #  Convert response to dictionary
    def response_to_dictionary(self, query_raw):

        query_json = json.loads(query_raw)


        #  Remove extraneous layers from the JSON
#       query_json = query_json["chart"]["result"]


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
#       print(f"query_raw='{query_raw}'")
        #  TODO FIXME:  Tailor handling to type of query.
        return self.query_raw_norm.sub(' ', query_raw)


    #  SUBCLASS OVERRIDE

    def get_query_stock(self, qry_symbol, query_json):
        query_stock = None

        query_stock = query_json[qry_symbol]

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
