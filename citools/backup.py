"""
Tools related to backup handling (download, restore etc.)
"""

import os
from subprocess import call
from shutil import rmtree
import tarfile
from tempfile import mkdtemp
import urllib2

from citools.db import Database

class Backuper(object):
    """
    Class for backup handler utils. Retrieve backup and restore it to database.
    """

    SUPPORTED_PROTOCOLS = ["http", "https"]
    CONFIG_SECTION = "backup"

    def __init__(self, config):
        super(Backuper, self).__init__()

        self.config = config

    def get_option(self, option):
        return self.config.get(self.CONFIG_SECTION, option)


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
            call(["gzip", "-d", file])
            return file[:-3]
        if file.endswith("sql.bz2"):
            call(["bzip2", "-d", file])
            return file[:-4]

        # determine archive
        if file.endswith("tar.bz2"):
            flag = "r:bz2"

        elif file.endswith(".tar.gz"):
            flag = "r:gz"
        else:
            raise ValueError("File %s is not a valid archive (.tar.gz|bz2)" % file)

        # uncompress
        archive = tarfile.open(file, flag)
        sqlfile = None
        for tarinfo in archive:
            if tarinfo.name == self.get_option("file"):
                archive.extract(tarinfo, backupdir)
                sqlfile = os.path.join(backupdir, tarinfo.name)

        archive.close()

        if not sqlfile:
            raise ValueError("Backup file %s not found in archive" % self.get_option("file"))
        else:
            assert os.path.exists(sqlfile)

        # check & returns
        if sqlfile.endswith(".sql"):
            return sqlfile
        else:
            raise ValueError("After all our backup handling, file %s do not end with sql :-(" % sqlfile)

    def get_backup(self):
        self.tmpdir = tmpdir = mkdtemp()
        protocol = self.get_option("uri").split(':')[0]
        if protocol not in self.SUPPORTED_PROTOCOLS:
            raise ValueError("Protocol %s not supported" % protocol)
        else:
            backupfile = getattr(self, "get_%s_backup" % protocol)(tmpdir=tmpdir)
            self.backup_file = self.get_backup_sql(backupfile)

    def clean_backup(self):
        # and delete temporary dir
        rmtree(self.tmpdir)
#        for file in os.listdir(self.tmpdir):
#            os.remove(os.path.join(self.tmpdir, file))
#        os.rmdir(self.tmpdir)
        return 0

    def restore_backup(self):
        db = Database(config=self.config)
        return db.execute_script(self.backup_file)
