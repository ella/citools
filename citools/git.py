from subprocess import CalledProcessError
from ConfigParser import SafeConfigParser
from distutils.errors import DistutilsOptionError
from citools.mongo import get_database_connection
from tempfile import mkdtemp
import os
from subprocess import check_call, PIPE, Popen

from distutils.core import Command

def fetch_repository(repository, workdir=None, branch=None, cache_config_dir=None, cache_config_file_name="cached_repositories.ini"):
    """
    Fetch repository inside a workdir. Return filesystem path of newly created dir.
    if cache_config_dir is False, no attempt to use caching is used. If None, curdir is used, if string, it's taken as path to directory.
        If given directory is not writeable, warning is logged and fetch proceeds as if cache_config_dir would be False
    """
    write_repository_cache = False

    if cache_config_dir is not False:
        if not cache_config_dir:
            cache_config_dir = os.curdir

        if not os.path.isdir(cache_config_dir) or not os.access(cache_config_dir, os.W_OK):
            cache_config_dir = False
        else:
            cache_file_path = os.path.join(cache_config_dir, cache_config_file_name)
            parser = SafeConfigParser()
            write_repository_cache = True

            if os.path.exists(cache_file_path):
                parser.read([cache_file_path])
                if parser.has_section(repository) and parser.has_option(repository, "cache_dir"):
                    cached_repo = parser.get(repository, "cache_dir")
                    if os.path.exists(cached_repo):
                        return cached_repo

    #HACK: I'm now aware about some "generate me temporary dir name" function,
    # so I'll make this create/remove workaround - patch welcomed ,)
    dir = os.path.abspath(mkdtemp(dir=workdir))

    if not branch:
        branch="master"

    check_call(["git", "init"], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    check_call(["git", "remote", "add", "origin", repository], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    check_call(["git", "fetch"], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    check_call(["git", "checkout", "-b", branch, "origin/%s" % branch], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)

    if write_repository_cache:
        if not parser.has_section(repository):
            parser.add_section(repository)
        parser.set(repository, "cache_dir", dir)
        f = open(cache_file_path, "w")
        parser.write(f)
        f.close()

    return dir



def get_last_revision(collection):
    pass

def get_revision_metadata_property(changeset, property):
    cmd = ["git", "log", '--pretty=format:%s' % property, "%(rev)s^..%(rev)s" % {"rev" : changeset}]
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    if not proc.returncode == 0:
        raise CalledProcessError(proc.returncode, cmd)

    return stdout.strip()


def get_revision_metadata(changeset, metadata_property_map=None):
    """
    Return dictionary of metadatas defined in metadata_property_map.

    Uses slow solution (git log query per property) to avoid "delimiter inside result" problem.
    """

    metadata = {}

    metadata_property_map = metadata_property_map or {
        "%h" : "hash_abbrev",
        "%H" : "hash",
        "%aN" : "author_name",
        "%aE" : "author_email",
        "%cN" : "commiter_name",
        "%cE" : "commiter_email",
    }
    
    for property in metadata_property_map:
#        try:
        metadata[metadata_property_map[property]] = get_revision_metadata_property(changeset, property)
#        except CalledProcessError:
#            metadata[metadata_property_map[property]] = "[failed to retrieve]"
    return metadata


def retrieve_repository_metadata(changeset):
    """
    Return list of dictionaris with metadata about changesets since revision to current
    """
    proc = Popen(["git", "log", r'--pretty=format:%H', "%s.." % changeset], stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    if not proc.returncode == 0:
        raise CalledProcessError("git log failed for metadata retrieval")

    metadata = []
    hashes = stdout.splitlines()
    hashes.reverse()
    for hash in hashes:
        metadata.append(get_revision_metadata(hash))

    return metadata



def store_repository_metadata(data):
    pass

class SaveRepositoryInformationGit(Command):
    """ Store repository metadata information in mongo database for cthulhubot usage """

    description = ""

    user_options = [
        ("mongodb-host=", None, "mongo database host"),
        ("mongodb-port=", None, "mongo database port"),
        ("mongodb-username=", None, "mongo connection username"),
        ("mongodb-password=", None, "mongo connection password"),
        ("mongodb-database=", None, "mongo database name"),
        ("mongodb-collection=", None, "mongo collection to store data to"),
    ]

    def initialize_options(self):
        self.mongodb_host = None

    def finalize_options(self):
        self.mongodb_host = self.mongodb_host or "localhost"
        self.mongodb_port = self.mongodb_host or None
        self.mongodb_username = self.mongodb_username or None
        self.mongodb_password = self.mongodb_password or None

        if not self.mongodb_database:
            raise DistutilsOptionError("Mongodb database not given")

        if not self.mongodb_collection:
            raise DistutilsOptionError("Mongodb collection not given")


    def run(self):
        collection = get_database_connection(
            hostname=self.mongodb_host,
            port=self.mongodb_port,
            database=self.mongodb_database,
            username=self.mongodb_username,
            password=self.mongodb_password
        )[self.mongodb_collection]
        
        changeset = get_last_revision(collection)
        data = retrieve_repository_metadata(changeset)
        store_repository_metadata(data)

