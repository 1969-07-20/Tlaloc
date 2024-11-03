#! /usr/bin/bash

: <<'COMMENT'
StartTlaloc.py:  Script to be called by systemd to start Tlaloc.

Copyright 2024 Tlaloc Labs LLC

Distributed under the terms of the GNU Affero General Public License.
See the file LICENSE.txt in this distribution or <https://www.gnu.org/licenses/>.
COMMENT


#  This script was written to start Tlaloc when run as a systemd service
#  on a Raspberry Pi running Ubuntu

#  Create name of logfile
dateStr=`date "+%Y%m%d"`
timeStr=`date "+%H%M%S"`

logFile="/home/pi/tlLog_${dateStr}_${timeStr}.txt"

echo "logFile='$logFile'"


#  Activate the Miniconda environment
. /home/pi/miniconda3/bin/activate Tlaloc
# /home/pi/miniforge3/bin/activate Tlaloc

#  List conda environments
conda info --envs

#  List packages in 'Tlaloc' environment
conda list -n Tlaloc

#  cd to the directory with the Tlaloc script and run it
cd ~/Tlaloc/
#home/pi/miniconda3/bin/python ./tlaloc.py  &> $logFile
#home/pi/miniforge3/bin/python ./tlaloc.py  &> $logFile
                        python ./tlaloc.py  &> $logFile
