from __future__ import with_statement
import os
from shutil import copytree
from os.path import dirname, exists, join
import re
from subprocess import check_call, Popen, PIPE
from datetime import datetime

from distutils.core import Command

from citools.build import ReplaceTemplateFiles, RenameTemplateFiles
from citools.debian.control import ControlFile, Dependency
from citools.git import fetch_repository
from citools.version import get_git_describe, compute_version, compute_meta_version, get_git_head_hash, retrieve_current_branch


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


def get_new_dependencies(dir, accepted_tag_pattern=None, branch="master"):
    
    version = compute_version(get_git_describe(repository_directory=dir, fix_environment=True, accepted_tag_pattern=accepted_tag_pattern))
    control = os.path.join(dir, 'debian', 'control')

    version = ".".join(map(str, version))
    
    ### FIXME: We shall not do this again AND should only use templates
    from citools.build import replace_template_files
    replace_template_files(root_directory=dir, variables={
        'branch' : branch,
        'version' : version,
    })

    
    cfile = ControlFile(filename=control)
    packages = cfile.get_packages()

    for p in packages:
        p.version = version

    return packages

def fetch_new_dependencies(repository, workdir=None):
    if repository.has_key('branch'):
        branch = repository['branch']
    else:
        if workdir:
            branch = retrieve_current_branch(repository_directory=workdir, fix_environment=True)
        else:
            branch = retrieve_current_branch()
    repo = fetch_repository(
        repository=repository['url'], branch=branch
    )
    #FIXME: This should not be hardcoded
    project_pattern = "%s-[0-9]*" % repository['package_name']
    
    deps = get_new_dependencies(repo, accepted_tag_pattern=project_pattern, branch=branch)

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

def update_dependency_versions(repositories, control_path, workdir=None, accepted_tag_pattern=None):
    """
    Update control_path (presumably debian/control) with package version collected
    by parsing debian/controls in dependencies.
    Also updates with change of my path.

    If any versioned dependencies are present, replace them too, as well as debian files
    """
    workdir = workdir or os.curdir
    cfile = ControlFile(filename=control_path)

    deps_from_repositories = []

    cfile_meta_version = '0.0.0.0'

    for repository in repositories:
        deps = fetch_new_dependencies(repository, workdir)
        deps_from_repositories.extend(deps)

    #FIXME: This will download deps again, fix it
    meta_version = compute_meta_version(repositories, workdir=workdir, accepted_tag_pattern=accepted_tag_pattern)
    meta_version_string = ".".join(map(str, meta_version))
    

    # also add myself as dependency
    deps = get_new_dependencies(workdir, accepted_tag_pattern=accepted_tag_pattern)

    # deps are my actual version; we want to update it to metaversion
    for dep in deps:
        dep.version = meta_version_string
    deps_from_repositories.extend(deps)

    cfile.replace_dependencies(deps_from_repositories)

    replace_versioned_debian_files(debian_path=dirname(control_path), original_version=cfile_meta_version, new_version=meta_version_string, control_file=cfile)
    cfile.replace_versioned_packages(meta_version_string, old_version=cfile_meta_version)

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
            format = "%s-[0-9]*" % self.distribution.metadata.get_name()
            update_dependency_versions(self.distribution.dependencies_git_repositories, os.path.join('debian', 'control'), accepted_tag_pattern=format)
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

    proc = Popen(['dch', '--changelog', changelog, '--newversion', version, '"%s"' % message], stdout=PIPE)

    return_code = proc.wait()
    if return_code == 0:
        return proc.stdout.read().strip()
    else:
        raise ValueError("Updating debianization failed with exit code %s" % return_code)


def get_packages_names():
    control = os.path.join('debian', 'control')
    if not os.path.exists(control):
        raise ValueError("Cannot find debian/control")
    packages = []
    version_pattern = re.compile("^(Package\:){1}(\s)*(?P<name>[\w\-\.]+).*(\s)*$")
    for line in open(control, 'r'):
        match = re.match(version_pattern, line)
        if match:
            packages.append(match.groupdict()['name'])
    return packages


def get_package_path(package_name, module_name, current_version=None):
    """ Return filesystem path to debian package build by bdist_deb"""
    if not current_version:
        #FIXME: not to hardcode
        format = "%s-[0-9]*" % module_name
        current_version = '.'.join(map(str, compute_version(get_git_describe(accepted_tag_pattern=format))))
    package_name = u"%(name)s_%(version)s_%(arch)s.deb" % {
        'name' : package_name,
        'version' : current_version,
        'arch' : 'all'
    }
    return os.path.normpath(os.path.join(os.curdir, os.pardir, package_name))



class UpdateDebianVersion(Command):

    description = "copy version string to debian changelog"

    user_options = [
        ('build-number=', None, "Provide a buildnumber for auto-computed version"),
    ]

    def initialize_options(self):
        self.build_number = None

    def finalize_options(self):
        pass

    def run(self):
        """ Compute current version and update debian version accordingly """
        version = self.distribution.get_version()
        if self.build_number:
            version = '%s-%s' % (version, self.build_number)
        try:
            update_debianization(version)
        except Exception:
            import traceback
            traceback.print_exc()
            raise

class CreateDebianPackage(Command):
    description = "run what's needed to build debian package"

    user_options = [
        ('build-number=', None, "Provide a buildnumber for auto-computed version"),
    ]

    def initialize_options(self):
        self.build_number = None

    def finalize_options(self):
        pass

    def run(self):
        for cmd_name in self.get_sub_commands():
            sub_cmd = self.reinitialize_command(cmd_name)
            sub_cmd.build_number = self.build_number
            self.run_command(cmd_name)

    sub_commands = [
        ("compute_version_git", None),
        ("replace_templates", None),
        ("rename_template_files", None),
        ("update_debian_version", None),
        ("bdist_deb", None),
    ]



class CreateDebianMetaPackage(Command):
    description = "run what's needed to build debian meta package"

    user_options = [
        ('build-number=', None, "Provide a buildnumber for auto-computed version"),
    ]

    def initialize_options(self):
        self.build_number = None

    def finalize_options(self):
        pass

    def run(self):
        for cmd_name in self.get_sub_commands():
            sub_cmd = self.reinitialize_command(cmd_name)
            sub_cmd.build_number = self.build_number
            self.run_command(cmd_name)

    sub_commands = [
        ("compute_version_meta_git", None),
        ("replace_templates", None),
        ("rename_template_files", None),
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

