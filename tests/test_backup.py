# -*- coding: utf-8 -*-
import os
import tarfile
from tempfile import mkstemp, gettempdir
from subprocess import check_call

from nose.tools import assert_equals, assert_true

from citools.main import main
from citools.config import Configuration
from citools.backup import Backuper

SQL_CONTENT = """
SHOW TABLES;
"""
CONFIG_SIMPLE = """
[backup]
realm=myrealm
username=joska
password=koníček
uri=https://my.backup.server/some.db.sql

[database]
file=test_citools_backup
name=test_citools_backup
username=citools
password=""

"""
CONFIG_MULTIDB = """
[backup]
realm=myrealm
username=joska
password=pepíček
uri=https://my.backup.server/some.db.tar.gz

[database_first]
file=test_citools_bz.sql
name=test_citools_bz
username=citools
password=""

[database_second]
file=test_citools_gz.sql
name=test_citools_gz
username=citools
password=""
"""

class BackupTestCase(object):

    def setUp(self):
        self.config = Configuration()
        self.backuper = self.configfile = self.backupfile = None

    def tearDown(self):
        os.remove(self.configfile)
        try:
            os.remove(self.backupfile)
        except:
            pass


    def set_config_and_backuper(self, content):
        handle, self.configfile = mkstemp(prefix="test_citools_config_", suffix=".ini", text=True)
        f = open(self.configfile, "w")
        f.write(content)
        f.close()
        self.config.read_config(self.configfile)
        self.backuper = Backuper(self.config)

    def create_backup_file(self, content):
        handle, self.backupfile = mkstemp(prefix="test_citools_backup", suffix=".sql", text=True)
        f = open(self.backupfile, "w")
        f.write(content)
        f.close()
        return self.backupfile


class TestBackuperSimple(BackupTestCase):

    def setUp(self):
        super(TestBackuperSimple, self).setUp()
        self.set_config_and_backuper(CONFIG_SIMPLE)

    def test_get_option(self):
        assert_equals(self.backuper.get_option('password'), 'koníček')

    def test_return_none_if_option_not_exist(self):
        assert_equals(self.backuper.get_option('tempdir'), None)

    def test_db_section(self):
        assert_equals(len(self.backuper.db_sections), 1)
        assert_equals(self.backuper.db_sections[0], 'database')


class TestBackuperMulti(BackupTestCase):

    def setUp(self):
        super(TestBackuperMulti, self).setUp()
        self.set_config_and_backuper(CONFIG_MULTIDB)

    def test_db_sections(self):
        assert_equals(len(self.backuper.db_sections), 2)
        assert_true('database_second' in self.backuper.db_sections)


class TestGzipSql(BackupTestCase):

    def setUp(self):
        super(TestGzipSql, self).setUp()
        self.set_config_and_backuper(CONFIG_SIMPLE)
        self.create_backup_file(SQL_CONTENT)

    def tearDown(self):
        super(TestGzipSql, self).tearDown()
        os.remove("%s.gz" % self.backupfile)

    def create_backup_file(self, content):
        super(TestGzipSql, self).create_backup_file(content)
        check_call(['gzip', self.backupfile])

    def test_get_backup_from_file(self):
        sqlfile = self.backuper.get_backup_sql(self.backupfile)
        assert_equals(sqlfile, self.backupfile)


class TestBzipSql(BackupTestCase):

    def setUp(self):
        super(TestBzipSql, self).setUp()
        self.set_config_and_backuper(CONFIG_SIMPLE)
        self.create_backup_file(SQL_CONTENT)

    def tearDown(self):
        super(TestBzipSql, self).tearDown()
        os.remove("%s.bz2" % self.backupfile)

    def create_backup_file(self, content):
        super(TestBzipSql, self).create_backup_file(content)
        check_call(['bzip2', self.backupfile])

    def test_get_backup_from_file(self):
        sqlfile = self.backuper.get_backup_sql(self.backupfile)
        assert_equals(sqlfile, self.backupfile)


class TestPlainSql(BackupTestCase):

    def setUp(self):
        super(TestPlainSql, self).setUp()
        self.set_config_and_backuper(CONFIG_SIMPLE)
        self.create_backup_file(SQL_CONTENT)

    def test_get_backup_from_file(self):
        sqlfile = self.backuper.get_backup_sql(self.backupfile)
        assert_equals(sqlfile, self.backupfile)


#class TestMultiDbTar(BackupTestCase):
#
#    def setUp(self):
#        super(TestMultiDbTar, self).setUp()
#        self.set_config_and_backuper(CONFIG_MULTIDB)
#        self.create_backup_file(SQL_CONTENT)
#
#    def tearDown(self):
#        super(TestMultiDbTar, self).tearDown()
#        os.remove(self.backup1)
#        os.remove(self.backup2)
#
#    def create_backup_file(self, content):
#        self.backup1 = super(TestMultiDbTar, self).create_backup_file(content)
#        self.backup2 = super(TestMultiDbTar, self).create_backup_file(content)
#        bf = "%s/test_citools_backup.tar" % gettempdir()
#        check_call(['tar', '-cf', bf, self.backup1, self.backup2])
#        check_call(['gzip', bf])
#        self.backupfile = "%s.gz" % bf
#
#    def test_get_backup_from_file(self):
#        sqlfiles = self.backuper.get_backup_sql(self.backupfile)
#        assert_equals(sqlfiles, self.backupfile)
