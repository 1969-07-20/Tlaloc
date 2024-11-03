#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""daily_checker.py:  Checks Tlaloc log files for errors.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import argparse
import re
import sys
import shutil
from pathlib import Path
from datetime import date
from datetime import datetime
from datetime import timedelta


#  Version info
version_num = '0.1.0'
version_date = '2023-06-10a'

version = 'version %s (%s)' % (version_num, version_date)


query_regex = {
    'CI_QUOTE':   re.compile('^https://quote.cnbc.com/quote-html-webservice/quote.htm\?noform=1&partnerId=2&fund=1&exthrs=0&output=json&symbols=' + '.*' + '&requestMethod=quick'),
    'CD_QUOTE':   re.compile('^https://ts-api.cnbc.com/harmony/app/charts/1D.json\?symbol=' + '.*'),
    'YI_QUOTE':   re.compile('^https://query2.finance.yahoo.com/v6/finance/quote\?lang=en-US&region=US&corsDomain=finance.yahoo.com&symbols=' + '.*'),
    'YD_S+D':     re.compile('^https://query2.finance.yahoo.com/v8/finance/chart/'),
    'YD_OPT':     re.compile('^https://query2.finance.yahoo.com/v7/finance/options/'),
    'YD_MISC0':   re.compile('^https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/' + '.*'),
    'YD_MISC1':   re.compile('^https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/'),
    'YD_MISC2':   re.compile('^https://query2.finance.yahoo.com/ws/insights/v2/finance/insights\?lang=en-US&region=US&corsDomain=finance.yahoo.com&symbol='),
    'YD_TS':      re.compile('^https://query2.finance.yahoo.com/v8/finance/chart/'),
#   'YD_MOD':     re.compile('^https://query2.finance.yahoo.com/(v6|v10)/finance/quoteSummary/'),
#   'YD_MOD':     re.compile('^https://query2.finance.yahoo.com/(v6|v10)/finance/quoteSummary/'),
    'YD_MOD':     re.compile('^https://query(2|1).finance.yahoo.com/(v6|v10|v8)/finance/(quoteSummary|chart)/'),
    'YD_FIN':     re.compile('^https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/'),
    'RD_QUOTE':   re.compile('^https://www.reuters.com/companies/api/getFetchCompanyProfile/' + '.*'),
#   'II_QUOTE':   re.compile('^https://sandbox.iexapis.com/stable/stock/market/batch\?types=book&symbols=' + '.*' + '&range=5y&token='),
    'II_QUOTE':   re.compile('^https://cloud.iexapis.com/stable/stock/market/batch\?types=book&symbols=' + '.*' + '&range=5y&token=' + '.*'),
    'AD_QUOTE':   re.compile('^https://www.alphavantage.co/query\?function=TIME_SERIES_INTRADAY&symbol=' + '.*' + '&interval=' + '.*' + '&outputsize=full&apikey=' + '.*'),
    'MD_TS0':     re.compile('^https://api.marketdata.app/v1/stocks/candles/1/(.+)/\?from=(\d\d\d\d)-(\d\d)-(\d\d)&to=(\d\d\d\d)-(\d\d)-(\d\d)&dateformat=timestamp'),
    'MD_OPT0':    re.compile('^https://api.marketdata.app/v1/options/chain/(.+)/\?dateformat=timestamp'),
}


def id_quote(url):

    for key in query_regex.keys():
        id_URL = query_regex[key]

        if id_URL.match(url):
            return key


    return None


#  From:  https://stackoverflow.com/questions/34803467/unexpected-exception-name-basestring-is-not-defined-when-invoking-ansible2
try:
    basestring
except NameError:
    basestring = str


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


def init_argparse():
    parser = argparse.ArgumentParser(
#       usage="%(prog)s [OPTION] [FILE]...",
        description="Check Tlaloc logs for errors.",
    )
    parser.add_argument( "-v", "--version", action="version", version="%s %s" % (parser.prog, version))

    parser.add_argument('--beg_date', default='TODAY', dest='beg_date', type=str)
    parser.add_argument('--end_date', default='TODAY', dest='end_date', type=str)

    return parser


def parse_date(date_str):
    
    m = re.compile('^(\d\d\d\d)-(\d\d)-(\d\d)$')

    m_result = m.match(date_str)

    if m_result:
        yy = m_result.group(1)
        mm = m_result.group(2)
        dd = m_result.group(3)

        return yy, mm, dd
    else:
        raise ValueError(f'ERROR:  Date string "{date_str}" not in the format "yyyy-mm-dd"')


