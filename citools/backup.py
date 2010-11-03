"""
Tools related to backup handling (download, restore etc.)
"""

import os
import urllib2
import tarfile
import atexit
from subprocess import check_call
from shutil import rmtree
from tempfile import mkdtemp
from ConfigParser import NoOptionError

from citools.db import Database

class Backuper(object):
    """
    Class for backup handler utils. Retrieve backup and restore it to database.
    """

    SUPPORTED_PROTOCOLS = ["http", "https"]
    CONFIG_SECTION = "backup"
    CONFIG_DB_SECTION = "database"

    def __init__(self, config):
        super(Backuper, self).__init__()

        self.config = config
        self.db_sections = []

        for s in self.config.parser.sections():
            if s.startswith(self.CONFIG_DB_SECTION):
                self.db_sections.append(s)

        if len(self.db_sections) == 0:
            raise NoOptionError("No database settings in configuration file.")

        atexit.register(self.clean_backup)


    def get_option(self, option):
        try:
            return self.config.get(self.CONFIG_SECTION, option)
        except NoOptionError:
            return None

    def get_http_backup(self, *args, **kwargs):
        return self.get_https_backup(*args, **kwargs)

    def get_https_backup(self, tmpdir):
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm=self.get_option("realm"),
                                  uri = "/".join(self.get_option("uri").split("/")[:-1]),
                                  user=self.get_option("username"),
                                  passwd=self.get_option("password"),
        )
        opener = urllib2.build_opener(auth_handler)

        file = opener.open(self.get_option("uri"))

        backupfile = os.path.join(tmpdir, self.get_option("uri").split("/")[-1])

        f = open(backupfile, "wb")
        f.writelines(file)
        f.close()

        return backupfile

    def get_backup_sql(self, file):
        backupdir = os.path.dirname(file)
        if file.endswith(".sql"):
            return file

        # determine compressed plain file
        if file.endswith("sql.gz"):
            check_call(["gzip", "-d", file])
            return file[:-3]
        if file.endswith("sql.bz2"):
            check_call(["bzip2", "-d", file])
            return file[:-4]

        # determine archive
        if file.endswith("tar.bz2"):
            flag = "r:bz2"

        elif file.endswith(".tar.gz"):
            flag = "r:gz"
        else:
            raise ValueError("File %s is not a valid archive (.tar.gz|bz2)" % file)

        db_files = []
        for s in self.db_sections:
            db_files.append(self.config.get(s, "file"))

        # uncompress
        archive = tarfile.open(file, flag)
        sqlfiles = []
        for tarinfo in archive:
            if tarinfo.name in db_files:
                archive.extract(tarinfo, backupdir)
                sqlfiles.append(os.path.join(backupdir, tarinfo.name))

        archive.close()

        if len(sqlfiles) == 0:
            raise ValueError("Backup file %s not found in archive" % self.get_option("file"))
        else:
            for f in sqlfiles:
                assert os.path.exists(f)
                assert f.endswith(".sql")

        # returns
        return sqlfiles

    def get_backup(self):
        if self.get_option('tempdir'):
            self.tmpdir = tmpdir = mkdtemp(dir=self.get_option('tempdir'))
        else:
            self.tmpdir = tmpdir = mkdtemp()
        protocol = self.get_option("uri").split(':')[0]
        if protocol not in self.SUPPORTED_PROTOCOLS:
            raise ValueError("Protocol %s not supported" % protocol)
        else:
            backupfile = getattr(self, "get_%s_backup" % protocol)(tmpdir=tmpdir)
            self.backup_files = self.get_backup_sql(backupfile)

    def clean_backup(self):
        # delete temporary dir
        rmtree(self.tmpdir, ignore_errors=True)
        return 0

    def restore_backup(self):
        db = Database(config=self.config, db_sections=self.db_sections, tmpdir=self.tmpdir)

        return db.execute_scripts()
        #return db.execute_script(self.backup_files)
