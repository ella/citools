from tempfile import mkdtemp
import os
from subprocess import check_call, PIPE

def fetch_repository(repository, workdir=None, branch=None):
    """
    Fetch repository inside a workdir. Return filesystem path of newly created dir.
    """
    #HACK: I'm now aware about some "generate me temporary dir name function",
    # so I'll make this create/remove workaround - patch welcomed ,)
    dir = os.path.abspath(mkdtemp(dir=workdir))

    if not branch:
        branch="master"

    check_call(["git", "init"], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    check_call(["git", "remote", "add", "origin", repository], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    check_call(["git", "fetch"], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    check_call(["git", "checkout", "-b", branch, "origin/%s" % branch], cwd=dir, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    return dir

