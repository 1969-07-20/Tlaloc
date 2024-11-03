# -*- coding: utf-8 -*-

"""Source_Playback_DailySummary.py:  Implements the class which plays back
   previously recorded data, facilitating off-line development.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import config

from Source_Generic import Source_Generic

#mport json
import re
#mport pprint


# BEG Source_Playback.py SPECIFIC
from datetime import datetime

from dateutil import tz
# END Source_Playback.py SPECIFIC


class Source_Playback(Source_Generic):

    def __init__(self):
        print('Inside Source_Playback::__init__()')

        self.src_name = "Source_Playback"

        super().__init__()

        self.configure_lvl2()   #  Default specific class configs
        self.configure_lvl3()   #  Override specific class override


    def populate_stock_list(self, stock_list):
        self.stock_list = []
        self.backoff = {}

        self.stock_list.append('<<PLAYBACK>>')


    def fetch_query_playback(self, batch_list,  query, query_sanitized, ):

        #  Ensure preconditions are met
        if self.fp is None:
            return None, True


        #  Read lines from file for next entry
        resync = False
        state  = 0

        while True:
            line = self.fp.readline()

            if not line:
                break

            self.line_cnt += 1
            line = line.strip()

#           print("Line {}.{}: {}".format(self.line_cnt, state, line.strip()))

            #  Handle resync operation if in resync mode:  skip lines until first one that begins "ENTRY..."
            if resync:
                # m0 = re.compile('^ENTRY\[\d+\]: *TYPE=QUOTE *TIME=.*QUERY_TYPE=(.*) *VERSION=.*$')
                if self.m0.match(line):
                     resync = False

                     state = 0

                elif '' != line:
                     print("WARNING:  Skipping line while resyncing with input stream")
                     continue

            #  Process non-blank line
            if '' != line:

                # m0 = re.compile('^ENTRY\[\d+\]: *TYPE=QUOTE *TIME=.*QUERY_TYPE=(.*) *VERSION=.*$')
                if self.m0.match(line):
                    if 0 == state:
                        quote_time = line

                        state = 1
                    else:
                        print(f'ERROR #1:  line="{line}"')
                        resync = True

                # m2 = re.compile('^https:\/\/')
                elif self.m2.match(line):
                    if 2 == state:
                        quote_url = line

                        state = 3
                    else:
                        print(f'ERROR #2:  line="{line}"')
                        resync = True

                # m3 = re.compile('^\{.*\}$')
                elif self.m3.match(line):
                    if 3 == state:
                        quote_content = line

                        return [quote_time, quote_symbols, quote_url, quote_content], False
                    else:
                        print(f'ERROR #3:  line="{line}"')
                        resync = True

                else:
                    if 1 == state:
                        quote_symbols = line

                        state = 2
                    else:
                        print(f'ERROR #4:  line="{line}"')
                        resync = True

        #  Unable to read from file, close it
        self.fp.close()
        self.fp = None

        self.pause = True

        print("PLAYBACK EXHAUSTED INPUT FILE.  HALTING...")

        return None, True


    def make_query(self, thread_timestamp, thread_num, query_type_src, batch_list, ):

        #  Create timestamps  (TODO:  Find a way to use one time hack for both time stamps)
        log_timestamp = datetime.now(tz.gettz('UTC')).strftime('%Y-%m-%d %H:%M:%S.%f %Z')
        dbg_timestamp = datetime.now(tz.tzlocal()).strftime('%Y-%m-%d %H:%M:%S.%f %Z')


        #  Create query URL
        query, query_sanitized, query_type_loc = self.make_query_url(batch_list)


        #  Debug query
        if config.runtime_params['debug_options']['query']:
            print("DBG(" + self.src_name + ", " + dbg_timestamp + "):  query='" + query_sanitized + "'")


        quote, fetch_failed = self.fetch_query_playback(batch_list,  query, query_sanitized, )

        if fetch_failed:
            self.mark_thread_done(thread_timestamp, thread_num)

            return


        #  Normalize response (e.g. removing line breaks)
        quote[3] = self.normalize_query(quote[3])


        #  Debug raw response
        if config.runtime_params['debug_options']['query_raw']:
            print("DBG:  query_raw='" + quote[3] + "'")


        #  Log response
        query_msg_head = "\n" + \
                         "\n" + \
                         quote[0] + "\n"
        query_msg_body = quote[1] + "\n" + \
                         quote[2] + "\n" + \
                         quote[3] + "\n"

        with config.log_q_lock:

            #  Combine the three parts of query message together
            query_msg = query_msg_head + query_msg_body

            # Send response through pipe to the processing side
            config.sp_queue.put(query_msg)

            # Log quote
            if config.log_quotes is not None:
                config.log_quotes.write(query_msg)


        #  Indicate thread is done
        self.mark_thread_done(thread_timestamp, thread_num)


    #  Playback specific configuration
    def configure_lvl2(self):

        print('Inside Source_Playback::configure_lvl2()')


        self.version = "2024-08-01a"

        self.shuffle_queries = False


        #  Query frequency and batch parameters
        self.delta_quote = 0.10

        self.poll_sleep_time = 0.05

        self.batch_sleep_time = 0.10
        self.max_threads = 1

        self.max_batch = 1


        #  Define when the market is open
        self.mkt_beg_time  =      1
        self.mkt_end_time  = 360000

        self.skip_today = False


        #  Configure dry run parameters
        self.dry_run_file = 'exampleJSON_playback.txt'

        #  Open file with input
        self.fp = open('combined.txt', 'r')

        #  Initialize state related to file
        self.line_cnt = 0

        #  Precompile regular expressions
        self.m0 = re.compile('^ENTRY\[\d+\]: *TYPE=QUOTE *TIME=.*QUERY_TYPE=(.*) *VERSION=.*$')
        self.m2 = re.compile('^https:\/\/')
        self.m3 = re.compile('^\{.*\}$')


        #  Debug attributes
        if config.runtime_params['debug_options']['src_attr_lvl2']:
            self.dump_src_attributes (2)


    #  SUBCLASS OVERRIDE

    def get_query_types(self):

        return [ 'PB_QUOTE' ]


    #  This method makes a blank stock entry
    def make_stock_entry(self):

        #  TODO FIXME
        return {
            'quote': {
            }
        }


    def make_query_url(self, batch_list):

        return "<< TODO >>", "<< TODO >>", "<< TODO >>"
