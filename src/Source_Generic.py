# -*- coding: utf-8 -*-

"""Source_Generic_DailySummary.py:  Implements functionality common to all
   data source classes.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

import json
import re
#mport pprint


# BEG Source_Generic.py SPECIFIC
from utils  import mkt_open_on_date

from datetime import datetime
from datetime import timedelta
from datetime import date

from dateutil import tz

import urllib.request, urllib.error
import http

import logging

import threading

import random

import inspect

import math

import time

import os

try:
    import requests
    use_requests = True
except ImportError as error:
    print("IMPORT ERROR:  requests")
    use_requests = False

try:
    from twisted.internet import reactor
except ImportError as error:
    print("IMPORT ERROR:  (twisted.internet) reactor")
# END Source_Generic.py SPECIFIC


class Source_Generic(object):


    def __init__(self):
        print('Inside Source_Generic::__init__()')

        #  Configure execution parameters
        self.configure_lvl0()   #  Default base class configs
        self.configure_lvl1()   #  Override base class configs
#       self.configure_lvl2()   #  Default specific class configs
#       self.configure_lvl3()   #  Override specific class override

        self.internal_lock = threading.Lock()


    def dump_src_attributes(self, level):

        print('\n');
        print(f'BEG Dump of attributes for source "{self.src_name}"  (level #{level})')

        # getmembers() returns all the members of an object
        for i in inspect.getmembers(self):

            # to remove private and protected functions
            if not i[0].startswith('_'):

                # To remove other methods that doesnot start with a underscore
                if not inspect.ismethod(i[1]):
                    print(i)

        print(f'END Dump of attributes for source "{self.src_name}"  (level #{level})')
        print('\n')


    def populate_stock_list(self, stock_list):
        self.stock_list = []
        self.backoff = {}
        self.time_of_last_query = {}

        yesterday = datetime.now() - timedelta(days = 1)

        if not hasattr(self, 'query_type_list'):
            query_types = []
        else:
            #  Get a list of all unique query types from the list of lists
            query_types = list(dict.fromkeys( [item for sublist in self.query_type_list for item in sublist] ))

        for stock in stock_list:
            if stock in self.skip_list:
                print(self.src_name + ":  NOT ADDING '" + stock + "' TO QUERY LIST")
            else:
                self.stock_list.append(stock)

                self.backoff [stock] = {}

                self.backoff [stock]['minor_reset'] = 1   #  TODO:  MAKE THESE TAILORABLE
                self.backoff [stock]['major_reset'] = 2

                self.backoff [stock]['minor_cnt'] = self.backoff [stock]['minor_reset']
                self.backoff [stock]['major_cnt'] = self.backoff [stock]['major_reset']

                if 0 == len(query_types):
                    self.time_of_last_query[stock] = yesterday
                else:
                    self.time_of_last_query[stock] = {}

                    for query_type in query_types:
                        self.time_of_last_query[stock][query_type] = yesterday


    def make_query_requests(self, batch_list, query, query_sanitized, ):

        #  Make three attempts to fetch the contents pointed to by the URL
        if self.to_backoff is None:
            to_backoff = 3.0 / 2.0
        else:
            to_backoff = self.to_backoff

        if self.timeout is None:
            timeout = 3.5 / to_backoff
        else:
            timeout = self.timeout / to_backoff

        for attempt in [1, 2, 3, 4]:
            timeout = timeout * to_backoff
            try:
                if 0 == len(config.runtime_params['ca_cert']):
                    response = requests.get(query, headers=self.hdr, timeout=timeout)
                else:
                    response = requests.get(query, headers=self.hdr, timeout=timeout, proxies=config.runtime_params['proxies'], verify=config.runtime_params['ca_cert'])
                query_raw = response.text

                if response.text:

                    #  Remove whitespace from beginning and end of line
                    resp_text = response.text.strip()

                    #   01234567890123456789
                    if '<!DOCTYPE html>' == resp_text[:15]:
                        time.sleep(2*(attempt-1))

                    #     01234567890123456789
                    elif '<html>' == resp_text[:6]:
                        time.sleep(2*(attempt-1))

                    #  Handle the no content case
                    elif (0 == len(resp_text)) or ('{}' == resp_text):
                        time.sleep(2*(attempt-1))

                    else:

                        #  Turn off throttling of queries due to error conditions
                        self.reset_backoff([entry['loc_symbol'] for entry in batch_list])

                        #  Make successful return
                        return resp_text, False

                    print("ERROR (#" + str(attempt) + ") FETCHING URL '" + query_sanitized + "'")
                    print(f"    INVALID RESPONSE:  response begins with '{response.text[:80]} ...'  (up to first 80 characters)")

                else:

                    print("ERROR (#" + str(attempt) + ") FETCHING URL '" + query_sanitized + "'")
                    print(f"    RESPONSE IS NOT / HAS NO TEXT")


            except Exception as e:
                print("ERROR (#" + str(attempt) + ") FETCHING URL '" + query_sanitized + "'")
                print(f"    EXCEPTION MESSAGE:  {str(e)}")
                # e.read().decode("utf8", 'ignore')

                time.sleep(2*(attempt-1))


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


    #  The following uses urllib.  The requests package may be better:  https://docs.python-requests.org/en/master/
    def make_query_urllib(self, batch_list, query, query_sanitized, ):

        url_fetch_failed = False

        query_raw = ""

        try:
            with urllib.request.urlopen(urllib.request.Request(query, data=None, headers=self.hdr)) as response:

                #  Read response, allow up to 'num_ic_retry' partial reads
                num_ic_retry = 10

                while True:
                    try:
                        query_raw_part = response.read ()

                    #  Handle incompete read
                    except http.client.IncompleteRead as ic_read:

                        query_raw = query_raw + ic_read.partial.decode ('utf-8')

                        if 0 < num_ic_retry:
                            print("WARNING INCOMPLETE FETCH OF URL '" + query_sanitized + "'")

                            num_ic_retry -= 1
                            continue
                        else:
                            print("ERROR FAILED TO COMPLETE FETCH OF URL '" + query_sanitized + "'")

                            query_raw = ""

                            url_fetch_failed = True

                    #  Handle completed read
                    else:
                        query_raw = query_raw + query_raw_part.decode ('utf-8')

                        #  Turn off throttling of queries due to error conditions
                        self.reset_backoff([entry['loc_symbol'] for entry in batch_list])

                    break

        except urllib.error.URLError as e:
            print("ERROR FETCHING URL '" + query_sanitized + "'")
            print(f"    EXCEPTION MESSAGE:  {str(e)}")
            # e.read().decode("utf8", 'ignore')

            for item in batch_list:    #  TODO:  PROVIDE ABILITY TO SUPPRESS BACK-OFF
                stock = item['loc_symbol']

                self.backoff [stock]['major_cnt'] -= 1

                if 0 >= self.backoff [stock]['major_cnt']:
                    self.backoff [stock]['minor_reset'] *= 2   #  TODO:  PROVIDE ABILITY TO IMPOSE MAX BACK-OFF

                    self.backoff [stock]['major_cnt'] = self.backoff [stock]['major_reset']

                    print(self.src_name + ":  ADJUSTING BACK-OFF '" + stock + "' new back-off:  %d" %
                        (self.backoff [stock]['minor_reset']))

                self.backoff [stock]['minor_cnt'] = self.backoff [stock]['minor_reset']

            url_fetch_failed = True


        #  If the fetch failed, return None as the query result
        if url_fetch_failed:
            query_raw = None


        #  Return
        return query_raw, url_fetch_failed


    #  SUBCLASS OVERRIDE

    def is_work_day(self, day):

        #  Only check for weekends and holidays on production runs
        if not config.runtime_params['production']:
            return True

        return mkt_open_on_date(day)


    #  SUBCLASS OVERRIDE

    def review_query_list(self, list_in, query_type, num_query_types, time_hack):
        return list_in


    def reset_backoff(self, backoff_list):

        for stock in backoff_list:
            self.backoff [stock]['minor_reset'] = 1   #   TODO:  MAKE THESE TAILORABLE
            self.backoff [stock]['major_reset'] = 2

            self.backoff [stock]['minor_cnt'] = self.backoff [stock]['minor_reset']
            self.backoff [stock]['major_cnt'] = self.backoff [stock]['major_reset']


    def init_threads_done(self, thread_timestamp, num_threads):

        with self.internal_lock:

            #  Ensure that thread_done is present
            if not hasattr(self, 'thread_done'):
                self.thread_done = {}

            #  Check if thread_done already has an entry to record running state
            if thread_timestamp in self.thread_done:
                print(f"WARNING (init_threads_done()) RE-INITIALIZING TIMESTAMP '{thread_timestamp}'")

            #  Remove stale entries
            try:
                while 2 < len(self.thread_done):
                    stale_timestamp = sorted(self.thread_done.keys())[0]

                    #  Remove timestamp
                    self.thread_done.pop(stale_timestamp, None)

                    print(f"WARNING (init_threads_done()) FORCING EXPIRATION OF STALE TIMESTAMP '{stale_timestamp}'")
            except TypeError as e:
                print(f"ERROR(TypeError exception in 'init_threads_done()'):  {str(e)}")


            #  Initialize new array for this batch of threads
            self.thread_done[thread_timestamp] = [None] * num_threads

        return False


    def expire_threads_done(self, thread_timestamp):

        with self.internal_lock:

            #  Ensure the thread_done has an entry to record running state
            if thread_timestamp not in self.thread_done:
                print(f"WARNING (expire_threads_done()) ATTEMPT TO EXPIRE MISSING TIMESTAMP '{thread_timestamp}'")
                return True

            #  Remove timestamp
            self.thread_done.pop(thread_timestamp, None)

        return False


    def mark_thread_running(self, thread_timestamp, thread_num):

        with self.internal_lock:

            #  Ensure the thread_done has an entry to record running state
            if thread_timestamp not in self.thread_done:
                print(f"WARNING (mark_thread_running()) ATTEMPT TO UPDATE MISSING TIMESTAMP '{thread_timestamp}'")
                return True

            if thread_num < 0 or thread_num >= len(self.thread_done[thread_timestamp]):
                print(f"WARNING (mark_thread_running()) INVALID TRHEAD NUMBER '{thread_num}'.  SHOULD BE IN RANGE [0,{len(self.thread_done[thread_timestamp])}]")
                return True

            #  Mark this thread as running
            self.thread_done[thread_timestamp][thread_num] = False

        return False


    def mark_thread_done(self, thread_timestamp, thread_num):

        with self.internal_lock:

            #  Ensure the thread_done has an entry to record running state
            if thread_timestamp not in self.thread_done:
                print(f"WARNING (mark_thread_done()) ATTEMPT TO UPDATE MISSING TIMESTAMP '{thread_timestamp}'")
                return True

            if thread_num < 0 or thread_num >= len(self.thread_done[thread_timestamp]):
                print(f"WARNING (mark_thread_done()) INVALID TRHEAD NUMBER '{thread_num}'.  SHOULD BE IN RANGE [0,{len(self.thread_done[thread_timestamp])}]")
                return True

            #  Mark this thread as done
            self.thread_done[thread_timestamp][thread_num] = True

        return False


    def all_threads_done(self, thread_timestamp):

        with self.internal_lock:

            #  Ensure the thread_done has an entry to record state
            if thread_timestamp not in self.thread_done:
                print(f"WARNING (all_threads_done()) ATTEMPT ACCESS MISSING TIMESTAMP '{thread_timestamp}'")
                return True

            #  Return whether all threads are done
            return all(self.thread_done[thread_timestamp])


    def threads_done_status(self, thread_timestamp):

        with self.internal_lock:

            #  Ensure the thread_done has an entry to record state
            if thread_timestamp not in self.thread_done:
                print(f"WARNING (threads_done_status()) ATTEMPT ACCESS MISSING TIMESTAMP '{thread_timestamp}'")

                return f"ERROR:  Bad thread timestamp '{thread_timestamp}'"


            #  Return string with state of threads
            return str(self.thread_done[thread_timestamp])


    def make_query(self, thread_timestamp, thread_num, query_type_src, batch_list, ):

        #  Create timestamps
        now_utc = datetime.now(tz.tzlocal())
        now_local = now_utc.astimezone(tz.tzlocal())

        log_timestamp = now_utc.strftime('%Y-%m-%d %H:%M:%S.%f %Z')
        dbg_timestamp = now_local.strftime('%Y-%m-%d %H:%M:%S.%f %Z')


        #  Create query URL
        query, query_sanitized, query_type_loc = self.make_query_url(batch_list)


        #  Debug query
        if config.runtime_params['debug_options']['query']:
            print("DBG(" + self.src_name + ", " + dbg_timestamp + "):  query='" + query_sanitized + "'", flush=True)

        if not config.runtime_params['dry_run']:
            if self.make_query_custom is not None:
                query_raw, url_fetch_failed = self.make_query_custom(batch_list,  query, query_sanitized, )
            elif use_requests:
                query_raw, url_fetch_failed = self.make_query_requests(batch_list,  query, query_sanitized, )
            else:
                query_raw, url_fetch_failed = self.make_query_urllib(batch_list,  query, query_sanitized, )

            #  If the fetch failed, indicate thread is done and return
            if url_fetch_failed:
                self.mark_thread_done(thread_timestamp, thread_num)

                return
        else:
            with open(self.dry_run_file, 'r') as file:
                query_raw = file.read().replace('\n', '')


        #  Normalize response (e.g. removing line breaks)
        query_raw = self.normalize_query(query_raw)


        #  Debug raw response
        if config.runtime_params['debug_options']['query_raw']:
            print("DBG:  query_raw='" + query_raw + "'")


        #  Log response
#       batch_str = '|'.join([batch_list[item]['qry_symbol'] for item in batch_list.keys()])
        batch_str = '|'.join(item['qry_symbol'] for item in batch_list)


        query_msg_head = "\n" + \
                         "\n" + \
                         "ENTRY[%s]:  TYPE=QUOTE  TIME=%s  QUERY_TYPE=%s  VERSION=%s\n" % ('%06d', log_timestamp, query_type_loc, self.version)
        query_msg_body = batch_str       + "\n" + \
                         query_sanitized + "\n" + \
                         query_raw       + "\n"

        with config.log_q_lock:

            #  Write sequence number into the message string
            query_msg_head = query_msg_head % (config.qu_entry_idx)
            config.qu_entry_idx += 1

            #  Combine the three parts of query message together
            query_msg = query_msg_head + query_msg_body

            # Send response through pipe to the processing side
            config.sp_queue.put(query_msg)

            # Log quote
            if config.log_quotes is not None:
                config.log_quotes.write(query_msg)


        #  Indicate thread is done
        self.mark_thread_done(thread_timestamp, thread_num)


    def process_query(self, batch_str, query_raw, query, log_timestamp, query_type, version):

        #  Convert response to dictionary
        query_json = self.response_to_dictionary(query_raw)


        #  Debug formatted responses
        query_pretty = json.dumps(query_json, indent=4, sort_keys=True)
        query_ugly   = json.dumps(query_json, separators=(',', ':'))

        if config.runtime_params['debug_options']['query_ugly']:
            print("DBG:  query_ugly='" + query_ugly + "'")

        if config.runtime_params['debug_options']['query_pretty']:
            print("DBG:  query_pretty=\n" + query_pretty)


        try:
            #  Create batch list
            batch_list = self.make_batch_list_pt2(batch_str.split('|'))


            #  Ensure there is an entry for every stock
#  TODO     if self.symbol_rollcall(batch_list, query_json, query):
#  TODO         continue


            #  Process response for each stock
            for item in batch_list:
                qry_symbol = item['qry_symbol']
                loc_symbol = item['loc_symbol']


                #  Select the JSON (sub)structure that should correspond to this stock
                query_stock = self.get_query_stock(qry_symbol, query_json)

                if None is query_stock:
                    print(query_stock)
                    print("ERROR:  No response for stock '%s'.  SKIPPING STOCK WHILE PROCESSING URL '%s'" %
                        (qry_symbol, query))
                    continue


                #  Extract info of interest about this stock
                self.parse_query_response(query_stock, loc_symbol, log_timestamp, query_type, version)

        except:
            print ("ERROR(Source_Generic::process_query()):  Failed to process query response.")
            print ("    ... error continued:  log_timestamp='%s'  batch_str='%s'  query='%s'" % (log_timestamp, batch_str, query))
            print ("    ... error continued:  query_ugly='" + query_ugly + "'")


    #  This method (a) creates list of stocks in query, (b) executes query, and (c) schedules next batch if not all stocks have been processed
    def query_driver_pt1(self):

        #  Init variables for query
        thread_timestamp = time.time_ns()

        thread_num = 0
        num_threads = min(-(len(self.stock_list_cur) // -self.max_batch), self.max_threads)

        self.init_threads_done(thread_timestamp, num_threads)


        #  Batch up symbols in list and create a query for each batch
        while (0 < len(self.stock_list_cur)) and (thread_num < self.max_threads):


            #  Create list of stocks in this query
            batch_list = []

            size_query = min(self.max_batch, len(self.stock_list_cur))


            #  Process batch size number of symbols
            batch_list = self.make_batch_list_pt1(self.stock_list_cur[0:size_query])

            self.stock_list_cur = self.stock_list_cur[size_query:]


            #  Debug spawning threads
            if config.runtime_params['debug_options']['threads']:
                logging.info(self.src_name + "::query_driver_pt1():  create and start thread %d.", thread_num)


            #  Spawn thread to make query (one per batch)
            self.mark_thread_running(thread_timestamp, thread_num)

            thrd = threading.Thread(target=self.make_query, args=(thread_timestamp, thread_num, self.query_type_src, batch_list))
            thrd.start()
            thread_num += 1


        #  Schedule thread cleanup routine
        if (0 < thread_num):
            reactor.callLater(self.poll_sleep_time, self.query_driver_pt2, thread_timestamp)


    #  This method (a) checks on whether threads are still running, (b) schedule next poll if one or more threads are still running.
    def query_driver_pt2(self, thread_timestamp):

        #  Report on state of threads if debugging
        if config.runtime_params['debug_options']['threads']:
            logging.info(self.src_name + "::query_driver_pt2():  is done=%s" % (self.threads_done_status(thread_timestamp)))


        #  Schedule another poll if not all threads are done
        if (not self.all_threads_done(thread_timestamp)):
            reactor.callLater(self.poll_sleep_time, self.query_driver_pt2, thread_timestamp)
            return


        #  Remove thread_timestamp list from self.thread_done
        self.expire_threads_done(thread_timestamp)


        #  Busy wait while pause_file is present
        while os.path.isfile(self.pause_file):
            print(f"QUERY DRIVER PT2({self.src_name}):  Found file '{str(self.pause_file)}'.  Pausing activity while file is present.", flush=True)

            time.sleep (self.pause_sleep)


        #  Schedule next iteration if there are still stocks to process
        if 0 < len (self.stock_list_cur):
            reactor.callLater(self.batch_sleep_time, self.query_driver_pt1)


        #  Since this batch is done, flush the quotes file handle
        if config.log_quotes is not None:
            with config.log_q_lock:
                config.log_quotes.flush()


    #  This method (a) schedules next query, (b) determines if market is open, and (c) initiates query if market is open
    def run_recurring_query(self):


        print(self.src_name + "::run_recurring_query():  " + datetime.now(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S.%f %Z'))


        #  Is pause file present
        if not hasattr(self, 'pause_file'):
            self.pause_file = os.path.join(str(config.runtime_params['cur_dir']), 'pause.txt')

        if not self.pause:
            if os.path.isfile(self.pause_file):
                print(f"RUN RECURRING QUERY({self.src_name}):  Found file '{str(self.pause_file)}'.  Pausing activity while file is present.", flush=True)

                self.pause = True
        else:
            if not os.path.isfile(self.pause_file):
                print(f"RUN RECURRING QUERY({self.src_name}):  File '{str(self.pause_file)}' not found.  Resuming activity.", flush=True)

                self.pause = False


        #  Determine status with respect to time window
        mkt_open, next_query = self.timeWindowCheck(self.mkt_time_zone, self.mkt_beg_time, self.mkt_end_time)

        #  NOTE:  At this point next_query is the next WALL CLOCK time of self.mkt_beg_time.  (Does not account for days market is closed.)


        #  Override wait time if market is currently open
        if mkt_open:

            #  Get datetime object for now
            now = datetime.now(self.mkt_time_zone)

            #  Create/update datetime object for begin and end of today's trading session if needed
            if (self.mkt_beg_today is None) or (now.today() != self.mkt_beg_today.today()):
                hh_beg = int(self.mkt_beg_time / 10000) % 100
                mm_beg = int(self.mkt_beg_time / 100  ) % 100
                ss_beg = int(self.mkt_beg_time        ) % 100

                self.mkt_beg_today = now.replace(hour=hh_beg, minute=mm_beg, second=ss_beg)


                #  Create datetime object for end of today's trading window
                hh_end = int(self.mkt_end_time / 10000) % 100
                mm_end = int(self.mkt_end_time / 100  ) % 100
                ss_end = int(self.mkt_end_time        ) % 100

                beg_sec = ((hh_beg * 60) + mm_beg) * 60 + ss_beg
                end_sec = ((hh_end * 60) + mm_end) * 60 + ss_end
 
                self.mkt_end_today = self.mkt_beg_today + timedelta(seconds=(end_sec - beg_sec))


            #  Schedule a new round of queries for today if there is at least self.delta_quote seconds left in the trading day
            if self.delta_quote <= (self.mkt_end_today - now).total_seconds():

                num_delta = math.floor((now - self.mkt_beg_today).total_seconds() / self.delta_quote) + 1

                if 0 >= num_delta:
                    num_delta = 1

                next_query = self.mkt_beg_today + timedelta(seconds = (num_delta * self.delta_quote))

        #  NOTE:  If the market is open, at this point next_query is the next time to query the stocks.


        #  If the user requested to skip today, don't make queries until open of market session
        if self.skip_today:
            mkt_open = False

            self.skip_today = False

            #  Determine when the next time window will open
            hh = int(self.mkt_beg_time / 10000) % 100
            mm = int(self.mkt_beg_time / 100  ) % 100
            ss = int(self.mkt_beg_time        ) % 100

            now        = datetime.now(self.mkt_time_zone)
            hhmmss     = int(now.strftime('%H%M%S'))

            next_query = now.replace(hour=hh, minute=mm, second=ss)

            if hhmmss >= self.mkt_beg_time:
                next_query += timedelta(days=1)

        #  NOTE:  If the user has requested to skip today, at this point next_query is the next WALL CLOCK time the market opens.


        #  Override time of next query if in paused state
        if self.pause:
            mkt_open = False

            next_query = datetime.now(self.mkt_time_zone) + timedelta(seconds = self.pause_sleep)

            print (f"PAUSED({self.src_name}).  Checking back in {self.pause_sleep} seconds.")

        #  NOTE:  If the user has put the program in a pause state, at this point next_query is the time of the next poll for exiting the pause state.


        #  Reset back-off if market is closed or we are in paused state
        if (not mkt_open) or self.pause:

            #  Turn off throttling of queries due to error conditions
            self.reset_backoff(self.backoff.keys())


        #  Schedule next query
        wait_time = (next_query - datetime.now(self.mkt_time_zone)).total_seconds()

        reactor.callLater(wait_time, self.run_recurring_query)


        print(self.src_name + ":  Next query at %s  (%d seconds)" % (next_query.strftime('%Y-%m-%d %H:%M:%S.%f %Z'), round (wait_time)))


        #  Initial query
        if config.runtime_params['skip_query']:
            print('ALERT:  Skipping execution of recurring query because "skip_query" option given on command line')

            return


        #  Make query if we are within the active time window
        if mkt_open:

            #  Record list of stocks (in reverse order so we can pop off the end)
            active_stock_list = []

            for stock in self.stock_list[::-1]:

                #  Skip stock if in the skip list
                if (stock in self.skip_list):
                    print(self.src_name + ":  SKIPPING '" + stock + "'")
                    continue

                #  Bypass back-off logic if in playback mode
                if config.runtime_params['playback']:
                    active_stock_list.append(stock)

                    continue

                self.backoff [stock]['minor_cnt'] -= 1

                if 0 >= self.backoff [stock]['minor_cnt']:
                    active_stock_list.append(stock)

                    self.backoff [stock]['minor_cnt'] = self.backoff [stock]['minor_reset']
                else:
                    print(self.src_name + ":  BACKING-OFF '" + stock + "'  back-off state:  %d/%d (minor)  %d/%d (major)" %
                        (self.backoff [stock]['minor_cnt'], self.backoff [stock]['minor_reset'], self.backoff [stock]['major_cnt'], self.backoff [stock]['major_reset']))


            #  Get time hack to be recorded for queries which will be made
            time_hack = datetime.now()


            #  Add entries for each combination of stock and query type
            self.stock_list_cur = []

            if None is not self.get_query_types:
                query_types = self.get_query_types()
            else:
                query_types = ['DEFAULT']

            for query_type in query_types:

                #  Review the active stock list for this query type
                active_stock_list0 = self.review_query_list(active_stock_list, query_type, len(query_types), time_hack)

                for stock in active_stock_list0:

                    #  Record (stock, query_type) in list of queries to be made shortly
                    self.stock_list_cur.append(stock + '::' + query_type)


            #  Shuffle the list if requested
            if self.shuffle_queries:
                random.shuffle(self.stock_list_cur)


            #  Initial query
            self.query_driver_pt1()


 #  TODO:  Add logic to detect and correctly handle case where the batch list ends up having length zero

    def make_batch_list_pt1(self, stock_list):
        batch_list = []

        query_type = ''

        for augmented_stock in stock_list:

            stock, query_type_instance = augmented_stock.split('::', 1)

            #  TODO:  Ensure that only one type of query is present
            if '' == query_type:
               query_type = query_type_instance

            if query_type != query_type_instance:
                print(f"ERROR(Source_Generic::make_batch_list_pt1):  Mixing query types in batch mode ('{query_type}' and '{query_type_instance}').  Skipping symbol {stock}.")
                continue

            '''
            #  Skip if in the skip list
            if (stock in self.skip_list):
                print(self.src_name + ":  SKIPPING '" + stock + "'")
                continue
            '''

            #  Translate local symbol to source symbol if needed
            stock_use = stock

            if stock in self.map_symbols:
                stock_use = self.map_symbols[stock]


            #  Add symbol and it's src name to list in batch
            batch_list.append({'loc_symbol': stock, 'qry_symbol': stock_use, 'query_type': query_type})


            if config.runtime_params['debug_options']['stock']:
                print("DBG:  stock='" + stock + "'  batch_list='" + str(batch_list) + "'")


        return batch_list


    def make_batch_list_pt2(self, stock_list):
        batch_list = []

        for stock in stock_list:

            #  Skip if in the skip list
            if (stock in self.skip_list):
                print(self.src_name + ":  SKIPPING '" + stock + "'")
                continue

            #  Translate local symbol to source symbol if needed
            stock_use = stock

            if stock in self.map_symbols:
                stock_use = self.map_symbols[stock]


            #  Add symbol and it's src name to list in batch
            batch_list.append({'loc_symbol': stock, 'qry_symbol': stock_use})


            if config.runtime_params['debug_options']['stock']:
                print("DBG:  stock='" + stock + "'  batch_list='" + str(batch_list) + "'")


        return batch_list


    #  SUBCLASS OVERRIDE

    #  Base class default parameters
    def configure_lvl0(self):

        print('Inside Source_Generic::configure_lvl0()')


        self.version = "<<>>"

        if not hasattr(self, 'make_query_custom'):
            self.make_query_custom = None
        self.shuffle_queries = False

        #  Query frequency and batch parameters
        self.mkt_beg_today = None
        self.mkt_end_today = None
        self.delta_quote = 24 * 60 * 60

        self.poll_sleep_time = 0.25

        self.batch_sleep_time = 13
        self.max_threads = 10

        self.max_batch = 20

        self.pause       = False
        self.pause_sleep = 10

        self.timeout    = 3.5
        self.to_backoff = 3.0 / 2.0


        #  List missing symbols
        self.map_symbols = {
            'FB':   'META',
        }

        self.skip_list = []


        #  Define when the market is open
        self.mkt_time_zone = 'America/New_York'

        if config.runtime_params['production']:
            if not config.runtime_params['offset_mkt_begin']:
                self.mkt_beg_time  =  93000
                self.mkt_end_time  = 163000
            else:
                self.mkt_beg_time  =  93030
                self.mkt_end_time  = 163000
        else:
            self.mkt_beg_time  =      1
            self.mkt_end_time  = 360000


        self.skip_today = False


        #  Normalize input to a single line
        self.query_raw_norm = ' *\n *'


        #  Specify user agent
        self.hdr = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1'
        }

        self.query_type_src = {'<<PLACE_HOLDER>>': False}


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_<<>>.txt'


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl0']:
            self.dump_src_attributes (0)


    #  Helper function for configure_lvl1()
    def global_to_source(self, gbl_name, default):

        #  Return default if entry in question does not exist in user supplied configuration
        if 'user_config' not in config.runtime_params:
            return default

        elif 'Generic' not in config.runtime_params['user_config']:
            return default

        elif gbl_name not in config.runtime_params['user_config']['Generic']:
            return default


        #  Return the entry in question in user supplied configuration
        return config.runtime_params['user_config']['Generic'][gbl_name]


    def configure_lvl1(self):

        print('Inside Source_Generic::configure_lvl1()')


#       self.version = "<<>>"

#       self.make_query_custom = None
        if config.runtime_params['shuffle_queries']:
            self.shuffle_queries = True
        else:
            self.shuffle_queries = self.global_to_source('shuffle_queries', self.shuffle_queries)

        #  Query frequency and batch parameters
#       self.mkt_beg_today = None
#       self.mkt_end_today = None
        self.delta_quote = self.global_to_source('delta_quote', self.delta_quote)

        self.poll_sleep_time = self.global_to_source('poll_sleep_time', self.poll_sleep_time)

        self.batch_sleep_time = self.global_to_source('batch_sleep_time', self.batch_sleep_time)
        self.max_threads = self.global_to_source('max_threads', self.max_threads)

        self.max_batch = self.global_to_source('max_batch', self.max_batch)

#       self.pause       = False
        self.pause_sleep = self.global_to_source('pause_sleep', self.pause_sleep)

        self.timeout = self.global_to_source('timeout', self.timeout)
        self.to_backoff = self.global_to_source('to_backoff', self.to_backoff)


        #  List missing symbols
        self.map_symbols = self.global_to_source('map_symbols', self.map_symbols)

#       self.skip_list = []


        #  Define when the market is open
        self.mkt_time_zone = self.global_to_source('mkt_time_zone', self.mkt_time_zone)

        self.mkt_beg_time = self.global_to_source('mkt_beg_time', self.mkt_beg_time)
        self.mkt_end_time = self.global_to_source('mkt_end_time', self.mkt_end_time)


        if config.runtime_params['skip_first_day']:
            self.skip_today = True
        else:
            self.skip_today = False


        #  Normalize input to a single line
        self.query_raw_norm = self.global_to_source('query_raw_norm', self.query_raw_norm)


        #  Specify user agent
        self.hdr = self.global_to_source('hdr', self.hdr)

#       self.query_type_src = {'<<PLACE_HOLDER>>': False}


        #  Configure dry run parameters
        self.dry_run_file = self.global_to_source('dry_run_file', self.dry_run_file)


#       self.populate_stock_list(config.runtime_params['symbols'])


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl1']:
            self.dump_src_attributes (1)


    #  Generic Source specific configuration
    '''
    def configure_lvl2(self):

        print('Inside Source_Generic::configure_lvl2()')


        self.version = "2024-08-01a"

        self.shuffle_queries = False

#       self.make_query_custom = None
#       self.shuffle_queries = False

        #  Query frequency and batch parameters
#       self.mkt_beg_today = None
#       self.mkt_end_today = None
#       self.delta_quote = 24 * 60 * 60

#       self.poll_sleep_time = 0.25

#       self.batch_sleep_time = 13
#       self.max_threads = 10

#       self.max_batch = 20

#       self.pause       = False
#       self.pause_sleep = 10

#       self.timeout    = 3.5
#       gelf.to_backoff = 3.0 / 2.0


        #  List missing symbols
#       self.map_symbols = {
#           'FB':   'META',
#       }

#       self.skip_list = []


        #  Define when the market is open
#       self.mkt_time_zone = tz.gettz('America/New_York')

#       if config.runtime_params['production']:
#           if not config.runtime_params['offset_mkt_begin']:
#               self.mkt_beg_time  =  93000
#               self.mkt_end_time  = 163000
#           else:
#               self.mkt_beg_time  =  93030
#               self.mkt_end_time  = 163000
#       else:
#           self.mkt_beg_time  =      1
#           self.mkt_end_time  = 360000


#       self.skip_today = False


        #  Normalize input to a single line
#       self.query_raw_norm = re.compile(' *\n *')


        #  Specify user agent
#       self.hdr = {
#           'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1'
#       }

#       self.query_type_src = {'<<PLACE_HOLDER>>': False}


        #  Configure dry run parameters
#       self.dry_run = False
        self.dry_run_file = 'exampleJSON_generic_source.txt'


        self.id_URL = re.compile('.*')


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl2']:
            self.dump_src_attributes (2)
    '''


    def configure_lvl3(self):

        print(f'Inside Source_Generic::configure_lvl3()  ({self.src_name})')


        #  Assimilate the configs for this source
        if self.src_name in config.runtime_params['user_config']:
            for (key, item) in config.runtime_params['user_config'][self.src_name].items():

                try:
                    #  Ensure the attribute is there
                    attr = getattr(self, key)

                    #  Set attribute 'key' to 'item'
                    setattr(self, key, item)  # attr = item
                except AttributeError:
                    pass

        #  Convert attributes to objects
        self.mkt_time_zone  = tz.gettz(self.mkt_time_zone)
        self.query_raw_norm = re.compile(self.query_raw_norm)


        #  Populate stock list
        self.populate_stock_list(config.runtime_params['symbols'])


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl3']:
            self.dump_src_attributes (3)


    #  SUBCLASS OVERRIDE

    def get_query_types(self):

        return [ 'GS_QUOTE' ]


    #  SUBCLASS OVERRIDE

    def id_quote(self, quote):
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

        return "<< TODO >>", "<< TODO >>", "<< TODO >>"


    #  SUBCLASS OVERRIDE

    #  Convert response to dictionary
    def response_to_dictionary(self, query_raw):

        query_json = json.loads(query_raw)


        #  Remove extraneous layers from the JSON
#       query_json = query_json["QuickQuoteResult"]["QuickQuote"]


        return query_json


    #  SUBCLASS OVERRIDE

    def symbol_rollcall(self, batch_list, query_json, query):

        #  Determine if the number of response symbols equals number of requested symbols
        return False


    #  SUBCLASS OVERRIDE

    def normalize_query(self, query_raw):
        return self.query_raw_norm.sub(' ', query_raw)


    #  SUBCLASS OVERRIDE

    def get_query_stock(self, qry_symbol, query_json):
        query_stock = None

#       print(query_stock)

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


    def timeWindowCheck(self, time_zone, hhmmss_beg, hhmmss_end):

        now = datetime.now(time_zone)
        today = date (now.year, now.month, now.day)

        hhmmss = int(now.strftime('%H%M%S'))


        if config.runtime_params['production']:

            #  Determine if we are currently within the time window
            if (hhmmss_beg <= hhmmss) and (hhmmss <= hhmmss_end):
                mkt_open = True
            else:
                mkt_open = False

            #  Market is not open if today is not a market day
            if  (not self.is_work_day(today)):
                mkt_open = False
        else:

            #  Determine if we are currently within the time window
            if (hhmmss_beg <= hhmmss) and (hhmmss <= hhmmss_end):
                mkt_open = True

            #  Determine if we are currently within the shifted time window
            elif (hhmmss_beg <= (hhmmss + 240000)) and ((hhmmss + 240000) <= hhmmss_end):
                mkt_open = True

            else:
                mkt_open = False


        #  Determine when the next time window will open
        hh = int(hhmmss_beg / 10000) % 100
        mm = int(hhmmss_beg / 100  ) % 100
        ss = int(hhmmss_beg        ) % 100

        next = now
        next = next.replace(hour=hh, minute=mm, second=ss)

        if hhmmss >= hhmmss_beg:
            next += timedelta(days=1)


#       print ('===> hhmmss=%06d   mkt_open=%s  next=%s' % (hhmmss, str(mkt_open), next.strftime('%H%M%S')))


        #  Return the results back to the caller
        return (mkt_open, next)


    def parse_JSON(self, dst, field, src, level1, level2, field_type):
        if level1 in src:
            if '' == level2:
                if None is src[level1]:
                    dst[field] = src[level1]
                elif 'string' == field_type:
                    dst[field] = src[level1]
                elif 'float' == field_type:
                    dst[field] = float(src[level1])
                elif 'int' == field_type:
                    dst[field] = round(float(src[level1]))
                elif 'intArray' == field_type:
                    dst[field] = src[level1]
                    for idx in range(0, len(dst[field])):
#                       if 'NoneType' != type(dst[field][idx]).__name__:
                        if None is not dst[field][idx]:
                            dst[field][idx] = round(float(dst[field][idx]))
                        else:
                            dst[field][idx] = 0
                elif 'floatArray' == field_type:
                    dst[field] = src[level1]
                    for idx in range(0, len(dst[field])):
#                       if ('NoneType' != type(dst[field][idx]).__name__):
                        if None is not dst[field][idx]:
                            dst[field][idx] = float(dst[field][idx])
                        else:
                            dst[field][idx] = 0
                elif 'bool' == field_type:
                    if 'bool' == type(src[level1]).__name__:
                        dst[field] = src[level1]
                    elif 'str' == type(src[level1]).__name__:
                        if re.match(r'(?i)^true$', src[level1]):
                            dst[field] = True
                        elif re.match(r'(?i)^false$', src[level1]):
                            dst[field] = False
                        else:
                            dst[field] = bool(src[level1])
                else:
                    raise Exception('UNKNOWN FIELD TYPE')
            elif level2 in src[level1]:
                if None is src[level1][level2]:
                    dst[field] = src[level1][level2]
                elif 'string' == field_type:
                    dst[field] = src[level1][level2]
                elif 'float' == field_type:
                    dst[field] = float(src[level1][level2])
                elif 'int' == field_type:
                    dst[field] = round(float(src[level1][level2]))
                elif 'bool' == field_type:
                    if 'bool' == type(src[level1]).__name__:
                        dst[field] = src[level1]
                    elif 'str' == type(src[level1]).__name__:
                        if re.match(r'(?i)^true$', src[level1]):
                            dst[field] = True
                        elif re.match(r'(?i)^false$', src[level1]):
                            dst[field] = False
                        else:
                            dst[field] = bool(src[level1])
                else:
                    raise Exception('UNKNOWN FIELD TYPE')
