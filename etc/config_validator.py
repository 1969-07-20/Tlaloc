#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""config_validator.py:  This program validates the syntax of Tlaloc config files.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
"""

import json
import re

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
    config_text = read_config_file('config.txt')

    #  Update runtime_parms data structure if text is not null
    if not '' == config_text:
        try:
           config = json.loads(config_text.replace('\n', ' '))

           print(f'\n\n')
           print(f'Result of parsing of "config.txt"')
           print(json.dumps(config, indent=4))

        except BaseException as e:
           print(f'ERROR PARSING "config.txt" ({str(e)})')
           print(f'BEG Text of config file (after comments removed)')
           print(config_text)
           print(f'END Text of config file (after comments removed)')

           return


if __name__ == '__main__':

    read_user_config()
