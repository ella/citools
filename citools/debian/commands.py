from __future__ import with_statement
import os
from shutil import copytree
from os.path import dirname, exists, join
from popen2 import Popen3
import re
from subprocess import check_call
from datetime import datetime

from distutils.core import Command

from citools.version import get_git_describe, compute_version, compute_meta_version, get_git_head_hash
from citools.debian.control import ControlFile, Dependency
from citools.git import fetch_repository


__all__ = (
    "BuildDebianPackage", "UpdateDebianVersion",
    "CreateDebianPackage", "CreateDebianMetaPackage",
    "CreateDebianization", "UpdateDependencyVersions",
)


def return_true(*args, **kwargs):
    return True


class BuildDebianPackage(Command):
    """ After debianization is in place, build a package for it """

    description = "run debian build wrapper dpkg-buildpackage"

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        check_call(['dpkg-buildpackage', '-rfakeroot-tcp', '-us', '-uc'])


def get_new_dependencies(dir):
    cfile = ControlFile(filename=os.path.join(dir, 'debian', 'control'))
    packages = cfile.get_packages()

    version = ".".join(map(str, compute_version(get_git_describe(repository_directory=dir, fix_environment=True))))
    for p in packages:
        p.version = version

    return packages

def fetch_new_dependencies(repository):
    repo = fetch_repository(
        repository=repository['url'], branch=repository['branch']
    )
    deps = get_new_dependencies(repo)

    return deps


def replace_versioned_packages(control_path, version, workdir=None):
    workdir = workdir or os.curdir
    cfile = ControlFile(filename=control_path)
    cfile.replace_versioned_packages(version)
    cfile.dump(control_path)

def replace_versioned_debian_files(debian_path, original_version, new_version, control_file):
    versioned_deps = control_file.get_versioned_dependencies()
    for path, dirs, files in os.walk(debian_path):
        for file in files:
            for dep in versioned_deps:
                s = "%s-%s" % (dep.name, original_version)
                if file.startswith(s):
                    f = open(os.path.join(path, file))
                    content = f.read()
                    f.close()
                    new_name = "%s-%s%s" % (dep.name, new_version, file[len(s):])

                    new_content = re.sub(original_version, new_version, content)

                    f = open(os.path.join(path, new_name), 'w')
                    f.write(new_content)
                    f.close()

                    os.remove(os.path.join(path, file))

def update_dependency_versions(repositories, control_path, workdir=None):
    """
    Update control_path (presumably debian/control) with package version collected
    by parsing debian/controls in dependencies.
    Also updates with change of my path.

    If any versioned dependencies are present, replace them too, as well as debian files
    """
    workdir = workdir or os.curdir
    cfile = ControlFile(filename=control_path)

    deps_from_repositories = []

    current_meta_version = None
    for package in cfile.get_versioned_dependencies():
        if not current_meta_version:
            current_meta_version = package.version
        else:
            assert current_meta_version == package.version, "Versioned packages with different versions, aborting"

    for repository in repositories:
        deps = fetch_new_dependencies(repository)
        deps_from_repositories.extend(deps)


    #FIXME: This will download deps again, fix it
    meta_version = compute_meta_version(repositories, workdir=workdir)
    meta_version_string = ".".join(map(str, meta_version))
    

    # also add myself as dependency
    deps = get_new_dependencies(workdir)

    # deps are my actual version; we want to update it to metaversion
    for dep in deps:
        dep.version = meta_version_string
    deps_from_repositories.extend(deps)

    cfile.replace_dependencies(deps_from_repositories)

    # if versioned packages present, replace'em
    if current_meta_version:
        replace_versioned_debian_files(debian_path=dirname(control_path), original_version=current_meta_version, new_version=meta_version_string, control_file=cfile)
        cfile.replace_versioned_packages(meta_version_string)

    cfile.dump(control_path)


class UpdateDependencyVersions(Command):

    description = "parse and update versions in debian control file"

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            update_dependency_versions(self.distribution.dependencies_git_repositories, os.path.join('debian', 'control'))
        except:
            import traceback
            traceback.print_exc()
            raise

