# -*- coding: utf-8 -*-

"""config.py:  Creates and initializes Tlaloc's core data structures which hold
   Tlaloc's runtime parameters.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import threading
from multiprocessing import Process, JoinableQueue

from pathlib import Path
import os
import sys


runtime_params = {
    'cur_dir':  '',
    'log_dir':  '',

    'config_file':  'config.txt',
    'creds_file':   'credentials.txt',

    'user_config':  {},
    'credentials':  {},

    'skip_query':  False,

    'dry_run':  False,

    'production':  True,

    'playback': False,

    'skip_first_day':  False,

    'offset_mkt_begin':  False,

    'shuffle_queries':  True,

    'enable_ticker':  False,

    'skip_log_quotes':  False,
    'skip_log_ticker':  False,

    'proxies': {},
    'ca_cert': '',

    #  BEG:  FUTURE - DISTRIBUTE INFO TO CLIENTS
    'use_SSL':  True,

    'server_cred_file':  "server_99.pem",
    'client_cred_file':  "public_99.pem",

    'pt2_executive_port':  8789,
    'pt3_subscribe_port':  8788,
    #  END:  FUTURE - DISTRIBUTE INFO TO CLIENTS

    'debug_options': {
         'stock':         False,
         'query':         True,
         'query_raw':     False,
         'query_ugly':    False,
         'query_pretty':  False,
         'query_extract': False,
         'threads':       False,
         'src_attr_lvl0': False,
         'src_attr_lvl1': False,
         'src_attr_lvl2': False,
         'src_attr_lvl3': False,
    },

    'source_list': {
        'CNBC_Intraday':      False,
        'CNBC_Daily':         False,
        'Yahoo_Intraday':     False,
        'Yahoo_Daily':        False,
        'Reuters_Daily':      False,
        'IEX_Intraday':       False,
        'AlphaVantage_Daily': False,
        'MarketData_Daily':   False,
    },

    'sources':  {
        'CNBC_Intraday':      None,
        'CNBC_Daily':         None,
        'Yahoo_Intraday':     None,
        'Yahoo_Daily':        None,
        'Reuters_Daily':      None,
        'IEX_Intraday':       None,
        'AlphaVantage_Daily': None,
        'MarketData_Daily':   None,
    },

    'symbols': ['AAPL', ],

    'market_holidays': [
#       '21-01-01', '21-01-18', '21-02-15', '21-04-02', '21-05-31',             '21-07-05', '21-09-06', '21-11-25', '21-12-24',
#                   '22-01-17', '22-02-21', '22-04-15', '22-05-30', '22-06-20', '22-07-04', '22-09-05', '22-11-24', '22-12-26',
#       '23-01-02', '23-01-16', '23-02-20', '23-04-07', '23-05-29', '23-06-19', '23-07-04', '23-09-04', '23-11-23', '23-12-25',
        '24-01-01', '24-01-15', '24-02-19', '24-03-29', '24-05-27', '24-06-19', '24-07-04', '24-09-02', '24-11-28', '24-12-25',
        '25-01-01', '25-01-20', '25-02-17', '25-04-18', '25-05-26', '25-06-19', '25-07-04', '25-09-01', '25-11-27', '25-12-25',
        '26-01-01', '26-01-19', '26-02-16', '26-04-03', '26-05-25', '26-06-19', '26-07-03', '26-09-07', '26-11-26', '26-12-25',
    ],
}


#  Determine whether Pathlib is available
if sys.version_info[0] >= 3 and sys.version_info[1] >= 6:
    runtime_params['use_pathlib'] = True
else:
    runtime_params['use_pathlib'] = False

#  Default the current working and logging directories
if runtime_params['use_pathlib']:
    runtime_params['cur_dir'] = Path.cwd()
    runtime_params['log_dir'] = Path.home() / 'logs'
else:
    runtime_params['cur_dir'] = os.getcwd()
    runtime_params['log_dir'] = os.path.join(os.path.expanduser('~'), "logs")


sp_queue     = JoinableQueue()    # None
qu_entry_idx = 0                  # None
tk_entry_idx = 0                  # None
log_quotes   = None
log_ticker   = None
log_q_lock   = threading.Lock()   # None
log_t_lock   = threading.Lock()   # None

