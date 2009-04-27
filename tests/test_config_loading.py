import os
from tempfile import mkstemp

from nose.tools import assert_equals

from citools.config import Configuration

class TestConfigurationFileLoading(object):

    def setUp(self):
        self.config = Configuration()

    def set_config_file(self, content):
        handle, self.filename = mkstemp(prefix="test_citools_", suffix=".ini", text=True)
        self.file = open(self.filename, "w")
        self.file.write(content)
        self.file.close()
        self.file = open(self.filename, "r")

    def test_proper_parsing(self):
        content = """
[backup]
protocol=ftp
username=blah
password=xxx
file=centrum/backup6/tmp/stdout.sql

[database]
name=stdout
username=buildbot
password=xxx
"""
        self.set_config_file(content)
        self.config.read_config(file=self.filename)

        assert_equals("xxx", self.config.get('database', 'password'))
        assert_equals("centrum/backup6/tmp/stdout.sql", self.config.get('backup', 'file'))

    def tear_down(self):
        if not self.file.closed:
            self.file.close()

        if os.file.exists(self.filename):
            os.remove(self.filename)


class TestConfigurationOptionsParsing(object):
    pass