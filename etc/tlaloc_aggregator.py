#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""tlaloc_aggregator.py:  Aggregates multiple daily Tloloc logs into combined logs.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import argparse
import glob
import hashlib
import re

#  Combine multiple quote and ticker logs into combined logs ordered chronologically
#  with redundant entries removed


def print_hi(name):
    print(f'Starting "{name}"')


def write_quote(quotes, key, entry, fp_out):

    if 0 == (entry % 10000):
        print(f'ENTRY {entry}', flush=True)

    symbols = quotes[key]['symbols']
    url     = quotes[key]['url']
    quote   = quotes[key]['quote']

    fp_out.write('\n')
    fp_out.write('ENTRY[%06d]:  TYPE=QUOTE  TIME=%s\n' % (entry, key))
    fp_out.write(symbols + '\n')
    fp_out.write(url + '\n')
    fp_out.write(quote + '\n')

    quotes.pop(key)

    return


def write_ticker(ticker, key, entry, fp_out):

    if 0 == (entry % 10000):
        print(f'ENTRY {entry}', flush=True)

    id   = ticker[key]['id']
    time = ticker[key]['time']
    data = ticker[key]['data']

    #  ENTRY[000001]:  ID=AAPL:CNBC:metadata,fundamentals  TIME=2021-02-09 14:52:46.369
    fp_out.write('\n')
    fp_out.write('ENTRY[%06d]:  ID=%s  TIME=%s\n' %(entry, id, time))
    for datum in data:
        fp_out.write(datum + '\n')

    ticker.pop(key)

    return


