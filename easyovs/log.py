__author__ = 'baohua'

from logging import Logger
import logging
import sys
import types


OUTPUT = 25

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'output': OUTPUT,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

LOGLEVELDEFAULT = 'output'

#default: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGMSGFORMAT = '%(message)s'

# Modified from python2.5/__init__.py
class StreamHandlerNoNewline(logging.StreamHandler):
    """StreamHandler that doesn't print newlines by default.
       Since StreamHandler automatically adds newlines, define a mod to more
       easily support interactive mode when we want it, or errors-only logging
       for running unit tests."""

    def emit(self, record):
        """Emit a record.
           If a formatter is specified, it is used to format the record.
           The record is then written to the stream with a trailing newline
           [ N.B. this may be removed depending on feedback ]. If exception
           information is present, it is formatted using
           traceback.printException and appended to the stream."""
        try:
            msg = self.format(record)
            fs = '%s'  # was '%s\n'
            if not hasattr(types, 'UnicodeType'):  # if no unicode support...
                self.stream.write(fs % msg)
            else:
                try:
                    self.stream.write(fs % msg)
                except UnicodeError:
                    self.stream.write(fs % msg.encode('UTF-8'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class Singleton(type):
    """Singleton pattern from Wikipedia
       See http://en.wikipedia.org/wiki/Singleton_Pattern

       Intended to be used as a __metaclass_ param, as shown for the class
       below."""

    def __init__(cls, name, bases, dict_):
        super(Singleton, cls).__init__(name, bases, dict_)
        cls.instance = None

    def __call__(cls, *args, **kw):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kw)
            return cls.instance


class OVSLogger(Logger, object):
    __metaclass__ = Singleton

    def __init__(self):

        Logger.__init__(self, "EasyOVS")

        # create console handler
        ch = StreamHandlerNoNewline(sys.stdout)
        # create formatter
        formatter = logging.Formatter(LOGMSGFORMAT)
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to lg
        self.addHandler(ch)

        self.set_log_level()

    def set_log_level(self, levelname=LOGLEVELDEFAULT):
        level = LEVELS.get(levelname)

        self.setLevel(level)
        self.handlers[0].setLevel(level)

    def output(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity 'OUTPUT'.

           To pass exception information, use the keyword argument exc_info
           with a true value, e.g.

           logger.warning("Houston, we have a %s", "cli output", exc_info=1)
        """
        if self.manager.disable >= OUTPUT:
            return
        if self.isEnabledFor(OUTPUT):
            self._log(OUTPUT, msg, args, kwargs)

lg = OVSLogger()


def make_list_compatible(fn):
    """Return a new function allowing fn( 'a 1 b' ) to be called as
       newfn( 'a', 1, 'b' )"""

    def newfn(*args):
        """
        Generated function. Closure-ish.
        """
        if len(args) == 1:
            return fn(*args)
        args = ' '.join([str(arg) for arg in args])
        return fn(args)

    # Fix newfn's name and docstring
    setattr(newfn, '__name__', fn.__name__)
    setattr(newfn, '__doc__', fn.__doc__)
    return newfn


info, output, warn, error, debug = (
    lg.info, lg.output, lg.warn, lg.error, lg.debug) = \
    [make_list_compatible(f) for f in
     lg.info, lg.output, lg.warn, lg.error, lg.debug]

setLogLevel = lg.set_log_level
