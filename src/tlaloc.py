#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""tlaloc.py:  The core of the Tlaloc software is implemented here.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

#  Query online data sources and record raw data into a quote log and
#  semiprocessed data into a ticker log.

#  TODO:
#  - Modify yahoo instrumentation to be contollable by user parameters.
#  - Split out source classes into separate files

import config

import json
import re
#mport pprint


# BEG tlaloc.py SPECIFIC
from utils  import days_to_next_session

from datetime import datetime
from datetime import timedelta

import logging

import threading

import argparse

from multiprocessing import Process, JoinableQueue

from pathlib import Path
import os
import sys
import time
import signal


try:
    from zope.interface import implementer
except ImportError as error:
    print("IMPORT ERROR:  (zope.interface) implementer")

try:
    from twisted.spread import pb
except ImportError as error:
    print("IMPORT ERROR:  (twisted.spread) pb")

try:
    from twisted.internet import reactor
except ImportError as error:
    print("IMPORT ERROR:  (twisted.internet) reactor")

try:
    from twisted.internet import ssl
except ImportError as error:
    print("IMPORT ERROR:  (twisted.internet) ssl")

'''
try:
    from twisted.cred import credentials
except ImportError as error:
    print("IMPORT ERROR:  (twisted.cred) credentials")
'''

try:
    from twisted.cred import portal
except ImportError as error:
    print("IMPORT ERROR:  (twisted.cred) portal")

try:
    from twisted.cred import checkers
except ImportError as error:
    print("IMPORT ERROR:  (twisted.cred) checkers")

'''
try:
    from twisted.python import util
except ImportError as error:
    print("IMPORT ERROR:  (twisted.python) util")
'''

try:
    from twisted.python.modules import getModule
except ImportError as error:
    print("IMPORT ERROR:  (twisted.python.modules) getModule")


from Source_AlphaVantage_DailySummary   import Source_AlphaVantage_DailySummary
from Source_CNBC_IntradayQuote          import Source_CNBC_IntradayQuote
from Source_CNBC_DailySummary           import Source_CNBC_DailySummary
from Source_IEX_IntradayQuote           import Source_IEX_IntradayQuote
from Source_MarketData_DailySummary     import Source_MarketData_DailySummary
from Source_Reuters_DailySummary        import Source_Reuters_DailySummary
from Source_Yahoo_IntradayQuote         import Source_Yahoo_IntradayQuote
from Source_Yahoo_DailySummary          import Source_Yahoo_DailySummary

from Source_Playback                    import Source_Playback
# END tlaloc.py SPECIFIC


def print_hi(part):
    print('Tlaloc V0.1  (' + part + ')')


def log_rotate_pt1():

    #  Create locks if needed
    if config.log_q_lock is None:
        config.log_q_lock = threading.Lock()

    if config.log_t_lock is None:
        config.log_t_lock = threading.Lock()


    #  If log files are open, close them
    with config.log_q_lock:
        if config.log_quotes is not None:
            config.log_quotes.close()

    with config.log_t_lock:
        if config.log_ticker is not None:
            config.log_ticker.close()


    #  Determine log directory and ensure it exists
    if config.runtime_params['use_pathlib']:
        log_dir = config.runtime_params['log_dir'] / 'tl_pt1'

        log_dir.mkdir(parents=True, exist_ok=True)
    else:
        log_dir = os.path.join(config.runtime_params['log_dir'], 'tl_pt1')

        if (not os.path.exists(log_dir)):
            os.path.mkdir (log_dir)

    now = datetime.now()

    #  Determine if this process has been told to self terminate
