"""
Database handling stuff
"""

from subprocess import Popen

class Database(object):
    """
    Represents configured database backend. Wrapper to handle cases when
    Django's settings are not available.
    """

    def __init__(self, config):
        super(Database, self).__init__()

        self.backend = "mysql"
        self.username = config.get("database", "username")
        self.password = config.get("database", "password")
        self.dbname = config.get("database", "name")


    def execute_script(self, script):
        proc = Popen(' '.join([
                'mysql',
                '--user=%s'% self.username,
                '--password="%s"'% self.password,
                self.dbname,
                '<',
                script
            ]),
            shell=True
        )
        proc.communicate()
        assert proc.returncode == 0

