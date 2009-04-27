"""
Config contains all function responsible for merging configuration from all
available sources back together
"""

from ConfigParser import SafeConfigParser

class Configuration(object):
    def __init__(self):
        super(Configuration, self).__init__()
        self.parser = SafeConfigParser()

    def read_config(self, file):
        self.parser.read(file)

    def get(self, *args, **kwargs):
        return self.parser.get(*args, **kwargs)

def get_config():
    return get_init_config()