def update_debianization(version):
    """
    Update Debian's changelog to current version and append "dummy" message.
    """
    # we need to add string version in the whole method
    if isinstance(version, (tuple, list)):
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


class UpdateDebianVersion(Command):

    description = "copy version string to debian changelog"

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """ Compute current version and update debian version accordingly """
        try:
            update_debianization(self.distribution.get_version())
        except Exception:
            import traceback
            traceback.print_exc()
            raise

class CreateDebianPackage(Command):
    description = "run what's needed to build debian package"

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

    sub_commands = [
        ("compute_version_git", None),
        ("update_debian_version", None),
        ("bdist_deb", None),
    ]



class CreateDebianMetaPackage(Command):
    description = "run what's needed to build debian meta package"

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

    sub_commands = [
        ("compute_version_meta_git", None),
        ("update_debian_version", None),
        ("update_dependency_versions", None),
        ("copy_dependency_images", None),
        ("bdist_deb", None),
    ]

def parse_setuppy_dependency(package):
    package = 'python-' + package.replace('_', '-')
    if '=' in package:
        i = package.index('=')
        offset = 0
        if package[package.rindex('=')-1] in ('<', '>', '='):
            offset = 1

        name, sign, version = package[:i-offset], package[i-offset:i+1], package[i+1:]
        return Dependency(name, version, sign)
    return Dependency(package)

def get_tzdiff(local, remote):
    '''
    little hack because of pretty bad time difference management in python
    TODO: can this solve datetime module itself?
    '''
    delta_minute = (local.hour - remote.hour) * 60 + (local.minute - remote.minute)
    sign = delta_minute < 0 and '-' or '+'
    hour = abs(delta_minute/60)
    minute = delta_minute%60
    return '%s%02d%02d' % (sign, hour, minute)

def create_debianization(distribution):
    if exists('debian'):
        raise NotImplementedError()

    # default values
    name = distribution.get_name()
    name = 'python-%s' % name.replace('_', '-').lower()

    maintainer = distribution.get_maintainer()
    maintainer_email = distribution.get_maintainer_email()
    if maintainer == 'UNKNOWN':
        maintainer = 'CH content team'
    if maintainer_email == 'UNKNOWN':
        maintainer_email = 'pg-content-dev@chconf.com'
    maintainer = '%s <%s>' % (maintainer, maintainer_email)

    version = distribution.get_version()
    if not version:
        version = '0.0.0'

    # get current date in proper format
    now = datetime.now()
    utcnow = datetime.utcnow()
    tzdiff = get_tzdiff(now, utcnow)
    nowstring = '%s %s' % (now.strftime('%a, %d %b %Y %H:%M:%S'), tzdiff)

    description = distribution.get_description()
    description = description.strip().replace('\n', '\n ')

    architecture = 'all'
    if distribution.has_ext_modules():
        architecture = 'any'

    # replace all occurences in debian template dir
    copytree(join(dirname(__file__), 'default_debianization'), 'debian')
    # do the replacement in template dir
    for root, dirs, files in os.walk('debian'):
        for f in files:
            file = join(root, f)
            with open(file) as fin:
                content = fin.read()

            for key, value in (
                ('#NAME#', name),
                ('#MAINTAINER#', maintainer),
                ('#VERSION#', version),
                ('#DATE#', nowstring),
                ):
                content = content.replace(key, value)

            with open(file, 'w') as fout:
                fout.write(content)

    # update control file
    cf = ControlFile(filename='debian/control')
    src = cf.source
    p = cf.packages[0]

    src['Source'] = p['Package'] = name
    src['Maintainer'] = maintainer
    p['Description'] = description
    p['Architecture'] = architecture

    install_requires = distribution.install_requires
    if install_requires:
        for package in install_requires:
            p['Depends'].append(parse_setuppy_dependency(package))
    cf.dump('debian/control')



class CreateDebianization(Command):
    description = "Create default debian directory containg everything needed to build a debian package."

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # TODO: build dependencies
        create_debianization(self.distribution)

