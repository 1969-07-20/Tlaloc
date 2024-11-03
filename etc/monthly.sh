#! /usr/bin/bash

: <<'COMMENT'
monthly.py:  Archive Tlaloc's logs for a month as a single *.tgz file for easy
handling and data transfer.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
COMMENT


#  Ensure one argument given
if [[ $# -ne 1 ]]; then
    echo "ERROR:  Script requires one argument of the form 'yyyy-mm'.  ABORTING"
    exit
fi


#  Ensure argument has the form 'yyyy-mm'
if [[ "$1" =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ ]]
#             |\______/ \______*______/|
#             |   |           |        |
#             |   |           |        |
#             | --year--   --month--   |
#             |          either 01...09|
#      start of line     or 10,11,12   |
#                                 end of line
then
    DATE=$1
    ROOT="data_raw_$DATE"

    echo "STEP #0:  '$DATE'  Results will be in '$ROOT'"
else
    echo "ERROR:  Argument should be of the form 'yyyy-mm'.  ABORTING"
    exit
fi


#  Make file strings
QUOTES="quotes_$DATE*.txt"
TICKER="ticker_$DATE*.txt"


#  Make directory strings
TL_LOGS="$ROOT/tlLog"
TL_PT1="$ROOT/tl_pt1"
TL_PT2="$ROOT/tl_pt2"


#  Abort if directories exist
echo "STEP #1:  Ensure there is no existing directory '$ROOT'."

ERROR="no"

if [ -d "$TL_LOGS" ]; then
  echo "ERROR:  $TL_LOGS exists.  ABORTING"
  ERROR="yes"
fi

if [ -d "$TL_PT1" ]; then
  echo "ERROR:  $TL_PT1 exists.  ABORTING"
  ERROR="yes"
fi

if [ -d "$TL_PT2" ]; then
  echo "ERROR:  $TL_PT2 exists.  ABORTING"
  ERROR="yes"
fi

if [ -d "$ROOT" ]; then
  echo "ERROR:  $ROOT exists.  ABORTING"
  ERROR="yes"
fi

if [[ ! $ERROR == "no" ]]; then
   exit
fi


echo "STEP #2:  Make directory tree ('$TL_LOGS', '$TL_PT1', '$TL_PT2')"
mkdir -p $TL_LOGS $TL_PT1 $TL_PT2


echo "STEP #3:  Move data files to '$ROOT'."
echo "   - Logs"
mv -i  logs/tlLog/*  $TL_LOGS

echo "   - Part 1 data files"
mv -i  logs/tl_pt1/$QUOTES  $TL_PT1

echo "   - Part 2 data files"
mv -i  logs/tl_pt2/$QUOTES  $TL_PT2


echo "STEP #4:  Remove zero length files:"
touch $TL_PT1/deleteMe
find $ROOT  -size 0 | xargs rm


echo "STEP #5:  Make TGZ file:"
tar zcvf $ROOT.tgz $ROOT
