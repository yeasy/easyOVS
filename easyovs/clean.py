__author__ = 'baohua'

from subprocess import Popen, PIPE

from easyovs.log import info

def sh( cmd ):
    "Print a command and send it to the shell"
    info( cmd + '\n' )
    return Popen( [ '/bin/sh', '-c', cmd ], stdout=PIPE ).communicate()[ 0 ]

def cleanup():
    """Clean up junk which might be left over from old runs;
    """
    sh( 'pkill -9 -f "neutron port-list"')

    info( "*** Removing junk from /tmp\n" )
    sh( 'rm -f /tmp/tmp_switch_* /tmp/vlogs* /tmp/*.out /tmp/*.log' )

    info( "*** Cleanup complete.\n" )