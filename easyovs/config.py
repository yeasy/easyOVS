__author__ = 'baohua'

import os
try:
    from oslo_config import cfg
except ImportError:
    from oslo.config import cfg
from easyovs import VERSION
from easyovs.log import LEVELS, LOGLEVELDEFAULT

default_opts = [
]
cfg.CONF.register_cli_opts(default_opts)
cfg.CONF.register_opts(default_opts)


openstack_opts = [
    cfg.StrOpt(
        'auth_url',
        default= os.getenv('OS_AUTH_URL', 'http://127.0.0.1:5000/v2.0'),
        help='Auth URL, defaults to env[OS_AUTH_URL].'),
    cfg.StrOpt(
        'username',
        default=os.getenv('OS_USERNAME', 'admin'),
        help='Auth username, defaults to env[OS_USERNAME].'),
    cfg.StrOpt(
        'password',
        default=os.getenv('OS_PASSWORD', 'admin'),
        help=' Auth password, defaults to env[OS_PASSWORD].'),
    cfg.StrOpt(
        'tenant_name',
        default=os.getenv('OS_TENANT_NAME', 'admin'),
        help='Auth tenant name, defaults to env[OS_TENANT_NAME].'),
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
    cfg.StrOpt('forced',
               short='f',
               default=False,
               help='Run command without confirmation'),
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
