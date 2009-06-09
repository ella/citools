from distutils.command.config import config
import re
import os
from popen2 import Popen3
from shutil import rmtree
from subprocess import check_call, PIPE
from tempfile import mkdtemp


"""
Help us handle continuous versioning. Idea is simple: We have n-number digits
version (in form 1.2(.3...).n), where number of 1...(n-1) must appear in tag.

n is then computed as number-of-commits since last version-setting tag (and we're
using git describe for it now)
"""

def compute_version(string):
    """ Return VERSION tuple, computed from git describe output """
    match = re.match("(?P<bordel>[a-z0-9\-\_]*)(?P<arch>\d\.\d{1})(?P<rest>.*)", string)

    if not match or not match.groupdict().has_key('arch'):
        raise ValueError(u"Something appears to be a scheme version, but it's not; failing")

    version = match.groupdict()['arch']

    if match.groupdict().has_key('rest') and match.groupdict()['rest']:
        staging = re.findall("(\.\d+)", match.groupdict()['rest'])
        version = ''.join([version]+staging)


    # we're using integer version numbers instead of string
    build_match = re.match(".*(%(version)s){1}.*\-{1}(?P<build>\d+)\-{1}g{1}[0-9a-f]{7}" % {'version' : version}, string)

    if not build_match or not build_match.groupdict().has_key('build'):
        # if version is 0.0....
        if re.match("^0(\.0)+$", version):
            # return 0.0.1 instead of 0.0.0, as "ground zero version" is not what we want
            build = 1
        else:
            build = 0
    else:
        build = int(build_match.groupdict()['build'])

    return tuple(list(map(int, version.split(".")))+[build])

def sum_versions(version1, version2):
    """
    Return sum of both versions. Raise ValueError when negative number met
    i.e.:
    (0, 2) = (0, 1) + (0, 1)
    (1, 23, 12) = (0, 2, 12) + (1, 21)
    """
    final_version = [int(i) for i in version1 if int(i) >= 0]

    if len(final_version) != len(version1):
        raise ValueError("Negative number in version number not allowed")

    position = 0
    for part in version2:
        if int(part) < 0:
            raise ValueError("Negative number in version number not allowed")
        if len(final_version) < position+1:
            final_version.append(part)
        else:
            final_version[position] += part
        position += 1
    return tuple(final_version)

def get_git_describe(fix_environment=False, repository_directory=None):
    """ Return output of git describe. If no tag found, initial version is considered to be 0.0.1 """
    if repository_directory and not fix_environment:
        raise ValueError("Both fix_environment and repository_directory or none of them must be given")
    
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
    version_regexp = re.compile(r"^(VERSION){1}(\ )+(\=){1}(\ )+\({1}([0-9])+(\,{1}(\ )*[0-9]+)+(\)){1}")

    for line in source_file:
        if version_regexp.match(line):
            content.append('VERSION = %s\n' % str(version))
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
    file = os.path.join(name, '__init__.py')
    replace_version_in_file(version, file)

def replace_version_in_file(version, file):
    """ Update VERSION attribute in $name/__init__.py module """
    file = open(file, 'r')
    content = replace_version(version=version, source_file=file)
    file.close()
    file = open(file.name, 'wb')
    file.writelines(content)
    file.close()

def fetch_repository(repository, workdir, branch=None):
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

def compute_meta_version(dependency_repositories):
    version = compute_version(get_git_describe())
    repositories_dir = mkdtemp(dir=os.curdir, prefix="build-repository-dependencies-")
    for repository_dict in dependency_repositories:
        if repository_dict.has_key('branch'):
            branch = repository_dict['branch']
        else:
            branch = None
        workdir = fetch_repository(repository_dict['url'], branch=branch, workdir=repositories_dir)
        new_version = compute_version(get_git_describe(repository_directory=workdir, fix_environment=True))
        version = sum_versions(version, new_version)
    rmtree(repositories_dir)
    return version

class GitSetMetaVersion(config):
    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """
        Clone all dependencies into temporary directory. Collect all git_set_versions for all
        packages (including myself).
        Update on all places as in git_set_version.
        """
        try:
            meta_version = compute_meta_version(self.distribution.dependencies_git_repositories)
            replace_init(meta_version, self.distribution.get_name())
            replace_version_in_file(meta_version, 'setup.py')
            version_str = '.'.join(map(str, meta_version))
            self.distribution.version = version_str
            
            print "Current version is %s" % '.'.join(map(str, meta_version))
        except Exception:
            import traceback
            traceback.print_exc()
            raise

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
        Because of line endings, should be not run on Windows."""
        try:
            current_git_version = get_git_describe()
            version = compute_version(current_git_version)
            replace_init(version, self.distribution.get_name())
            version_str = '.'.join(map(str, current_git_version))
            self.distribution.version = version_str
            print "Current version is %s" % version_str
        except Exception:
            import traceback
            traceback.print_exc()
            raise

class UpdateDebianVersion(config):
    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """ Compute current version and update debian version accordingly """
        try:
            update_debianization(self.distribution.version)
        except Exception:
            import traceback
            traceback.print_exc()
            raise

def validate_repositories(dist, attr, value):
    # TODO: 
    # http://peak.telecommunity.com/DevCenter/setuptools#adding-setup-arguments
    pass

