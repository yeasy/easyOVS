__author__ = 'baohua'

from gettext import gettext as _

from oslo.config import cfg
from easyovs import VERSION
from easyovs.log import LEVELS, LOGLEVELDEFAULT

from easyovs.common import CMDS_ONE, CMDS_TWO, CMDS_OTHER

default_opts = [
]
cfg.CONF.register_cli_opts(default_opts)
cfg.CONF.register_opts(default_opts)


admin_opts = [
    cfg.StrOpt('auth_url',
               default='http://127.0.0.1:5000/v2.0',
               help='authentication url in keystone'),
    cfg.StrOpt('username',
               default='admin',
               help='username in keystone'),
    cfg.StrOpt('password',
               default='admin',
               help='username in keystone'),
    cfg.StrOpt('tenant_name',
               default='admin',
               help='the tenant name to check'),
]
cfg.CONF.register_opts(admin_opts, "ADMIN")
cfg.CONF.register_opts(admin_opts, "PROJECT")

cli_opts = [
    cfg.StrOpt('verbosity',
                short='v',
                default=LOGLEVELDEFAULT,
                choices=LEVELS,
                help='Set the verbose level.'),
    cfg.StrOpt('cmd',
                short='m',
                default='cli',
                help='Run some inside command directly'),
    cfg.BoolOpt('clean',
                short='c',
                default=False,
                help='Clean the environment and exit.'),
]

cfg.CONF.register_cli_opts(cli_opts)


def init(args, **kwargs):
    cfg.CONF(args=args, project='easyovs',
             version='%%prog %s' % VERSION,
             **kwargs)
