#!/usr/bin/python2
'''Something to make managing single-use aliases easier.
It doesn't remove extraneous aliases from configuration yet.
'''

import os
import sys

from lxml import etree
from rnc2rng import rnctree

import handlers

def parse_config():
    validator = etree.RelaxNG(etree.fromstring(rnctree.make_nodetree(rnctree.token_list(open('schema.rnc').read())).toxml()))
    config = etree.parse("config.xml")

    try:
        validator.assertValid(config)
    except etree.DocumentInvalid as e:
        print "Configuration error:", e
        sys.exit(-1)

    return config.getroot()

if os.geteuid() != 0:
    print "This tool must be run as root."
    sys.exit(-1)

config = parse_config()
get_option = lambda option: config.find(option).text

aliases = config.findall("alias")

nginx = handlers.NginxHandler(get_option)
bind = handlers.BindHandler(get_option)

handlers = [nginx, bind]

for alias in aliases:
    for handler in handlers:
        if alias.get("name") not in handler.names:
            handler.add(alias)

[handler.flush() for handler in handlers]
