#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Test the openstack python sdk, based on restful APIs.
# ref: http://docs.openstack.org/user-guide/content/sdk_auth.html

__author__ = 'baohua'
from easyovs import config
from oslo.config import cfg
import keystoneclient.v2_0.client as ksclient
import neutronclient.v2_0.client as neutronclient
import novaclient.v1_1.client as nvclient

import sys

if __name__ == '__main__':
    config.init(sys.argv[1:])

    keystone = ksclient.Client(auth_url=cfg.CONF.OS.auth_url,
                               tenant_name=cfg.CONF.OS.tenant_name,
                               username=cfg.CONF.OS.username,
                               password=cfg.CONF.OS.password)
    token = keystone.auth_token

    #nova_endpoint_url = keystone.service_catalog.url_for(
    # service_type='compute')
    nova = nvclient.Client(auth_token=token)

    neutron_endpoint_url = keystone.service_catalog.url_for(
        service_type='network')
    neutron = neutronclient.Client(endpoint_url=neutron_endpoint_url,
                                   token=token)
    print neutron.list_networks()
    print neutron.list_ports()