#   if runtime_params['use_pathlib']:
#       test_file = config.runtime_params['cur_dir'] / 'reboot1.txt'
#   else:
#       test_file = os.path.join(config.runtime_params['cur_dir'], 'reboot1.txt')

    test_file = os.path.join(str(config.runtime_params['cur_dir']), 'reboot1.txt')

    if os.path.isfile(test_file):
        print("LOG ROTATE:  Found file '%s'.  Renaming file and terminating process %s for reboot." % (str(test_file), str(os.getpid())), flush=True)
        os.rename(str(test_file), str(test_file) + '_' + now.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3])

        os.kill(os.getpid(), signal.SIGABRT)

        print('ERROR(log_rotate_pt1()):  SIGABRT did not work.  Trying SIGKILL', flush=True)
        os.kill(os.getpid(), signal.SIGKILL)

        print('ERROR(log_rotate_pt1()):  SIGKILL did not work.  Trying os._exit().', flush=True)
        os._exit(os.EX_OK)

        print('ERROR(log_rotate_pt1()):  os._exit()  did not work.  Soldiering on.', flush=True)


    if not config.runtime_params['skip_log_quotes']:
        quotes_file = 'quotes_' + now.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3] + '.txt'
    else:
        quotes_file = '<<QUOTE LOGGING OFF>>'

    if not config.runtime_params['skip_log_ticker']:
        ticker_file = 'ticker_' + now.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3] + '.txt'
    else:
        ticker_file = '<<TICKERLOGGING OFF>>'

    print("LOG ROTATE:  Opening new log files -- quotes_file='%s'   ticker_file='%s'   log_dir='%s'" % (quotes_file, ticker_file, str(log_dir)), flush=True)

    if not config.runtime_params['skip_log_quotes']:
        if config.runtime_params['use_pathlib']:
            with config.log_q_lock:
                config.log_quotes = open(str(log_dir / quotes_file), 'a')
        else:
            with config.log_q_lock:
                config.log_quotes = open(str(log_dir + '/' + quotes_file), 'a')
    else:
        config.log_quotes = None

#   if not config.runtime_params['skip_log_ticker']:
#       if config.runtime_params['use_pathlib']:
#           with config.log_t_lock:
#               config.log_ticker = open(str(log_dir / ticker_file), 'a')
#       else:
#           with config.log_t_lock:
#               config.log_ticker = open(str(log_dir + '/' +  ticker_file), 'a')
#   else:
#       config.log_ticker = None

    next_rotate = now.replace(hour=0, minute=0, second=9) + timedelta(days = 1)

    delta = next_rotate - datetime.now()

    reactor.callLater(delta.total_seconds(), log_rotate_pt1)

    print("LOG ROTATE:  Next rotate at %s  (%d seconds)" % (
        next_rotate.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], round (delta.total_seconds())), flush=True)


# TODO:  Consider combining log_rotate_pt1() and log_rotate_pt2() into one function.

def log_rotate_pt2():

    #  Create locks if needed
    if config.log_q_lock is None:
        config.log_q_lock = threading.Lock()

    if config.log_t_lock is None:
        config.log_t_lock = threading.Lock()


    #  If log files are open, close them
    with config.log_q_lock:
        if config.log_quotes is not None:
            config.log_quotes.close()

    with config.log_t_lock:
        if config.log_ticker is not None:
            config.log_ticker.close()


    #  Determine log directory and ensure it exists
    if config.runtime_params['use_pathlib']:
        log_dir = config.runtime_params['log_dir'] / 'tl_pt2'

        log_dir.mkdir(parents=True, exist_ok=True)
    else:
        log_dir = os.path.join(config.runtime_params['log_dir'], 'tl_pt2')

        if (not os.path.exists(log_dir)):
            os.path.mkdir (log_dir)

    now = datetime.now()

    #  Determine if this process has been told to self terminate
#   if runtime_params['use_pathlib']:
#       test_file = config.runtime_params['cur_dir'] / 'reboot2.txt'
#   else:
#       test_file = os.path.join(config.runtime_params['cur_dir'], 'reboot2.txt')

    test_file = os.path.join(str(config.runtime_params['cur_dir']), 'reboot2.txt')

    if os.path.isfile(test_file):
        print("LOG ROTATE:  Found file '%s'.  Renaming file and terminating process %s for reboot." % (str(test_file), str(os.getpid())), flush=True)
        os.rename(str(test_file), str(test_file) + '_' + now.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3])

        os.kill(os.getpid(), signal.SIGABRT)

        print('ERROR(log_rotate_pt2()):  SIGABRT did not work.  Trying SIGKILL', flush=True)
        os.kill(os.getpid(), signal.SIGKILL)

        print('ERROR(log_rotate_pt2()):  SIGKILL did not work.  Trying os._exit().', flush=True)
        os._exit(os.EX_OK)

        print('ERROR(log_rotate_pt2()):  os._exit()  did not work.  Soldiering on.', flush=True)


    if not config.runtime_params['skip_log_quotes']:
        quotes_file = 'quotes_' + now.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3] + '.txt'
    else:
        quotes_file = '<<QUOTE LOGGING OFF>>'

    if not config.runtime_params['skip_log_ticker']:
        ticker_file = 'ticker_' + now.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3] + '.txt'
    else:
        ticker_file = '<<TICKERLOGGING OFF>>'

    print("LOG ROTATE:  Opening new log files -- quotes_file='%s'   ticker_file='%s'   log_dir='%s'" % (quotes_file, ticker_file, str(log_dir)), flush=True)

    if not config.runtime_params['skip_log_quotes']:
        if config.runtime_params['use_pathlib']:
            with config.log_q_lock:
                config.log_quotes = open(str(log_dir / quotes_file), 'a')
        else:
            with config.log_q_lock:
                config.log_quotes = open(str(log_dir + '/' + quotes_file), 'a')
    else:
        config.log_quotes = None

    if not config.runtime_params['skip_log_ticker']:
        if config.runtime_params['use_pathlib']:
            with config.log_t_lock:
                config.log_ticker = open(str(log_dir / ticker_file), 'a')
        else:
            with config.log_t_lock:
                config.log_ticker = open(str(log_dir + '/' +  ticker_file), 'a')
    else:
        config.log_ticker = None

    next_rotate = now.replace(hour=0, minute=0, second=9) + timedelta(days = 1)

    delta = next_rotate - datetime.now()

    reactor.callLater(delta.total_seconds(), log_rotate_pt2)

    print("LOG ROTATE:  Next rotate at %s  (%d seconds)" % (
        next_rotate.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], round (delta.total_seconds())), flush=True)


