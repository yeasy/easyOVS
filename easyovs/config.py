__author__ = 'baohua'

from gettext import gettext as _

import os
try:
    from oslo_config import cfg
except ImportError:
    from oslo.config import cfg
from easyovs import VERSION
from easyovs.log import LEVELS, LOGLEVELDEFAULT

from easyovs.common import CMDS_ONE, CMDS_TWO, CMDS_OTHER

default_opts = [
]
cfg.CONF.register_cli_opts(default_opts)
cfg.CONF.register_opts(default_opts)


openstack_opts = [
    cfg.StrOpt('auth_url',
               default=os.getenv('OS_AUTH_URL', 'http://127.0.0.1:5000/v2.0'),
               help='Authentication URL, defaults to env[OS_AUTH_URL].'),
    cfg.StrOpt('username',
               default=os.getenv('OS_USERNAME', 'admin'),
               help='Authentication username, defaults to env[OS_USERNAME].'),
    cfg.StrOpt('password',
               default=os.getenv('OS_PASSWORD', 'admin'),
               help=' Authentication password, defaults to env[OS_PASSWORD].'),
    cfg.StrOpt('tenant_name',
               default=os.getenv('OS_TENANT_NAME', 'admin'),
               help='Authentication tenant name, defaults to env[OS_TENANT_NAME].'),
]
cfg.CONF.register_opts(openstack_opts, "OS")

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


# read all parameters from /etc/easyovs.conf or...
def init(args, **kwargs):
    cfg.CONF(args=args, project='easyovs',
             version='%%prog %s' % VERSION,
             **kwargs)
