import argparse
import os
import sys

def perm_check():
    if os.geteuid() != 0:
        print("This tool must be run as root.")
        sys.exit(-1)

parser = argparse.ArgumentParser(description='Manage some things')
parser.add_argument('--list-apps', help='List the registered applications and quit.', action='store_true')
parser.add_argument('--start-apps', help='Start all registered applications and quit.', action='store_true')
parser.add_argument('-f', '--force', help='Force all entries to be rebuilt.', action='store_true')
parser.add_argument('--increment-zone', help='Increment the zone serial of the bind-master.', action='store_true')
parser.add_argument('--reload-services', help='Reload affected services (nginx and powerdns).', action='store_true')
