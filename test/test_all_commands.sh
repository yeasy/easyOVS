#!/bin/bash

# This script will test all supported commands inside easyovs and output the
# results into the _log file

[ ! -e header.sh ] && echo_r "Not found header file" && exit -1
. ./header.sh

log_file=$0".log"

[ -f ${log_file} ] && mv ${log_file} ${log_file}"_bak"

echo_b "All results would be recorded into ${log_file}"

echo_b "##Test: easyovs -m addbr br-test" | tee -a ${log_file}
if easyovs -m 'addbr br-test' | tee -a ${log_file} | grep -i "error" > /dev/null 2>&1
then
    echo_r "Failed" | tee -a ${log_file}
    exit -1
else
	echo_g "Passed" | tee -a ${log_file}
fi

echo_b "##Test: easyovs -m delbr br-test" | tee -a ${log_file}
if easyovs -m 'delbr br-test' | tee -a ${log_file} | grep -i "error" > /dev/null 2>&1
then
    echo_r "Failed" | tee -a ${log_file}
    exit -1
else
	echo_g "Passed" | tee -a ${log_file}
fi

echo_b "##Test: easyovs -m list" | tee -a ${log_file}
easyovs -m 'addbr br-test'
if easyovs -m list | tee -a ${log_file} | grep "br-test" > /dev/null 2>&1
then
	echo_g "Passed" | tee -a ${log_file}
else
    echo_r "Failed" | tee -a ${log_file}
    exit -1
fi
easyovs -m 'delbr br-test'


exit 0