def print_errors(errors):
    if 0 == len(errors.keys()):
        return

    if not all(errors[key]['count'] == 0 for key in errors.keys()):
        print('')

    for key in errors.keys():
        error = errors[key]
        count = error['count']

        if 0 < count:
            print(f'TYPE {key:>4}:  count={count}  <--')
        else:
            print(f'TYPE {key:>4}:  count={count}')


def print_queries(queries, queries_str):
    if 0 == len(queries.keys()):
        return

    print(queries_str)

#   if not all(queries[key]['count'] == 0 for key in queries.keys()):
#       print('')

    for key in sorted(queries.keys()):
        query = queries[key]
        count = query['count']

        print(f'TYPE {key:>8}:  count={count}')


def main():

    #  Print out version info
    print(f'Tlaloc Error Checker:  v{version_num}  ({version_date})')


    #  Get today's year, month, and day
    now = datetime.now().astimezone()

    today_yy = f'{now.year:d}'
    today_mm = f'{now.month:02d}'
    today_dd = f'{now.day:02d}'


    #  Parse command line arguments
    arg_parser = init_argparse()

    args = arg_parser.parse_args()

    if ('beg_date' in args) and (args.beg_date is not None):
        beg_date = args.beg_date
        if 'TODAY' == args.beg_date:
            beg_year, beg_month, beg_day = today_yy, today_mm, today_dd
        else:
            beg_year, beg_month, beg_day = parse_date(args.beg_date)
    else:
        beg_year, beg_month, beg_day = today_yy, today_mm, today_dd

    if ('end_date' in args) and (args.end_date is not None):
        end_date = args.end_date
        if 'TODAY' == args.end_date:
            end_year, end_month, end_day = today_yy, today_mm, today_dd
        else:
            end_year, end_month, end_day = parse_date(args.end_date)
    else:
        end_year, end_month, end_day = today_yy, today_mm, today_dd


    #  Print out span of dates to check
    print('')
    print('')
    print('======')
    print('DATES:')
    print('======')
    print('')
    print(f'Current Date:  year={today_yy}  month={today_mm}  day={today_dd}')
    print(f'    Beg Date:  year={beg_year}  month={beg_month}  day={beg_day}')
    print(f'    End Date:  year={end_year}  month={end_month}  day={end_day}')


    #  Turn date strings into date objects
    beg_date = date(int(beg_year), int(beg_month), int(beg_day))
    end_date = date(int(end_year), int(end_month), int(end_day))


    #  Initialize directory names
    work_dir = Path('.')
    root_dir = Path('.')

    pt1_dir = root_dir / 'logs/tl_pt1/'
    pt2_dir = root_dir / 'logs/tl_pt2/'


    #  Print out directory names
    print('')
    print('')
    print('================')
    print('DIRECTORY NAMES:')
    print('================')
    print('')
    print(f'work_dir = "{work_dir}"')
    print(f'root_dir = "{root_dir}"')
    print(f' pt1_dir = "{pt1_dir}"')
    print(f' pt2_dir = "{pt2_dir}"')


    #  Print out space on file systems
    print('')
    print('')
    print('===========')
    print('FREE SPACE:')
    print('===========')
    print('')

    total, used, free = shutil.disk_usage(work_dir)
    print(f'PWD:   used {used  / (2**30):.2f} GB   free {free / (2**30):.2f} GB')

    total, used, free = shutil.disk_usage(pt1_dir)
    print(f'PT1:   used {used  / (2**30):.2f} GB   free {free / (2**30):.2f} GB')

    total, used, free = shutil.disk_usage(pt2_dir)
    print(f'PT2:   used {used  / (2**30):.2f} GB   free {free / (2**30):.2f} GB')


    print('')
    print('')
    print('============')
    print('QUOTE FILES:')
    print('============')
    print('')

#   year, month, day = beg_year, beg_month, beg_day

    cur_date = beg_date

    #0 = re.compile('^LOG ROTATE:  Opening new log files -- quotes_file=\'quotes_(\d\d\d\d)-(\d\d)-(\d\d)_(\d\d)-(\d\d)-(\d\d).(\d\d\d).txt\'   ticker_file=\'<<TICKERLOGGING OFF>>\'   log_dir=\'/home/pi/logs/tl_pt1\'$')

    #  ENTRY[000623]:  TYPE=QUOTE  TIME=2023-05-30 07:30:00.225290 MDT  QUERY_TYPE=CI_QUOTE  VERSION=2022-10-23a
    mq = re.compile('^ENTRY\[(\d+)\]:  TYPE=QUOTE  TIME=(\d\d\d\d-\d\d-\d\d +\d\d:\d\d:\d\d\.\d+) (?:MST|MDT)  QUERY_TYPE=([A-Z0-9_]+)  VERSION=(\d\d\d\d-\d\d-\d\d[a-z])$')
    #q = re.compile('^ENTRY\[(\d+)\]:')

    while cur_date <= end_date:
        year, month, day = cur_date.year, cur_date.month, cur_date.day
