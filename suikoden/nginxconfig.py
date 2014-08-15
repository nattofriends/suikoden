# -*- coding: utf-8 -*-

from functools import reduce
from operator import add
from string import ascii_letters, digits, punctuation

import funcparserlib.parser as p
from namedlist import namedlist


class Directive(namedlist('Directive', ['name', 'contents'])):
    def emit_nginx(self, indent):
        return "{indent}{name} {contents};\n".format(
            indent=' ' * indent * 4,
            name=self.name,
            contents=' '.join(self.contents),
        )

    @property
    def content_string(self):
        return ' '.join(self.contents)

class Block(namedlist('Block', ['name', 'block_arguments', 'directives'])):
    def emit_nginx(self, indent):
        block_str = ''
        if self.block_arguments:
            block_str = ' '.join(self.block_arguments) + ' '
        return "{indent}{name} {block_str}{{\n{directives}{indent}}}\n".format(
            indent=' ' * indent * 4,
            name=self.name,
            block_str=block_str,
            directives=''.join([d.emit_nginx(indent + 1) for d in self.directives]),
        )

    def find_directive(self, name, silent=False):
        """Find all directives in this block called name."""
        directives = [directive for directive in self.directives if directive.name == name]

        if len(directives) == 0:
            if silent:
                return None
            else:
                raise KeyError(name)
        if len(directives) == 1:
            return directives[0]
        return directives

    def get_comments(self):
        """Caller has to do the legwork here."""
        return [directive for directive in self.directives if isinstance(directive, Comment)]

class Configuration(namedlist('Configuration', ['elements'])):
    def emit_nginx(self):
        result = ""
        for thing in self.elements:
            result += thing.emit_nginx(0)
        return result

    def find_by_type(self, type):
        """Get root elements by type."""
        return [elem for elem in self.elements if isinstance(elem, type)]


class Comment(namedlist('Comment', ['content'])):
    """Comments on their own lines are preserved. Others are not."""
    def emit_nginx(self, indent):
        return "{indent}#{content}\n".format(
            indent=' ' * indent * 4,
            content=self.content
        )

    @property
    def name(self):
        """Throw 'em off!"""
        return None

class NginxConfigParser:
    identifier_letters = list(ascii_letters) + ['_']
    value_letters = set(ascii_letters + digits + punctuation) - set(';{}')  # What if this is in a string?
    everything_else = set(map(chr, list(range(0, 256)))) - set('\n')

    char = lambda ch: p.skip(p.a(ch))
    skaby = lambda what: p.skip(p.maybe(what))
    add_all = lambda to_add: reduce(add, to_add)
    skip_all = lambda to_skip: p.skip(p.maybe(p.many(p.some(lambda ch: ch in to_skip))))
    filter_ignore = lambda items: [item for item in items if not isinstance(item, p._Ignored)]

    semi = p.skip(p.a(';'))
    whitespace = skip_all(' \t\n')

    identifier = p.oneplus(p.some(lambda ch: ch in NginxConfigParser.identifier_letters)) + whitespace >> (lambda letters: ''.join(letters))
    value = p.oneplus(p.some(lambda ch: ch in NginxConfigParser.value_letters)) + whitespace >> (lambda letters: ''.join(letters))
    values = p.maybe(p.oneplus(value))

    comment = p.a('#') + p.many(p.some(lambda ch: ch not in '#\n')) >> (lambda things: Comment(''.join(things[1])))

    block = p.forward_decl()
    directive = whitespace + identifier + values + whitespace + semi + whitespace + skaby(comment) + whitespace >> (lambda things: Directive(*things))
    directives_or_blocks = p.oneplus(directive | block | whitespace + comment)

    block.define(
        add_all([
            whitespace,

            identifier,
            values,

            char('{'),
            whitespace,

            directives_or_blocks,

            whitespace,
            char('}'),
            whitespace
        ]) >> (lambda things: Block(*things))
    )

    things = whitespace + p.many(block | directive | comment) + p.skip(p.finished) >> (lambda things: Configuration(things))

    def parse(self, config):
        parsed_things = self.things.parse(config)
        return parsed_things

