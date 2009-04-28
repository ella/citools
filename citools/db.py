"""
Database handling stuff
"""

import subprocess

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
        f = open(script, "r+b")
        proc = subprocess.Popen(' '.join([
                'mysql',
                '--user=%s'% self.username,
                '--password=%s'% self.password,
                self.dbname
            ]),
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        proc.stdin.writelines(f)
        proc.communicate()
        f.close()
        assert proc.returncode == 0

