import os
from tempfile import mkstemp

from nose.tools import assert_equals

from citools.main import main
from citools.config import Configuration

class TestConfigurationLoading(object):

    def setUp(self):
        self.config = Configuration()
        self.content = """
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
        self.set_config_file(self.content)

    def set_config_file(self, content):
        handle, self.filename = mkstemp(prefix="test_citools_", suffix=".ini", text=True)
        self.file = open(self.filename, "w")
        self.file.write(content)
        self.file.close()
        self.file = open(self.filename, "r")

    def test_proper_ini_parsing(self):
        self.config.read_config(file=self.filename)

        assert_equals("xxx", self.config.get('database', 'password'))

    def test_ini_parsing_parsers_slashes(self):
        self.config.read_config(file=self.filename)

        assert_equals("centrum/backup6/tmp/stdout.sql", self.config.get('backup', 'file'))

    def test_using_specified_configuration_file(self):
        main(argv=["--config", self.filename, "validate_arguments"], config=self.config, do_exit=False)
        
        assert_equals("centrum/backup6/tmp/stdout.sql", self.config.get('backup', 'file'))

    def test_empty_validate_arguments(self):
        main(argv=["validate_arguments"], config=self.config, do_exit=False)
        # no problem should occure
        assert True

    def tearDown(self):
        if not self.file.closed:
            self.file.close()

        if os.path.exists(self.filename):
            os.remove(self.filename)