#       print(f'Current Date:  year={year}  month={month}  day={day}  pt1_dir={pt1_dir}  pt2_dir={pt2_dir}')

        #  quotes_2023-05-30_00-00-09.328.txt
        quote_files1 = sorted(pt1_dir.glob(f'quotes_{year:04d}-{month:02d}-{day:02d}_*.txt'))
        quote_files2 = sorted(pt2_dir.glob(f'quotes_{year:04d}-{month:02d}-{day:02d}_*.txt'))


        for quote_file in quote_files1:

            queries = {}
            beg_entry_no = None
            end_entry_no = None

            with open(quote_file, encoding='latin-1') as fp_in:
                for line in fp_in:
                    line = line.strip()

                    mq_result = mq.match(line)
                    if mq_result:
                        entry_no = int(mq_result.group(1))
                        time_stamp = mq_result.group(2)
                        query_type = mq_result.group(3)
                        query_version = mq_result.group(4)

                        if query_type in queries.keys():
                            queries[query_type]['count'] += 1
                        else:
                            queries[query_type] = {
                                'beg_time': time_stamp,
                                'end_time': time_stamp,
                                'count': 1,
                            }

                        if beg_entry_no is None:
                            beg_entry_no = entry_no
                        elif beg_entry_no > entry_no:
                            beg_entry_no = entry_no
        
                        if end_entry_no is None:
                            end_entry_no = entry_no
                        elif end_entry_no < entry_no:
                            end_entry_no = entry_no

#                       print(f'line="{line}"  entry_no={entry_no}  query_type={query_type}')

            str_list = []
            for key in sorted(queries.keys()):
                str_list.append(f'{key}:  {queries[key]["count"]}')

            file_size = quote_file.stat().st_size

            if beg_entry_no is None:
                beg_entry_no = -1

            if end_entry_no is None:
                end_entry_no = -1

            if 0 < len(str_list):
                str_list = ", ".join(str_list)
            else:
                str_list = "<< NO ENTRIES >>"

            print(f'PT1:  {str(quote_file)}: {file_size:10d}  ({file_size / (2**30):.3f} GB)    Entries:  {beg_entry_no:06d}:{end_entry_no:06d}   Queries:  {str_list}')
            

        for quote_file in quote_files2:

            queries = {}
            beg_entry_no = None
            end_entry_no = None

            with open(quote_file, encoding='latin-1') as fp_in:
                for line in fp_in:
                    line = line.strip()

                    mq_result = mq.match(line)
                    if mq_result:
                        entry_no = int(mq_result.group(1))
                        time_stamp = mq_result.group(2)
                        query_type = mq_result.group(3)
                        query_version = mq_result.group(4)

                        if query_type in queries.keys():
                            queries[query_type]['count'] += 1
                        else:
                            queries[query_type] = {
                                'beg_time': time_stamp,
                                'end_time': time_stamp,
                                'count': 1,
                            }

                        if beg_entry_no is None:
                            beg_entry_no = entry_no
                        elif beg_entry_no > entry_no:
                            beg_entry_no = entry_no
        
                        if end_entry_no is None:
                            end_entry_no = entry_no
                        elif end_entry_no < entry_no:
                            end_entry_no = entry_no

