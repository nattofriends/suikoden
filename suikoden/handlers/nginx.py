import re
from copy import copy

from ..handler import Handler
from ..handler import SubhandlerBase
from ..nginxconfig import Block
from ..nginxconfig import Comment
from ..nginxconfig import Directive
from ..nginxconfig import NginxConfigParser

class NginxHandler(Handler):

    def __init__(self, *args, **kwargs):
        super(NginxHandler, self).__init__(*args, **kwargs)

        self.nginx_path = self.config.nginx_config
        self.domain_base = self.config.domain_base

        self._init_subhandlers()

        parser = NginxConfigParser()
        self.parsed = parser.parse(open(self.nginx_path).read())

        blocks = self.parsed.find_by_type(Block)
        self.names = []
        if self.args.force:
            # Gotta clear them out.
            del self.parsed.elements[:]
        else:
            for handler in self.subhandlers.values():
                self.names += handler.get_names(blocks)

    def _init_subhandlers(self):
        self.subhandlers = {
            'app': NginxAppHandler(self),
            'alias': NginxAliasHandler(self),
        }

    def add(self, elem):
        self.subhandlers[elem.tag].add(elem)

    def flush(self):
        with open(self.nginx_path, 'w') as f:
            f.write(self.parsed.emit_nginx())


class NginxAliasHandler(SubhandlerBase):

    def add(self, alias):
        server_directives = [d.text.split(" ", 1) for d in alias.findall('nginx-directive')]
        server_directives = [Directive(name, [values]) for name, values in server_directives]

        server_directives.extend([
            Directive("listen", ["80"]),
            Directive("listen", ["443 ssl spdy"]),
            Block("if", ["($scheme = http)"], [
                Directive("return", ["301 https://$host$request_uri"]),
            ]),
        ])

        type = alias.get('type')
        if type == 'local':
            self._add(
                alias.get('name'),
                server_directives,
                root=self.handler.config.local_root,
                index=alias.get('value'),
            )
        elif type == 'redirect':
            self._add(alias.get('name'), server_directives, rewrite='.* ' + alias.get('value'))
        elif type == 'diy':
            self._add(alias.get('name'), server_directives)
        else:  # cname
            pass

    def _add(self, server_name, directives, **kwargs):
        self.handler.log("Writing {} to nginx configuration".format(server_name))

        kwargs['server_name'] = server_name + '.' + self.handler.domain_base
        directives.extend([Directive(name=name, contents=[values]) for name, values in list(kwargs.items())])

        block = Block(name='server', directives=directives, block_arguments=None)
        self.handler.parsed.elements.append(block)

    def get_names(self, blocks):
        # What a shitty test. If it has a location / block it is an app,
        # otherwise an alias.

        has_location = [block.find_directive('location', silent=True) for block in blocks]
        location_blocks = zip(blocks, has_location)
        location_blocks = [block for block, has_location in location_blocks if not has_location]
        name_directives = [block.find_directive('server_name') for block in location_blocks]
        names = [directive.content_string.replace("." + self.handler.domain_base, "") for directive in name_directives]
        return names


class NginxAppHandler(SubhandlerBase):

    proxy_block_prototype = Block(
        name='location',
        block_arguments='/',
        directives=None
    )

    def get_names(self, blocks):
        # What a shitty test. If it has a location / block it is an app,
        # otherwise an alias.
        # TODO: Need to handle the case of merging blocks with the same server_name
        # but no comment name. Or do we?

        has_location = [block.find_directive('location', silent=True) for block in blocks]
        location_blocks = zip(blocks, has_location)
        location_blocks = [block for block, has_location in location_blocks if has_location]
        comment_directives = [comment.content.strip() for block in location_blocks for comment in block.get_comments()]
        comment_matches = [re.match("name:(.*)", comment) for comment in comment_directives]
        comments = [m.group(1) for m in comment_matches if m]

        return comments

    def add(self, app):
        def parse_directives(node, toplevel=False):
            directives = [d.text.split(" ", 1) for d in node.findall('nginx-directive')]
            directives = [Directive(name, [values]) for name, values in directives]

            if not toplevel:
                directives.extend(parse_blocks(node))

            return directives

        def parse_blocks(node):
            blocks = node.findall('nginx-block')
            blocks = [Block(
                name=block.get('name'),
                block_arguments=[block.get('arguments')] if block.get('arguments') else [],
                directives=parse_directives(block)
            ) for block in blocks]
            return blocks

        if app.get("external-name") and app.get("http-name"):
            raise ValueError("Cannot define both external-name and http-name")
        if not bool(app.get("http-name")) == bool(app.get("dns-name")):
            raise ValueError("Only one service-name defined")

        directives = [Comment(content=" name:{}".format(app.get("name")))]
        directives.extend(parse_directives(app, toplevel=True))
        directives.extend(parse_blocks(app))

        if app.get("external-name"):
            directives.append(Directive(name='server_name', contents=[app.get("external-name")]))
        if app.get("http-name"):
            directives.append(Directive(name='server_name', contents=[app.get("http-name")]))

        self.handler.log('Writing {} to nginx configuration'.format(app.get("name")))
        # Construct the proxy pass block.
        proxy_pass = Directive(name='proxy_pass', contents=['http://127.0.0.1:{}'.format(app.get('port'))])

        root_location_blocks = [directive for directive in directives \
                                if isinstance(directive, Block) \
                                and directive.name == 'location' \
                                and directive.block_arguments == ['/']
        ]

        if len(root_location_blocks) > 1:
            raise ValueError("Please condense your location /s.")
        if len(root_location_blocks) == 1:
            root_location_blocks[0].directives.append(proxy_pass)
        else:
            proxy_block = copy(self.proxy_block_prototype)
            proxy_block.directives = [proxy_pass]
            directives.append(proxy_block)

        server_block = Block(name='server', directives=directives, block_arguments=None)
        self.handler.parsed.elements.append(server_block)
