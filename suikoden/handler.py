class HandlerMeta(type):
    def __init__(cls, name, bases, ns):
        super(HandlerMeta, cls).__init__(name, bases, ns)

        if not hasattr(cls, 'handler_classes'):
            cls.handler_classes = set()

        cls.handler_classes |= set((cls,))
        cls.handler_classes -=  set(bases)


class Handler(object, metaclass=HandlerMeta):
    whitelist = []
    blacklist = []

    def __init__(self, config, args):
        self.config = config
        self.args = args

    def _handles(self, tag):
        if len(self.whitelist) > 0:
            return tag in self.whitelist
        if len(self.blacklist) > 0:
            return tag not in self.blacklist
        return True

    def log(self, msg):
        print("[{}] {}".format(self.__class__.__name__, msg))

    @classmethod
    def instantiate(cls, *args, **kwargs):
        cls.instances = [sub(*args, **kwargs) for sub in cls.handler_classes]

        return cls.instances

    @classmethod
    def run(cls, elems):
        for elem in elems:
            for instance in cls.instances:
                if instance._handles(elem.tag):
                    if elem.get("name") not in instance.names:
                        instance.add(elem)

    @classmethod
    def flush_all(cls):
        [instance.flush() for instance in cls.instances]

    @classmethod
    def instance_by_class(cls, type):
        instances = [instance for instance in cls.instances if isinstance(instance, type)]
        if len(instances) != 1:
            raise KeyError(type)

        return instances[0]

class SubhandlerBase:
    def __init__(self, handler):
        self.handler = handler
