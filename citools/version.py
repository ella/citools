from distutils.command.config import config

import re
import os
from popen2 import Popen3

def get_version(string):
    """ Return VERSION tuple, computed from git describe output """
    match = re.match(".*(?P<schema_version>\d+\.\d+).*", string)

    if not match or not match.groupdict().has_key('schema_version'):
        raise ValueError(u"No schema version identified")

    # we're using integer version numbers instead of string
    arch, major = [int(i) for i in match.groupdict()['schema_version'].split('.')]
    minor_match = re.match(".*(%(arch)s){1}\.{1}(%(major)s){1}.*\-{1}(?P<minor>\d+)\-{1}g{1}[0-9a-f]{7}" % {'arch' : arch, 'major' : major}, string)

    if not minor_match or not minor_match.groupdict().has_key('minor'):
        if arch == 0 and major == 0:
            # we're building first release at all, and 0.0.0 would be...not so appealng, so let's do an exception
            return (0, 0, 1)
        else:
            # otherwise, it looks like we're on tag, so this is the 'zero' version
            return (arch, major, 0)
    else:
        # number of commits since tag
        return (arch, major, int(minor_match.groupdict()['minor']))

def get_git_describe(fix_environment=False, repository_directory=None):
    """ Return output of git describe. If no tag found, initial version is considered to be 0.0.1 """
    if fix_environment:
        if not repository_directory:
            raise ValueError(u"Cannot fix environment when repository directory not given")
        env_git_dir = None
        if os.environ.has_key('GIT_DIR'):
            env_git_dir = os.environ['GIT_DIR']

        os.environ['GIT_DIR'] = os.path.join(repository_directory, '.git')

    try:
        proc = Popen3("git describe", capturestderr=True)
        return_code = proc.wait()
        if return_code == 0:
            return proc.fromchild.read().strip()

        elif return_code == 32768:
            # git describe failed as there is no tag in repository
            # strangely, $? returns 128, but is represented like this in Python...
            return '0.0'

        else:
            raise ValueError("Unknown return code %s" % return_code)

    finally:
        if fix_environment:
            if env_git_dir:
                os.environ['GIT_DIR'] = env_git_dir
            else:
                del os.environ['GIT_DIR']

def replace_version(source_file, version):
    content = []
    version_regexp = re.compile(r"^(VERSION){1}(\ )+(\=){1}(\ )+(\(){1}([0-9])+(\,){1}(\ )+([0-9])+(\,){1}(\ )+([0-9])+(\)){1}")

    for line in source_file:
        if version_regexp.match(line):
            content.append('VERSION = (%d, %d, %d)\n' % version)
        else:
            content.append(line)
    return content

def get_git_head_hash(fix_environment=False, repository_directory=None):
    """ Return output of git describe. If no tag found, initial version is considered to be 0.0.1 """
    if fix_environment:
        if not repository_directory:
            raise ValueError(u"Cannot fix environment when repository directory not given")
        env_git_dir = None
        if os.environ.has_key('GIT_DIR'):
            env_git_dir = os.environ['GIT_DIR']

        os.environ['GIT_DIR'] = os.path.join(repository_directory, '.git')

    try:
        proc = Popen3("git rev-parse HEAD")
        return_code = proc.wait()
        if return_code == 0:
            return proc.fromchild.read().strip()
        else:
            raise ValueError("Non-zero return code %s from git log" % return_code)

    finally:
        if fix_environment:
            if env_git_dir:
                os.environ['GIT_DIR'] = env_git_dir
            else:
                del os.environ['GIT_DIR']


def update_debianization(version):
    """
    Update Debian's changelog to current version and append "dummy" message.
    """
    # we need to add string version in the whole method
    version = '.'.join(map(str, version))
    changelog = 'debian/changelog'
    hash = get_git_head_hash()
    message = "Version %(version)s was build from revision %(hash)s by automated build system" % {
                      'version' : version,
                      'hash' : hash
    }

    proc = Popen3('dch --changelog %(changelog)s --newversion %(version)s "%(message)s"' % {
                 'changelog' : changelog,
                 'version' : version,
                 'message' : message,
           })

    return_code = proc.wait()
    if return_code == 0:
        return proc.fromchild.read().strip()
    else:
        raise ValueError("Updating debianization failed with exit code %s" % return_code)

def replace_init(version, name):
    """ Update VERSION attribute in $name/__init__.py module """
    file = open(os.path.join(name, '__init__.py'), 'r')
    content = replace_version(version=version, source_file=file)
    file.close()
    file = open(file.name, 'wb')
    file.writelines(content)
    file.close()

class GitSetVersion(config):
    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """ Compute current version for tag and git describe. Expects VERSION variable to be stored in
        $name/__init__.py file (relatively placed to $cwd.) and to be a tuple of three integers.
        Because of line endings, should be not run on Windows or ending mismatches might occur."""
        try:
            current_git_version = get_git_describe()
            version = get_version(current_git_version)
            replace_init(version, self.distribution.get_name())
            update_debianization(version)
            print "Current version is %s" % '.'.join(map(str, version))
        except Exception:
            import traceback
            traceback.print_exc()
            raise