def reset_all_backoff():

    # Loop over sources, backing each off
    for source in config.runtime_params['sources']:
        source.reset_backoff(source.backoff.keys())


    #  Schedule next backoff
    next_rotate = datetime.now().replace(hour=0, minute=0, second=9) + timedelta(days = 1)

    delta = next_rotate - datetime.now()

    reactor.callLater(delta.total_seconds(), reset_all_backoff)

    print("BACKOFF RESET:  Next reset at %s  (%d seconds)" % (
        next_rotate.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], round (delta.total_seconds())))


def tlaloc_pt1_run():

    # Loop over sources, kicking each off
    for source in config.runtime_params['sources']:
        reactor.callWhenRunning(source.run_recurring_query)

    print('Start!')
    reactor.run()
    print('Stop!')


def print_runtime_params ():

    print(f"")
    print(f"")
    print(f"Runtime Parameters")
    print(f"               cur_dir = {config.runtime_params['cur_dir']}")
    print(f"               log_dir = {config.runtime_params['log_dir']}")
    print(f"           config_file = {config.runtime_params['config_file']}")
    print(f"            creds_file = {config.runtime_params['creds_file']}")
    print(f"            skip_query = {config.runtime_params['skip_query']}")
    print(f"               dry_run = {config.runtime_params['dry_run']}")
    print(f"            production = {config.runtime_params['production']}")
    print(f"              playback = {config.runtime_params['playback']}")
    print(f"        skip_first_day = {config.runtime_params['skip_first_day']}")
    print(f"      offset_mkt_begin = {config.runtime_params['offset_mkt_begin']}")
    print(f"       shuffle_queries = {config.runtime_params['shuffle_queries']}")
    print(f"         enable_ticker = {config.runtime_params['enable_ticker']}")
    print(f"       skip_log_quotes = {config.runtime_params['skip_log_quotes']}")
    print(f"       skip_log_ticker = {config.runtime_params['skip_log_ticker']}")
    print(f"               proxies = {config.runtime_params['proxies']}")
    print(f"               ca_cert = {config.runtime_params['ca_cert']}")
# FUTURE:   print(f"               use_SSL = {config.runtime_params['use_SSL']}")
# FUTURE:   print(f"      server_cred_file = <<REDACTED>>")
# FUTURE:   print(f"      client_cred_file = <<REDACTED>>")
# FUTURE:   print(f"    pt2_executive_port = {config.runtime_params['pt2_executive_port']}")
# FUTURE:   print(f"    pt3_subscribe_port = {config.runtime_params['pt3_subscribe_port']}")
    print(f"")
    print(f"         debug_options:")
    print(f"                 stock = {config.runtime_params['debug_options']['stock']}")
    print(f"                 query = {config.runtime_params['debug_options']['query']}")
    print(f"             query_raw = {config.runtime_params['debug_options']['query_raw']}")
    print(f"            query_ugly = {config.runtime_params['debug_options']['query_ugly']}")
    print(f"          query_pretty = {config.runtime_params['debug_options']['query_pretty']}")
    print(f"         query_extract = {config.runtime_params['debug_options']['query_extract']}")
    print(f"               threads = {config.runtime_params['debug_options']['threads']}")
    print(f"         src_attr_lvl0 = {config.runtime_params['debug_options']['src_attr_lvl0']}")
    print(f"         src_attr_lvl1 = {config.runtime_params['debug_options']['src_attr_lvl1']}")
    print(f"         src_attr_lvl2 = {config.runtime_params['debug_options']['src_attr_lvl2']}")
    print(f"         src_attr_lvl3 = {config.runtime_params['debug_options']['src_attr_lvl3']}")
    print(f"")
    print(f"           source_list:")
    print(f"         CNBC_Intraday = {config.runtime_params['source_list']['CNBC_Intraday']}")
    print(f"            CNBC_Daily = {config.runtime_params['source_list']['CNBC_Daily']}")
    print(f"        Yahoo_Intraday = {config.runtime_params['source_list']['Yahoo_Intraday']}")
    print(f"           Yahoo_Daily = {config.runtime_params['source_list']['Yahoo_Daily']}")
    print(f"         Reuters_Daily = {config.runtime_params['source_list']['Reuters_Daily']}")
    print(f"          IEX_Intraday = {config.runtime_params['source_list']['IEX_Intraday']}")
    print(f"    AlphaVantage_Daily = {config.runtime_params['source_list']['AlphaVantage_Daily']}")
    print(f"      MarketData_Daily = {config.runtime_params['source_list']['MarketData_Daily']}")
    print(f"")
    print(f"               symbols = [{', '.join(config.runtime_params['symbols'])}]")
    print(f"")
    print(f"       market_holidays = [{', '.join(config.runtime_params['market_holidays'])}]")


