from lxml import etree
from rnc2rng import rnctree

class ConfParse(object):
    defaults = {
        "schema": "schema.rnc",
        "config_file": "config.xml",
    }

    def __init__(self, schema=None, config_file=None):
        self.schema = schema if schema else self.defaults['schema']
        self.config_file = config_file if config_file else self.defaults['config_file']

    def parse(self):
        schema_xml = bytes(rnctree.make_nodetree(
            rnctree.token_list(
                open(self.schema).read()
            )
        ).toxml(), encoding='ascii')

        validator = etree.RelaxNG(
            etree.fromstring(schema_xml)
        )

        config = etree.parse(self.config_file)

        try:
            validator.assertValid(config)
        except etree.DocumentInvalid as ex:
            raise ValueError("Configuration error: {error}".format(error=ex))

        self.config = config.getroot()
        return config.getroot()

    def __getattr__(self, name):
        """Config is read-only so we shouldn't feel too bad about frobbing
        names and whatnot.

        Anything expecting multiple elements should not use this interface.
        """

        # Why didn't we just rename the elements in the schema?
        # Because it's {more, less} aesthetically pleasing that way.
        name_replaced = name.replace("_", "-")

        option = self.config.findall(name_replaced)

        if len(option) == 0:
            raise KeyError(name)

        if len(option) == 1:
            return option[0].text

        raise ValueError("Multiple of '{}' found".format(name))

    def all(self, *names):
        names_replaced = [name.replace("_", "-") for name in names]
        elem_lists = [self.config.findall(name) for name in names_replaced]
        elems = [elem for list in elem_lists for elem in list]

        return elems
