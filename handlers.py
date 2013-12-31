import os
import sys

import nginxparser
import pyparsing


class NginxHandler(object):
    def __init__(self, get_option):
        self.get_option = get_option
        self.nginx_path = get_option("nginx-config")
        self.domain_base = get_option("domain-base")
        if not os.path.exists(self.nginx_path):
            print "nginx configuration file", self.nginx_path, "does not exist"
            sys.exit(-1)
        self.parsed = nginxparser.load(open(self.nginx_path))
        self.names = [dict(entry[1])['server_name'].replace("." + get_option("domain-base"), "") for entry in self.parsed]

    def add(self, alias):
        print "adding {} to nginx configuration".format(alias.get('name'))
        type = alias.get('type')
        directives = [d.text.split(" ", 1) for d in alias.findall('nginx-directive')]
        if type == 'local':
            self._add(alias.get('name'),
                      directives,
                      root=self.get_option('local-root'),
                      index=alias.get('value'),
                      # rewrite='.* / last'
                      )
        elif type == 'redirect':
            self._add(alias.get('name'), directives, rewrite='.* ' + alias.get('value'))
        elif type == 'diy':
            self._add(alias.get('name'), directives)

    def _add(self, server_name, directives, **kwargs):
        kwargs['server_name'] = server_name + '.' + self.domain_base
        directives.extend(kwargs.items())
        self.parsed.append((['server'], (directives)))

    def flush(self):
        with open(self.nginx_path, 'w') as f:
            # For some reason, .dump shits all over the file
            f.write(nginxparser.dumps(self.parsed))
        print "Wrote new nginx configuration to file"

class BindHandler(object):
    comment = pyparsing.Suppress(pyparsing.Regex(";.*"))
    rr = pyparsing.Word(pyparsing.alphanums + '.-').setResultsName("key") + pyparsing.Suppress("IN") + pyparsing.Suppress("CNAME") + pyparsing.Word(pyparsing.alphanums + '.').setResultsName("value")
    line = comment ^ rr ^ pyparsing.empty
    out = "{}\tIN\tCNAME\t{}\n".format

    def __init__(self, get_option):
        self.get_option = get_option
        self.bind_config = get_option("bind-config")
        self.config = [BindHandler.line.parseString(line) for line in open(self.bind_config).readlines()]
        self.config = {r.key: r.value for r in self.config if {'key', 'value'}.symmetric_difference(r.keys()) == set()}
        self.names = self.config.keys()

    def add(self, alias):
        print "adding {} to bind configuration".format(alias.get('name'))
        type = alias.get('type')
        if type in ('local', 'redirect', 'diy'):
            self.config[alias.get('name')] = self.get_option('resolve-to')
        elif type == 'cname':
            self.config[alias.get('name')] = alias.get('value')

    def flush(self):
        output = sorted(map(lambda t: BindHandler.out(*t), self.config.items()))
        with open(self.bind_config, 'w') as f:
            f.writelines(output)
        print "Wrote new bind configuration to file"