#                       print(f'line="{line}"  entry_no={entry_no}  query_type={query_type}')

            str_list = []
            for key in sorted(queries.keys()):
                str_list.append(f'{key}:  {queries[key]["count"]}')

            file_size = quote_file.stat().st_size

            if beg_entry_no is None:
                beg_entry_no = -1

            if end_entry_no is None:
                end_entry_no = -1

            if 0 < len(str_list):
                str_list = ", ".join(str_list)
            else:
                str_list = "<< NO ENTRIES >>"

            print(f'PT2:  {str(quote_file)}: {file_size:10d}  ({file_size / (2**30):.3f} GB)    Entries:  {beg_entry_no:06d}:{end_entry_no:06d}   Queries:  {str_list}')


        if (0 < len(quote_files1)) or (0 < len(quote_files2)):
            print('')

        #icker1 = sorted(pt1_dir.glob(f'ticker_{year}-{month}-{day}_*.txt'))
        #icker2 = sorted(pt2_dir.glob(f'ticker_{year}-{month}-{day}_*.txt'))

        #rint(f'ticker1={ticker1}')
        #rint(f'ticker2={ticker2}')

        cur_date = cur_date + timedelta(days = 1)


    #  LOG ROTATE:  Next rotate at 2023-05-31 00:00:09.328  (86400 seconds)
    #  LOG ROTATE:  Opening new log files -- quotes_file='quotes_2023-05-27_11-30-43.159.txt'   ticker_file='<<TICKERLOGGING OFF>>'   log_dir='/home/pi/logs/tl_pt1'

    #0 = re.compile('^LOG ROTATE:  Opening new log files -- quotes_file=\'quotes_2023-05-19_00-00-09.873.txt\'   ticker_file=\'<<TICKERLOGGING OFF>>\'   log_dir=\'/home/pi/logs/tl_pt1\'$')
    #0 = re.compile('^LOG ROTATE:  Opening new log files -- quotes_file=\'quotes_(\d\d\d\d)-(\d\d)-(\d\d)_00-00-09.873.txt\'   ticker_file=\'<<TICKERLOGGING OFF>>\'   log_dir=\'/home/pi/logs/tl_pt1\'$')
    m0 = re.compile('^LOG ROTATE:  Opening new log files -- quotes_file=\'quotes_(\d\d\d\d)-(\d\d)-(\d\d)_(\d\d)-(\d\d)-(\d\d).(\d\d\d).txt\'   ticker_file=\'<<TICKERLOGGING OFF>>\'   log_dir=\'/home/pi/logs/tl_pt1\'$')

    #  DBG(IEX_Intraday, 2023-05-26 11:12:15.911431 MDT):  query='https://cloud.iexapis.com/stable/stock/market/batch?types=book&symbols=MSFT,MRO,MMM,MCD,MAR,LUV,KR,KO,JPM,JNJ,INTC,HIMX,HD,GOOG,FSLY,FDX,META,EXC,ET,ERJ,EADSY,DIS,DASH,CVX,CSX,CSCO,CP,COST,COP,CNI&range=5y&token=REMOVED'
    m1 = re.compile('^DBG\((.+), (\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\.\d+ (?:MST|MDT)\): +query=\'(.+)\'')

    #  ERROR (#1) FETCHING URL 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=ATSG&interval=1min&outputsize=full&apikey=REMOVED'
    m2 = re.compile('^ERROR \(#(\d)\) FETCHING URL \'(.*)\'$')

    #  ERROR FAILED TO FETCH URL 'https://cloud.iexapis.com/stable/stock/market/batch?types=book&symbols=NVDA,TSM,ASML,XOM,WMT,WM,WFC,VOO,VMW,VDE,V,UNP,U,TSLA,TAP,T,SLB,SFTBY,SBUX,PNW,PLTR,PG,PEP,PEG,OXY,OPEN,NKE,NIO,NFLX,NET&range=5y&token=REMOVED'
    m3 = re.compile('^ERROR FAILED TO FETCH URL \'(.*)\'$')

    #  UNHANDLED ERROR:  ERROR(TypeError exception in 'init_threads_done()'):  'builtin_function_or_method' object is not iterable
    m4 = re.compile('UNHANDLED ERROR:  ERROR\(TypeError exception in \'init_threads_done\(\)\'\):  \'builtin_function_or_method\' object is not iterable')
    m4 = re.compile('UNHANDLED ERROR:  ERROR(TypeError exception in \'init_threads_done()\'):  \'builtin_function_or_method\' object is not iterable')
    m4 = re.compile('UNHANDLED ERROR:  ERROR')
    m4 = re.compile('ERROR\(TypeError exception in \'init_threads_done\(\)\'\):  \'builtin_function_or_method\' object is not iterable')

    mY = re.compile('.*WARNING.*')
    mZ = re.compile('.*ERROR.*')


