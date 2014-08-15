from .confparse import ConfParse
from .handler import Handler
from .util import perm_check, parser

# There are better solutions to this...
from .handlers import *

config = ConfParse()
config.parse()

def run_handlers(args):
    Handler.instantiate(config, args)
    Handler.run(config.all("alias", "app"))
    Handler.flush_all()

def list_apps(args):
    Handler.instantiate(config, args)
    Handler.run(config.all("alias", "app"))
    mdh = Handler.instance_by_class(MakefileHandler)
    mdh.list_apps()

if __name__ == "__main__":
    perm_check()

    args = parser.parse_args()

    if args.list_apps:
        list_apps(args)

    else:
        run_handlers(args)