def read_config_file(file_name):

    #  Default output parameters
    config_text = ''


    #  Compile regexes used to remove comments from config files
    cmnt_regex0 = re.compile('^(.*)(#@!.*)$')
    cmnt_regex1 = re.compile('^((?s:.)*?)(#@>(?s:.)*?<@#)((?s:.)*$)')


    #  Read the lines from the config file
    try:
        with open(file_name) as fp:
            lines = fp.readlines()

    except IOError as e:
        print('Operation failed: %s' % e.strerror)
        return config_text


    #  Clean up individual lines and concatenate them
    for line in lines:

        #  Remove white space and line breaks from ends of line
        line = line.strip()

        #  Remove to end of line comments
        while m := cmnt_regex0.match(line):
            line = m.group(1).strip()

        #  Concatenate lines with content
        if 0 < len(line):
            config_text = config_text + ' \n' + line


    #  Remove multi-line comments
    while m := cmnt_regex1.match(config_text):
        config_text = m.group(1) + m.group(3)


    #  Remove blank lines
    config_text = re.sub('( *\n)+', ' \n', config_text)
    config_text = re.sub('^( *\n)+$', '', config_text)


    #  Pass config text back to caller
    return config_text


def read_user_config():

    #  Read the text and remove comments
    config_text = read_config_file(config.runtime_params['config_file'])

    #  Update runtime_parms data structure if text is not null
    if not '' == config_text:
        try:
           config.runtime_params['user_config'] = json.loads(config_text.replace('\n', ' '))

           print(f'\n\n')
           print(f'Result of parsing of "{config.runtime_params["config_file"]}"')
           print(json.dumps(config.runtime_params['user_config'], indent=4))

        except BaseException as e:
           print(f'ERROR PARSING "{config.runtime_params["config_file"]}" ({str(e)})')
           print(f'BEG Text of config file (after comments removed)')
           print(config_text)
           print(f'END Text of config file (after comments removed)')

           return


def read_credentials():

    #  Read the text and remove comments
    config_text = read_config_file(config.runtime_params['creds_file'])

    #  Update runtime_parms data structure if text is not null
    if not '' == config_text:
        try:
           config.runtime_params['credentials'] = json.loads(config_text.replace('\n', ' '))
		   
        except BaseException as e:
           print(f'ERROR PARSING "{config.runtime_params["creds_file"]}" ({str(e)})')

           return


# my_parser.add_argument('-v',
#                        '--verbosity',
#                        action='store',
#                        type=int,    #  type=bool
#                        metavar='LEVEL',
#                        dest='my_verbosity_level',

#                        nargs='2',  #  nargs='+', '*', '?'
#                        required=True,
#                        choices=range(1, 5),   # choices=['head', 'tail'],
#                        default='5',
#                        help='set the user choice to head or tail')

# my_group = my_parser.add_mutually_exclusive_group(required=True)
# my_group.add_argument('-v', '--verbose', action='store_true')
# my_group.add_argument('-s', '--silent', action='store_true')

#       'dry_run':  False,
#       'playback': False,
#       'production':  True,
#       'shuffle_queries': False,
#       'skip_first_day':  False,
#       'enable_ticker':  False,
#       'skip_log_quotes':  False,
#       'skip_log_ticker':  False,