#   year, month, day = beg_year, beg_month, beg_day
#   print(f'Current Date:  year={year}  month={month}  day={day}')

    logs = sorted(work_dir.glob('tlLog_*.txt'))

    for log in logs:
        print('')
        print('=' * len(str(log)))
        print(log)
        print('=' * len(str(log)))


        with open(log, encoding='latin-1') as fp_in:
            state = 0
            errors = {}
            queries = {}
            queries_str = ''
            log_date = None

            line_no = 0

            for line in fp_in:
                line_no += 1
                line = line.strip()

                m0_result = m0.match(line)

                if m0_result:

                    if 1 == state:
                        print_errors(errors)
                        print_queries(queries, queries_str)

                    '''
                    log_timestamp = log_date.strftime('%Y-%m-%d %H:%M:%S.%f %Z')
                    beg_timestamp = beg_date.strftime('%Y-%m-%d %H:%M:%S.%f %Z')
                    end_timestamp = end_date.strftime('%Y-%m-%d %H:%M:%S.%f %Z')

                    print(f'beg_timestamp={beg_timestamp}  log_timestamp={log_timestamp}  end_timestamp={end_timestamp}')
                    '''


                    l_year  = m0_result.group(1)
                    l_month = m0_result.group(2)
                    l_day   = m0_result.group(3)
                    l_hour  = m0_result.group(4)
                    l_min   = m0_result.group(5)
                    l_sec   = m0_result.group(6)

#                   print(f'MATCH m0  {l_year}  {l_month}  {l_day}  {l_hour}  {l_min}  {l_sec}')
#                   print(f'yy:  {l_year}, {year}  mm:  {l_month}, {month}  dd:  {l_day}, {day}')


                    log_date = date(int(l_year), int(l_month), int(l_day))

                    if (beg_date <= log_date) and (log_date <= end_date):
                        log_timestamp = log_date.strftime('%Y-%m-%d')

                        print('')
                        print(f'----------{"-" * len(log_timestamp)}-')
                        print(f'ERRORS ON {log_timestamp}:')
                        print(f'----------{"-" * len(log_timestamp)}-')
                        print('')

                        queries_str = ''
                        queries_str += ('\n')
                        queries_str += (f'-----------{"-" * len(log_timestamp)}-\n')
                        queries_str += (f'QUERIES ON {log_timestamp}:\n')
                        queries_str += (f'-----------{"-" * len(log_timestamp)}-\n')
#                       queries_str += ('\n')

                        queries = {}

                        state = 1

                        errors = {
                            '#1': {'count': 0},
                            '#2': {'count': 0},
                            '#3': {'count': 0},
                            '#4': {'count': 0},
                            'FAIL': {'count': 0},
                            'ITER': {'count': 0},
                            'UNKN': {'count': 0},
                            'WARN': {'count': 0},
                        }

                    else:
                        state = 0

                        errors = {}


                if 1 == state:

                    m1_result = m1.match(line)
                    m2_result = m2.match(line)
                    m3_result = m3.match(line)
                    m4_result = m4.match(line)
                    mY_result = mY.match(line)
                    mZ_result = mZ.match(line)

                    if m1_result:
                        q_src = m1_result.group(1)

                        q_year = m1_result.group(2)
                        q_month = m1_result.group(3)
                        q_day = m1_result.group(4)

                        q_hour = m1_result.group(5)
                        q_min = m1_result.group(6)
                        q_sec = m1_result.group(7)

                        q_url = m1_result.group(8)

                        query_type = id_quote(q_url)

#                       if None is query_type:
#                           print(f'UNKNOWN SRC  url={q_url}')
#                       else:
#                           print(f'SRC="{query_type}"')

                        if query_type in queries.keys():
                            queries[query_type]['count'] += 1
                        else:
                            queries[query_type] = {
                                'beg_time': time_stamp,
                                'end_time': time_stamp,
                                'count': 1,
                            }

#                       print(f'DBG:  {q_src}  {q_year}-{q_month}-{q_day}  {q_hour}:{q_min}:{q_sec}  {q_url}')

                        time_stamp = f'{q_year}-{q_month}-{q_day}  {q_hour}:{q_min}:{q_sec}'

                    elif m2_result:
                        error_no = m2_result.group(1)
                        error_url = m2_result.group(2)

                        print(f'{time_stamp}  --  ERROR #{error_no}:  {error_url}')

                        errors[f'#{error_no}']['count'] += 1

                    elif m3_result:
                        fail_url = m3_result.group(1)

                        print(f'{time_stamp}  --  FAILED QUERY:  {fail_url}')

                        errors['FAIL']['count'] += 1

                    elif m4_result:
                        errors['ITER']['count'] += 1

                    elif mZ_result:
                        print(f'{time_stamp}  --  UNHANDLED ERROR:  {line}')

                        errors['UNKN']['count'] += 1

                    elif mY_result:
                        print(f'{time_stamp}  --  UNHANDLED WARNING:  {line}')

                        errors['WARN']['count'] += 1

        if 1 == state:
            print_errors(errors)
            print_queries(queries, queries_str)


if __name__ == '__main__':
    main()