def do_combine(suppress_quotes, suppress_ticker, filter_iex, root_dir, proc_dir, yr_mo, pt):

    #  Create names of output files
    suffix = f"{yr_mo}_pt{pt}"

    #   quotes_COMBINED_2024-09_pt1.txt
    file_quotes = f"quotes_COMBINED_{suffix}.txt"
    file_ticker = f"ticker_COMBINED_{suffix}.txt"


    #  Create names of input and output directories
    input_dir  = f'{root_dir}data_raw_{yr_mo}/{proc_dir}{pt}/'
    output_dir = f'{root_dir}combined_{yr_mo}/'


    #  Precompile regular expressions
    m0 = re.compile('^ENTRY\[\d+\]: *TYPE=QUOTE *TIME=.*$')
    m2 = re.compile('^https:\/\/')
    m3 = re.compile('^\{.*\}$')

   #<!doctype html> <html lang="en"> <head> <title>Server Error (500)</title> </head> <body> <h1>Server Error (500)</h1><p></p> </body> </html>
    mSkip01 = re.compile('^<!DOCTYPE html>', re.IGNORECASE)
    mSkip02 = re.compile('^<html>')
    mSkip03 = re.compile('^https://cloud.iexapis.com')
    mSkip04 = re.compile('<!doctype html public "-//W3C//DTD HTML 4.01//EN"')
    mSkip05 = re.compile('^An unknown error occurred')
    mSkip06 = re.compile('<HTML><HEAD> *<TITLE>Access Denied</TITLE>')


    #  Get list of quote files
    if suppress_quotes:
        quoteFileList = []
    else:
        quoteFileList = glob.glob(input_dir + 'quote*.txt')
        quoteFileList.sort()


    #  Initialize for quotes processing
    num_skip = 0
    num_keep = 0

    entry = 0

    flush_fifo = [0, 0, 0]
    flush_ptr0 = 0
    flush_ptr1 = 0

    quotes = {}
    quotes_keys = {}


    #  Process quotes
    if 0 < len(quoteFileList):
        with open(output_dir + file_quotes, "w") as fp_out:

            #  Process input files one at a time
            for quoteFile in quoteFileList:

                #  Skip combined files (based on name)
                if "COMBINED" in quoteFile:
                    continue

                print(quoteFile, flush=True)

                with open(quoteFile) as fp_in:
                    state   = 0
                    line_no = 0

                    #  Process file line by line
                    for line in fp_in:
                        line_no += 1
                        line = line.strip()

                        #  print("Line {}.{}: {}".format(line_no, state, line.strip()), flush=True)


                        #  Handle blank lines
                        if '' == line:
                            if 99 == state:
                                state = 0

                            continue


                        #  Handle non-blank lines
                        if mSkip01.match(line):
                            print(f"SKIP 1:  line='{line[:80]} ...'  (at most first 80 characters)", flush=True)
                            state = 99
                        elif mSkip02.match(line):
                            print(f"SKIP 2:  line='{line[:80]} ...'  (at most first 80 characters)", flush=True)
                            state = 99
                        elif mSkip04.match(line):
                            print(f"SKIP 4:  line='{line[:80]} ...'  (at most first 80 characters)", flush=True)
                            state = 99
                        elif mSkip05.match(line):
                            print(f"SKIP 5:  line='{line[:80]} ...'  (at most first 80 characters)", flush=True)
                            state = 99
                        elif mSkip06.match(line):
                            print(f"SKIP 6:  line='{line[:80]} ...'  (at most first 80 characters)", flush=True)
                            state = 99

                        elif 0 == state:

                            #  Ensure line matches regular expression:  m0 = re.compile('^ENTRY\[\d+\]: *TYPE=QUOTE *TIME=.*$')
                            if not m0.match(line):
                                print(f'ERROR #1:  line="{line}"', flush=True)
                                exit(1)

                            #  Get info and change state
                            key = re.sub('^.*TIME=', '', line)

                            state = 1

                        elif 1 == state:
                            #  Get info and change state
                            symbols = line

                            state = 2

                        elif 2 == state:

                            #  Ensure line matches regular expression:  m2 = re.compile('^https:\/\/')
                            if not m2.match(line):
                                print(f'ERROR #2:  line="{line}"', flush=True)
                                exit(1)

                            #  Get info and change state
                            url = line

                            state = 3

                        elif 3 == state:

                            #  Ensure line matches regular expression:  m3 = re.compile('^\{.*\}$')
                            if not m3.match(line):
                                print(f'ERROR #3:  line="{line}"', flush=True)
                                exit(1)

                            #  Get info
                            quote = line

                            #  Process quote
                            if filter_iex and mSkip03.match(url):
                                num_skip += 1

                                #  print('SKIP 03', flush=True)
                                #  exit(1)

                            else:

                                #  Create hash for this quote
                                hash_sep = ' -=::=- '
                                hash_src = symbols + hash_sep + url + hash_sep + quote
                                hash_val = hashlib.sha224(hash_src.encode('utf8')).hexdigest()

                                #  Handle duplicates and key clashes
                                if key in quotes_keys:
                                    num_skip += 1

                                    if quotes_keys[key] == hash_val:
                                        print(f'DUPLICATE:')

                                        print(f'   key={key}')
                                        print(f'   symbols={symbols}')
                                        print(f'   url={url}')
                                        #rint(f'   quote={quote}')

                                    else:
                                        print(f"KEY CLASH:  {key}", flush=True)
                                        exit(0)

                                #  Good quote, record it
                                else:
                                    num_keep += 1

                                    quotes[key] = {
                                        'symbols': symbols, 'url': url, 'quote': quote,
                                    }

                                    quotes_keys[key] = hash_val

                            #  Change state
                            state = 0

                        else:
                            print(f'ERROR #4:  line="{line}"', flush=True)
                            exit(1)


                    #  Perform partial flush if appropriate
                    flush_ptr1 = flush_fifo.pop(0)

                    flush_fifo.append(num_keep)

                    num_flush = flush_ptr1 - flush_ptr0
                    flush_keys = sorted(quotes.keys())[0:num_flush]

                    for key in flush_keys:
                        write_quote(quotes, key, entry, fp_out)

                        entry = entry + 1

                    flush_ptr0 = flush_ptr1


            #  Flush remaining quotes
            flush_keys = sorted(quotes.keys())

            for key in flush_keys:
                write_quote(quotes, key, entry, fp_out)

                entry = entry + 1

    #  Print summary of what was done
    print(f"QUOTES:  num_skip={num_skip}   num_keep={num_keep}", flush=True)

    quotes = None


    #  Precompile regular expressions
    #  ENTRY[000000]:  ID=AAPL:CNBC:metadata,fundamentals  TIME=2021-04-01 13:30:00.782781 UTC
    #  ENTRY[000000]:  ID=PEG:CNBC_Intraday:metadata,fundamentals,realtime  TIME=2021-06-01 13:33:32.429345 UTC
    m0 = re.compile('^ENTRY\[\d+\]: *ID=([A-Za-z,_:\-\.]+) *TIME=(.*)$')
    m1 = re.compile('^\{.*\}$')


    #  Get list of ticker files
    if suppress_ticker:
        tickerFileList = []
    else:
        tickerFileList = glob.glob(input_dir + 'ticker*.txt')
        tickerFileList.sort()


    #  Initialize for ticker processing
    num_skip = 0
    num_keep = 0

    entry = 0

    flush_fifo = [0, 0, 0]
    flush_ptr0 = 0
    flush_ptr1 = 0

    ticker = {}
    ticker_keys = {}


    #  Process ticker
    if 0 < len(tickerFileList):
        with open(output_dir + file_ticker, "w") as fp_out:

            #  Process input files one at a time
            for tickerFile in tickerFileList:

                #  Skip combined files (based on name)
                if "COMBINED" in tickerFile:
                    continue

                print(tickerFile, flush=True)

                with open(tickerFile) as fp_in:
                    state   = 0
                    line_no = 0

                    #  Process file line by line
                    for line in fp_in:
                        line_no += 1
                        line = line.strip()

                        #  print("Line {}.{}: {}".format(line_no, state, line.strip()), flush=True)


                        #  Handle blank lines
                        if '' == line:
                            continue


                        #  Handle non-blank lines
                        if 0 == state:

                            #  Ensure line matches regular expression:  m0 = re.compile('^ENTRY\[\d+\]: *ID=([A-Za-z,_:\-\.]+) *TIME=(.*)$')
                            if not m0.match(line):
                                print(f'ERROR #11:  line="{line}"', flush=True)
                                exit(1)

                            m = m0.match(line)
                            symbol, src, types = m.group(1).split(':')

                            types = types.split(',')

                            key = m.group(2) + ' ' + symbol

                            #  print(f"key='{key}'  symbol='{symbol}'  src='{src}'  types='(%s)'" % "^".join(types))

                            types.reverse()


                            ticker_id   = m.group(1)
                            ticker_time = m.group(2)
                            ticker_data = []

                            state = 1

                        elif 1 == state:

                            #  Ensure line matches regular expression:  m1 = re.compile('^\{.*\}$')
                            if not m1.match(line):
                                print(f'ERROR #12:  line="{line}"', flush=True)
                                exit(1)

                            #  Get info and change state
                            ticker_data.append(line)

                            types.pop()

                            if 0 == len(types):

                                #  Create hash for this ticker
                                hash_sep = ' -=::=- '
                                hash_src = ticker_id + hash_sep + ticker_time

                                for datum in ticker_data:
                                    hash_src = hash_src + hash_sep + datum

                                hash_val = hashlib.sha224(hash_src.encode('utf8')).hexdigest()

                                #  Handle duplicates and key clashes
                                if key in ticker_keys:
                                    num_skip += 1

                                    if ticker_keys[key] == hash_val:
                                        print(f'DUPLICATE:')

                                        print(f'   key={key}')
                                        print(f'   id={ticker_id}')
                                        print(f'   time={ticker_time}')

                                    else:
                                        print(f"KEY CLASH:  {key}", flush=True)
                                        exit(0)

                                #  Good ticker, record it
                                else:
                                    num_keep += 1

                                    ticker[key] = {
                                        'id': ticker_id, 'time': ticker_time, 'data': ticker_data,
                                    }

                                    ticker_keys[key] = hash_val

                                #  Change state
                                state = 0

                        else:
                            print(f'ERROR #14:  line="{line}"', flush=True)
                            exit(1)


                    #  Perform partial flush if appropriate
                    flush_ptr1 = flush_fifo.pop(0)

                    flush_fifo.append(num_keep)

                    num_flush = flush_ptr1 - flush_ptr0
                    flush_keys = sorted(ticker.keys())[0:num_flush]

                    for key in flush_keys:
                        write_ticker(ticker, key, entry, fp_out)

                        entry = entry + 1

                    flush_ptr0 = flush_ptr1


            #  Flush remaining ticker
            flush_keys = sorted(ticker.keys())

            for key in flush_keys:
                write_ticker(ticker, key, entry, fp_out)

                entry = entry + 1

    print(f"TICKER:  num_skip={num_skip}   num_keep={num_keep}", flush=True)

    ticker = None


