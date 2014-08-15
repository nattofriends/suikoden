import pyparsing
from pyparsing import Suppress
from pyparsing import Regex
from pyparsing import Word

from ..handler import Handler
from ..handler import SubhandlerBase

class BindHandler(Handler):

    comment = Suppress(Regex(";.*"))
    rr = Word(pyparsing.alphanums + '.-').setResultsName("key") + Suppress("IN") + Suppress("CNAME") + pyparsing.Word(pyparsing.alphanums + '.').setResultsName("value")
    line = comment ^ rr ^ pyparsing.empty
    out = "{}\tIN\tCNAME\t{}\n".format

    def __init__(self, *args, **kwargs):
        super(BindHandler, self).__init__(*args, **kwargs)

        self.bind_config = self.config.bind_config
        self.entries = [BindHandler.line.parseString(line) for line in open(self.bind_config).readlines()]
        # This is it. I'm not moving this to funcparserlib. Which idiot thought
        # this was a good idea?

        self._init_subhandlers()

        if self.args.force:
            self.entries = {}
            self.names =[]
        else:
            self.entries = {r.key: r.value for r in self.entries if {'key', 'value'}.symmetric_difference(list(r.keys())) == set()}
            self.names = list(self.entries.keys())

    def _init_subhandlers(self):
        self.subhandlers = {
            'app': BindAppHandler(self),
            'alias': BindAliasHandler(self),
        }

    def add(self, elem):
        self.subhandlers[elem.tag].add(elem)

    def flush(self):
        output = sorted([BindHandler.out(*t) for t in list(self.entries.items())])
        with open(self.bind_config, 'w') as file:
            file.writelines(output)

class BindAliasHandler(SubhandlerBase):
    def add(self, alias):
        self.handler.log("Writing {} to bind configuration".format(alias.get('name')))

        type = alias.get('type')
        if type in ('local', 'redirect', 'diy'):
            self.handler.entries[alias.get('name')] = self.handler.config.resolve_to
        elif type == 'cname':
            self.handler.entries[alias.get('name')] = alias.get('value')

class BindAppHandler(SubhandlerBase):
    def add(self, app):
        name = None
        if app.get("external-name") and app.get("dns-name"):
            raise ValueError("Cannot define both external-name and dns-name")
        elif not bool(app.get("http-name")) == bool(app.get("dns-name")):
            raise ValueError("Only one service-name defined")
        elif app.get("external-name"):
            name = app.get("external-name")
        elif app.get("dns-name"):
            name = app.get("dns-name")
        # If there's no externa; configuration, forget about it!
        else:
            return

        # I wish I didn't have to do this.
        name = name.replace("." + self.handler.config.domain_base, "")

        self.handler.log("Writing {} to bind configuration".format(app.get('name')))
        self.handler.entries[name] = self.handler.config.resolve_to