#  Adapted from:  https://github.com/symonsoft/str2bool/blob/master/str2bool/__init__.py
def loc_strtobool(value, raise_exc=False):
    _true_set = {'yes', 'true', 't', 'y', '1'}
    _false_set = {'no', 'false', 'f', 'n', '0'}

    if isinstance(value, str) or sys.version_info[0] < 3 and isinstance(value, basestring):
        value = value.lower()
        if value in _true_set:
            return True
        if value in _false_set:
            return False

    if raise_exc:
        raise ValueError('Expected "%s"' % '", "'.join(_true_set | _false_set))
    return None


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
#       usage="%(prog)s [OPTION] [FILE]...",
        description="Obtain market data from data sources.",
    )
    parser.add_argument( "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0 (2022-02-19a)")

    parser.add_argument('--cur_dir',         dest='cur_dir',         metavar='<file name>',  type=str)
    parser.add_argument('--log_dir',         dest='log_dir',         metavar='<file name>',  type=str)
    parser.add_argument('--config_file',     dest='config_file',     metavar='<file name>',  type=str)
    parser.add_argument('--cred_file',       dest='cred_file',       metavar='<file name>',  type=str)
    parser.add_argument('--skip_query',      dest='skip_query',      metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--dry_run',         dest='dry_run',         metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--production',      dest='production',      metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--playback',        dest='playback',        metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--skip_first_day',  dest='skip_first_day',  metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--offset_begin',    dest='offset_begin',    metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--shuffle_queries', dest='shuffle_queries', metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--enable_ticker',   dest='enable_ticker',   metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--skip_log_quotes', dest='skip_log_quotes', metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--skip_log_ticker', dest='skip_log_ticker', metavar='<True|False>', type=lambda x:bool(loc_strtobool(x)))
    parser.add_argument('--proxies',         dest='proxies',         metavar='<proxy url>',  type=str)
    parser.add_argument('--ca_cert',         dest='ca_cert',         metavar='<file name>',  type=str)

    parser.add_argument('--debug',   dest='debug',   metavar='<debug_1,...,debug_N>',   type=str)
    parser.add_argument('--sources', dest='sources', metavar='<source_1,...,source_N>', type=str)
    parser.add_argument('--symbols', dest='symbols', metavar='<symbol_1,...,symbol_N>', type=str)

    return parser


def tlaloc_pt1():

    #  Initialize parse of command line arguments
    arg_parser = init_argparse()

    args = arg_parser.parse_args()


    #  Process config file command line arguments
    if ('cur_dir' in args) and (args.cur_dir is not None):
        config.runtime_params['cur_dir'] = Path(args.cur_dir)

        #  Change the directory now to pick up config files in the 'cur_dir'
        os.chdir(config.runtime_params['cur_dir'])

    if ('config_file' in args) and (args.config_file is not None):
        config.runtime_params['config_file'] = args.config_file

    if ('cred_file' in args) and (args.cred_file is not None):
        config.runtime_params['creds_file'] = args.cred_file


    #  Read config files
    read_user_config()

    read_credentials()


    #  Assimilate global parameters
    if 'global' in config.runtime_params['user_config']:
        for (key, item) in config.runtime_params['user_config']['global'].items():
            if (key in config.runtime_params) and (key != 'user_config'):
                config.runtime_params[key] = config.runtime_params['user_config']['global'][key]
            else:
                print(f'WARNING(tlaloc_pt1()):  Skipping global input parameter "{key}" because it is not a runtime configuration parameter.')


    #  Finish assimilating command line arguments
    if ('log_dir' in args) and (args.log_dir is not None):
        config.runtime_params['log_dir'] = Path(args.log_dir)

    if ('skip_query' in args) and (args.skip_query is not None):
        config.runtime_params['skip_query'] = args.skip_query

    if ('dry_run' in args) and (args.dry_run is not None):
        config.runtime_params['dry_run'] = args.dry_run

    if ('production' in args) and (args.production is not None):
        config.runtime_params['production'] = args.production

    if ('playback' in args) and (args.playback is not None):
        config.runtime_params['playback'] = args.playback

    if ('skip_first_day' in args) and (args.skip_first_day is not None):
        config.runtime_params['skip_first_day'] = args.skip_first_day

    if ('offset_begin' in args) and (args.offset_begin is not None):
        config.runtime_params['offset_mkt_begin'] = args.offset_begin

    if ('shuffle_queries' in args) and (args.shuffle_queries is not None):
        config.runtime_params['shuffle_queries'] = args.shuffle_queries

    if ('enable_ticker' in args) and (args.enable_ticker is not None):
        config.runtime_params['enable_ticker'] = args.enable_ticker

    if ('skip_log_quotes' in args) and (args.skip_log_quotes is not None):
        config.runtime_params['skip_log_quotes'] = args.skip_log_quotes

    if ('skip_log_ticker' in args) and (args.skip_log_ticker is not None):
        config.runtime_params['skip_log_ticker'] = args.skip_log_ticker

    if ('proxies' in args) and (args.proxies is not None):
        config.runtime_params['proxies'] = args.proxies

    if ('ca_cert' in args) and (args.ca_cert is not None):
        config.runtime_params['ca_cert'] = args.ca_cert


    #  Handle debug arguments
    if ('debug' in args) and (args.debug is not None):
        debug_str = args.debug

        debug_list = debug_str.split(",")

        for debug_opt in debug_list:
            if debug_opt in config.runtime_params['debug_options']:
                config.runtime_params['debug_options'][debug_opt] = True
            else:
                print(f"ERROR(tlaloc_pt1()):  unknown debug type ('{debug_opt}')")
                error = True


    #  Handle source arguments
    if ('sources' in args) and (args.sources is not None):
        sources_str = args.sources

        sources_list = sources_str.split(",")

        for sources_opt in sources_list:
            if sources_opt in config.runtime_params['source_list']:
                config.runtime_params['source_list'][sources_opt] = True
            else:
                print(f"ERROR(tlaloc_pt1()):  unknown source type ('{sources_opt})")
                error = True


    #  Handle stock arguments
    if ('symbols' in args) and (args.symbols is not None):
        symbols_str = args.symbols

        config.runtime_params['symbols'] = symbols_str.split(",")


    #  If we are in playback mode then turn off production
    if config.runtime_params['playback']:
        config.runtime_params['production'] = False


    #  Change the directory (if needed)
    if not str(os.getcwd()) == str(config.runtime_params['cur_dir']):
        os.chdir(config.runtime_params['cur_dir'])


    #  Print out the runtime parameters in effect
    print_runtime_params ()


    #  Open log files

    format = "PT1:  %(asctime)s: %(message)s"

    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")


    print_hi('pt1')


    #  Spin off quote aggregator task

    # tlaloc_pt2() reads from queue as a different process...
    if not config.runtime_params['skip_query']:
        tlaloc_pt2_proc = Process(target=tlaloc_pt2, args=(config.sp_queue, config.runtime_params))
        tlaloc_pt2_proc.daemon = True
        tlaloc_pt2_proc.start()
    else:
        print('ALERT:  Skipping invocation of Process 2 because "skip_query" option given on command line')


    #  Create logs
    log_rotate_pt1 ()


    #  Create objects for the requested sources
    if not config.runtime_params['playback']:
        config.runtime_params['sources'] = get_sources(config.runtime_params['source_list'])
    else:
        config.runtime_params['sources'] = [Source_Playback()]


    #  Reset backoff background job
    reset_all_backoff()


    #  Kickoff
    tlaloc_pt1_run()


    #  If log files are open, close them
    with config.log_q_lock:
        if config.log_quotes is not None:
            config.log_quotes.close()

    with config.log_t_lock:
        if config.log_ticker is not None:
            config.log_ticker.close()

    print("TLALOC PT1 DONE")


def make_null_stock_entries(stocks, sources):
    stock_data = {}

    for stock in stocks:
        null_entry = {}

        for source in sources:
            null_entry[source.src_name] = source.make_stock_entry()

        stock_data[stock] = null_entry

    return stock_data


#   query_msg = "\n" + \
#               "\n" + \
#               "ENTRY[%06d]:  TYPE=QUOTE  TIME=%s  QUERY_TYPE=%s  VERSION=%s\n" % ('%06d', log_timestamp, query_type_loc, self.version) \
#               batch_str + "\n" + \
#               query_sanitized + "\n" + \
#               query_raw + "\n"

def parse_pipe_msg(quote_str, ts_regex, sources):

    #  Deconstruct the lines of the quote, stripping extra space in the process
    parts = quote_str.splitlines()

    for idx in range(len(parts)):
        parts[idx].strip()

    while (parts[0] == ''):
        parts = parts[1:]

    while (parts[-1] == ''):
        parts.pop()


    #  Log the normalized lines of the quote
#   for idx in range(len(parts)):
#       with config.log_q_lock:
#           config.log_quotes.write("{0}:  '{1}'\n".format(idx, parts[idx]))


    #  Use a regular expression to extract the timestamp
    match = ts_regex.match(parts[0])

    log_timestamp = match.group(1)
    query_type = match.group(2)
    version = match.group(3)


    #  Package the deconstructed quote into a dictionary
    quote = {
        'timestamp':  log_timestamp,
        'entry':      parts[0],
        'stocks':     parts[1],
        'url':        parts[2],
        'response':   parts[3],
        'query_type': query_type,
        'version':    version,
    }


    #  Log the resulting deconstructed quote
#   with config.log_q_lock:
#       config.log_quotes.write("XXX>  '{0}'\n".format(str(quote)))


    #  Identify the source of the quote
    for source in sources:
        if source.id_quote(quote['url']):
            return source, quote


    #  Could not identify source, return default response
    return None, quote


def quoteToTwistedEvent_step2(symbol, message):
    print ("ENTER  quoteToTwistedEvent_step2():  message='" + message + "'")

    if config.runtime_params ['tickerServer'] is not None:
        config.runtime_params ['tickerServer'].broadCast('--TICKER--', '#TlalocTickerClient', symbol, message)


def quoteToTwistedEvent_step1(symbol, message):
    if config.runtime_params ['enable_ticker']:
        reactor.callFromThread(quoteToTwistedEvent_step2, symbol, message)


class TickerServer:
    def __init__(self, debug_connection):
        if debug_connection:
            print ("ENTER TickerServer::__init__()")

        self.groups = {}  # indexed by name
        self.debug_connection = debug_connection
#       self.symbols = { 'AAPL': True, '<<ALL>>': True, }
        self.symbols = { 'AAPL': True, }

    def joinGroup(self, groupname, user, allowMattress):
        if self.debug_connection:
            print ("ENTER TickerServer::joinGroup()  groupname='%s'  user='%s'" % (groupname, user))

        if groupname not in self.groups:
            if self.debug_connection:
                print ("ENTER TickerServer::joinGroup()  creating new group")

            self.groups[groupname] = Group(groupname, allowMattress)

        self.groups[groupname].addUser(user)
        return self.groups[groupname]

    def broadCast(self, from_user, groupname, symbol, message):
        if self.debug_connection:
            print ("ENTER TickerServer::broadCast()  from_user='%s'  groupname='%s'  symbol='%s'  message='%s'" % (from_user, groupname, symbol, message))

        print ("TODO:  review whether all broadcasts should be transmitted to all groups.  What if a user was a member of multiple groups?")

        if groupname in self.groups:
            if (symbol in self.symbols) or ('<<ALL>>' in self.symbols):
                if self.debug_connection:
                    print ("ENTER TickerServer::broadCast()  Broadcasting to groupname='%s'" % (groupname))

                self.groups[groupname].view_ticker (from_user, message)


@implementer(portal.IRealm)
class TickerRealm:
    def requestAvatar(self, avatarID, mind, *interfaces):
        print ("ENTER TickerRealm::requestAvatar()")
        assert pb.IPerspective in interfaces
        avatar = User(avatarID)
        avatar.server = self.server
        avatar.attached(mind)
        return pb.IPerspective, avatar, lambda a=avatar: a.detached(mind)


try:
    class User(pb.Avatar):
        def __init__(self, name):
            self.name = name

        def attached(self, mind):
            self.remote = mind

        def detached(self, mind):
            self.remote = None

        def perspective_joinGroup(self, groupname, allowMattress=True):
            return self.server.joinGroup(groupname, self, allowMattress)

        def send(self, message):
            self.remote.callRemote("print", message)
except:
    print ("NameError:  (class User) pb")


try:
    class Group(pb.Viewable):
        def __init__(self, groupname, allowMattress):
            self.name = groupname
            self.allowMattress = allowMattress
            self.users = []

        def addUser(self, user):
            self.users.append(user)

        def view_send(self, from_user, message):
            if not self.allowMattress and "mattress" in message:
                raise ValueError("Don't say that word")
            for user in self.users:
                user.send("<{}> says: {}".format(from_user.name, message))

        def view_ticker(self, user_name, message):
            for user in self.users:
                user.send("<{}> ticker: {}".format(user_name, message))
except:
    print ("NameError:  (class Group) pb")


def tlaloc_pt2_run():

    debug_connection = False

    if debug_connection:
        print ("ENTER:  tlaloc_pt2_run()")


    #  Start up thread that interacts with Pt1
    thrd = threading.Thread(target=tlaloc_pt2_rcv_loop)
    thrd.start()


    if config.runtime_params ['enable_ticker']:
        if debug_connection:
            print ("tlaloc_pt2_run()  Attempt to create realm")

        realm = TickerRealm ()
        config.runtime_params ['tickerServer'] = TickerServer (debug_connection)
        realm.server = config.runtime_params ['tickerServer']


        if debug_connection:
            print ("tlaloc_pt2_run()  Initialize authentication accounts")

        #  Set up authentication state
        print ("TODO:  Do not store credentials in memory.")

        checker = checkers.InMemoryUsernamePasswordDatabaseDontUse ()
        checker.addUser (b"alice", b"1234")
        checker.addUser (b"bob",   b"secret")
        checker.addUser (b"carol", b"fido")

        if debug_connection:
            print ("tlaloc_pt2_run()  create portal")

        pt2_portal = portal.Portal (realm, [checker])


        if config.runtime_params ['use_SSL']:

            if debug_connection:
                print ("tlaloc_pt2_run()  Attempt to get server credentials.")

            certData = getModule (__name__).filePath.sibling (config.runtime_params ['server_cred_file']).getContent ()
            certificate = ssl.PrivateCertificate.loadPEM (certData)

            if debug_connection:
                print ("tlaloc_pt2_run()  Attempt to call reactor.listenSSL ().  port=%d" % config.runtime_params ['pt2_executive_port'])

            reactor.listenSSL (config.runtime_params ['pt2_executive_port'], pb.PBServerFactory (pt2_portal), certificate.options ())
        else:

            if debug_connection:
                print ("tlaloc_pt2_run()  Attempt to call reactor.listenTCP ().  port=%d" % config.runtime_params ['pt2_executive_port'])

            reactor.listenTCP (config.runtime_params ['pt2_executive_port'], pb.PBServerFactory (pt2_portal))


    if debug_connection:
        print ("tlaloc_pt2_run()  call reactor.run()")

    reactor.run()


def tlaloc_pt2_rcv_loop():

    #  ENTRY[000000]:  TYPE=QUOTE  TIME=2022-09-11 19:45:56.179889 MDT  QUERY_TYPE=YD_MISC0  VERSION=2022-09-10a
    ts_regex = re.compile(r'ENTRY.*\s+TIME=(.*\S)\s+QUERY_TYPE=(\S+)\s+VERSION=(\S+).*$')


    print ("tlaloc_pt2_rcv_loop():  sleep for one second")
    time.sleep (1.0)


    #  Loop forever, reading from the queue shared with Pt1
    while True:
        quote_str = config.sp_queue.get()         #  Read from the queue and do nothing
        config.sp_queue.task_done()
        
        with config.log_q_lock:
            if config.log_quotes is not None:
                config.log_quotes.write(quote_str)

        source, quote = parse_pipe_msg(quote_str, ts_regex, config.runtime_params['sources'])

        if source is not None:
            source.process_query(quote['stocks'], quote['response'], quote['url'], quote['timestamp'], quote['query_type'], quote['version'])


def tlaloc_pt2(arg_sp_queue, arg_runtime_params):

    config.runtime_params = arg_runtime_params

    config.sp_queue = arg_sp_queue


    #  Open log files

    format = "PT2:  %(asctime)s: %(message)s"

    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")


    print_hi('pt2')


    log_rotate_pt2 ()


    config.runtime_params['sources'] = get_sources(config.runtime_params['source_list'])


    #  Initialize stock data
    stock_data = make_null_stock_entries(config.runtime_params['symbols'], config.runtime_params['sources'])


    tlaloc_pt2_run()


    #  If log files are open, close them
    with config.log_q_lock:
        if config.log_quotes is not None:
            config.log_quotes.close()

    with config.log_t_lock:
        if config.log_ticker is not None:
            config.log_ticker.close()

    print("TLALOC PT2 DONE")


def get_sources(source_list):
    sources = []

    if source_list['CNBC_Intraday'] is True:
        sources.append(Source_CNBC_IntradayQuote())

    if source_list['CNBC_Daily'] is True:
        sources.append(Source_CNBC_DailySummary())

    if source_list['Yahoo_Intraday'] is True:
        sources.append(Source_Yahoo_IntradayQuote())

    if source_list['Yahoo_Daily'] is True:
        sources.append(Source_Yahoo_DailySummary())

    if source_list['Reuters_Daily'] is True:
        sources.append(Source_Reuters_DailySummary())

    if source_list['IEX_Intraday'] is True:
        sources.append(Source_IEX_IntradayQuote())

    if source_list['AlphaVantage_Daily'] is True:
        sources.append(Source_AlphaVantage_DailySummary())

    if source_list['MarketData_Daily'] is True:
        sources.append(Source_MarketData_DailySummary())


    return sources


if __name__ == '__main__':

    import requests
    import logging

    tlaloc_pt1()
