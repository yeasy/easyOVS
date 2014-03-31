#!/usr/bin/python

__author__ = 'baohua'

import sys
import time

from log import info, debug, error, output
from clean import cleanup
from cli import CLI


class Platform( object ):
    "Build, setup, and run the platform."

    def __init__( self ):
        "Init."
        self.options = None
        self.parseArgs()
        self.setup()
        self.begin()

    def parseArgs(self):
        pass

    def setup( self ):
        pass

    def begin( self ):
        start = time.time()
        output("***\n Welcome to EasyOVS, type help to see available commands.\n***\n")
        CLI()
        elapsed = float( time.time() - start )
        info( 'completed in %0.3f seconds\n' % elapsed )

if __name__ == "__main__":
    try:
        Platform()
    except KeyboardInterrupt:
        info( "\n\nKeyboard Interrupt. Shutting down and cleaning up...\n\n")
        cleanup()
    except Exception:
        # Print exception
        type_, val_, trace_ = sys.exc_info()
        errorMsg = ( "-"*80 + "\n" +
                     "Caught exception. Cleaning up...\n\n" +
                     "%s: %s\n" % ( type_.__name__, val_ ) +
                     "-"*80 + "\n" )
        error( errorMsg )
        # Print stack trace to debug log
        import traceback
        stackTrace = traceback.format_exc()
        debug( stackTrace + "\n" )
        cleanup()