if __name__ == '__main__':

    print_hi('tlaloc_aggregator v0.1')

    #  print('TODO:  Enforce monotonically increasing keys', flush=True)


    #  Process command line arguments
    parser = argparse.ArgumentParser()


    parser.add_argument(
        "-r", "--root_dir",
        dest="root_dir",
        default=".",
        help="Name of root directory")

    parser.add_argument(
        "-p", "--proc_dir",
        dest="proc_dir",
        default="tl_pt",
        help="Name of process root sub-directory")

    parser.add_argument(
        "-d", "--yr_mo",
        dest="yr_mo",
        default="",
        required=True,
        help="Year and month in the form 'yyyy-mm'")

    parser.add_argument(
        "-Q", "--no_quotes",
        dest="suppress_quotes",
        default=False,
        help="Do not process quote files")

    parser.add_argument(
        "-T", "--no_ticker",
        dest="suppress_ticker",
        default=False,
        help="Do not process ticker files")

    parser.add_argument(
        "-I", "--filter_iex",
        dest="filter_iex",
        default=False,
        help="Filter out IEX responses")


    args = parser.parse_args()


    #  Initialize variables based on command line arguments
    root_dir = args.root_dir
    proc_dir = args.proc_dir

    yr_mo = args.yr_mo

    suppress_quotes = args.suppress_quotes
    suppress_ticker = args.suppress_ticker

    filter_iex = args.filter_iex


    print(f"")
    print(f"")
    print(f"Runtime Parameters")
    print(f"               root_dir = {root_dir}")
    print(f"               proc_dir = {proc_dir}")
    print(f"                  yr_mo = {yr_mo}")
    print(f"              no_quotes = {suppress_quotes}")
    print(f"              no_ticker = {suppress_ticker}")
    print(f"             filter_iex = {filter_iex}")


    do_combine(suppress_quotes, suppress_ticker, filter_iex, root_dir, proc_dir, yr_mo, 1)
    do_combine(suppress_quotes, suppress_ticker, filter_iex, root_dir, proc_dir, yr_mo, 2)
