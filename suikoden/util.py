import argparse
import os
import sys

def perm_check():
    if os.geteuid() != 0:
        print("This tool must be run as root.")
        sys.exit(-1)

parser = argparse.ArgumentParser()
parser.add_argument('--list-apps', help='List the registered applications and quit.', action='store_true')
parser.add_argument('-f', '--force', help='Force all entries to be rebuilt.', action='store_true')
