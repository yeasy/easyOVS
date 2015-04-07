#!/bin/bash

# This script will test all supported commands inside easyovs and output the
# results into the _log file

[ ! -e header.sh ] && echo_r "Not found header file" && exit -1
. ./header.sh

log_file=$0".log"

[ -f ${log_file} ] && mv ${log_file} ${log_file}"_bak"

echo_b "All results would be recorded into ${log_file}"

echo_b "##Test: easyovs -m list" | tee -a ${log_file}
ovs-vsctl --may-exist add-br br-test
if easyovs -m list | tee -a ${log_file} | grep "br-test" > /dev/null 2>&1
then
	echo_g "Passed" | tee -a ${log_file}
else
    echo_r "Failed" | tee -a ${log_file}
fi

ovs-vsctl --if-exists del-br br-test
