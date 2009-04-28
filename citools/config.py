"""
Config contains all function responsible for merging configuration from all
available sources back together
"""

from ConfigParser import SafeConfigParser

class Configuration(object):

    # specify which commands from namespace
    # maps to what section/arg in configuration
    NAMESPACE_CONFIG_MAP = {
    }

    def __init__(self):
        super(Configuration, self).__init__()
        self.parser = SafeConfigParser()
        self.command = None

    def read_config(self, file):
        self.parser.read(file)

    def get(self, *args, **kwargs):
        return self.parser.get(*args, **kwargs)

    def merge_with_cmd(self, namespace):
        kwargs = namespace._get_kwargs()
        for key in self.NAMESPACE_CONFIG_MAP:
            if key in kwargs and kwargs[key]:
                section, option = kwargs[key]
                self.parser.set(section, option)

