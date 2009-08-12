from ConfigParser import SafeConfigParser
from tempfile import mkdtemp
import os
from subprocess import check_call, PIPE

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

