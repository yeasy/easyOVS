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

echo_b "##Test: easyovs -m 'delbr br-test'" | tee -a ${log_file}
if easyovs -m 'delbr br-test' | tee -a ${log_file} | grep -i "error" > /dev/null 2>&1
then
    echo_r "Failed" | tee -a ${log_file}
    exit -1
else
    echo_g "Passed" | tee -a ${log_file}
fi

echo_b "##Test: easyovs -m list" | tee -a ${log_file}
easyovs -m 'addbr br-test' > /dev/null 2>&1
if easyovs -m list | tee -a ${log_file} | grep "br-test" > /dev/null 2>&1
then
    echo_g "Passed" | tee -a ${log_file}
else
    echo_r "Failed" | tee -a ${log_file}
    exit -1
fi
easyovs -m 'delbr br-test' > /dev/null 2>&1

echo_b "##Test: easyovs -m 'addflow br-test priority=3 ip actions=OUTPUT:1'" | tee -a ${log_file}
easyovs -m 'addbr br-test' > /dev/null 2>&1
if easyovs -m 'addflow br-test priority=3 ip actions=OUTPUT:1' | tee -a ${log_file} | grep -i "error" > /dev/null 2>&1
then
    echo_r "Failed" | tee -a ${log_file}
    exit -1
else
    echo_g "Passed" | tee -a ${log_file}
fi

echo_b "##Test: easyovs -m delflow" | tee -a ${log_file}


echo_b "##Test: easyovs -m dump" | tee -a ${log_file}
easyovs -m 'addflow br-test priority=5 ip actions=OUTPUT:989' > /dev/null 2>&1
if easyovs -m 'dump br-test' | tee -a ${log_file} | grep -i "output:989" > /dev/null 2>&1
then
    echo_g "Passed" | tee -a ${log_file}
else
    echo_r "Failed" | tee -a ${log_file}
    exit -1
fi
easyovs -m 'delbr br-test' > /dev/null 2>&1

exit 0
