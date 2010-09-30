"""
Database handling stuff
"""

from subprocess import Popen
from ConfigParser import NoOptionError


class Database(object):
    """
    Represents configured database backend. Wrapper to handle cases when
    Django's settings are not available.
    """

    CONFIG_DB_SECTION = "database"

    def __init__(self, config, db_sections=[], tmpdir=''):
        super(Database, self).__init__()

        self.config = config
        self.tmpdir = tmpdir

        self.dbs = {}
        for s in db_sections:
            self.dbs[s] = {}
            self.dbs[s]['dbname'] = config.get(s, 'name')
            self.dbs[s]['username'] = config.get(s, 'username')
            self.dbs[s]['password'] = config.get(s, 'password')
            try:
                self.dbs[s]['file'] = config.get(s, 'file')
            except NoOptionError, e:
                self.dbs[s]['file'] = "%s.sql" % config.get(s, 'name')

    def execute_scripts(self):
        for s in self.dbs.keys():
            self.execute_script(self.dbs[s])

    def execute_script(self, section):
        proc = Popen(' '.join([
                'mysql',
                '--user=%s' % section['username'],
                '--password="%s"' % section['password'],
                section['dbname'],
                '<',
                "%s/%s" % (self.tmpdir, section['file'])
            ]),
            shell=True
        )
        proc.communicate()
        assert proc.returncode == 0

