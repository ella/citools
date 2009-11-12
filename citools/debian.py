import os
from os.path import dirname
from popen2 import Popen3
import re
from shutil import rmtree
from subprocess import check_call

from distutils.core import Command
from citools.version import get_git_describe, compute_version, compute_meta_version, get_git_head_hash

from os import walk
from citools.git import fetch_repository


__all__ = (
    "Dependency", "ControlParser",
    "BuildDebianPackage", "UpdateDebianVersion"
    "CreateDebianPackage", "CreateDebianMetaPackage",
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
        check_call(['dpkg-buildpackage', '-rfakeroot', '-us', '-uc'])


class Dependency(object):
    """
    Dependency in the debian package
    """

    LINE_PATTERN = "(?P<name>[a-z0-9\-]+)(?P<version>\ \([\=\>\<]+\ [0-9\-\.]+\))?"

    def __init__(self, name, version=None, sign=None):
        super(Dependency, self).__init__()
        
        self.name = name
        self.version = version
        self.sign = sign

        if not self.sign and version:
            self.sign = u'='

    def is_versioned(self):
        return False

    def get_dependency_string(self):
        if self.version:
            return u"%(name)s (%(sign)s %(version)s)" % {
                'name' : self.name,
                'version' : self.version,
                'sign' : self.sign or '=',
            }
        else:
            return self.name

    def extract_version_from_debversion(self, debversion):
        version = re.match("\ ?\((?P<sign>[\=\>\<]+)\ (?P<version>[0-9\-\.]+)\)", debversion)
        if version and version.groupdict().has_key('sign') \
            and version.groupdict().has_key('version'):

            self.version = version.groupdict()['version']
            self.sign = version.groupdict()['sign']

    def update_version(self, version_candidate):
        """
        Update my version if I'm allowed to do that
        """
        if self.sign == '=':
            self.version = version_candidate

    def __str__(self):
        return u"%(name)s: %(version)s" % {
            'name' : self.name,
            'version' : self.version or '<unspecified>',
        }

class VersionedDependency(Dependency):
    """
    Versioned dependency. Unlike Dependency, it includes version into package name,
    not in parenthesis.

    This is hack around Debian absence of slots.
    """

    LINE_PATTERN = "(?P<name>[a-z0-9\-]+)\-(?P<version>[0-9\-\.]+)"

    def get_dependency_string(self):
        return u"%(name)s-%(version)s" % {
            'name' : self.name,
            'version' : self.version,
        }

    def is_versioned(self):
        return True

    def extract_version_from_debversion(self, debversion):
        version = re.match("(?P<version>[0-9\-\.]+)", debversion)
        if version and version.groupdict().has_key('version'):
            self.version = version.groupdict()['version']

    def update_version(self, version_candidate):
        self.version = version_candidate

class Package(object):
    def __init__(self, name, version=None):
        super(Package, self).__init__()

        self.name = name
        self.version = version

    def get_full_name(self):
        if self.version:
            return "%s-%s" % (self.name, self.version)
        else:
            return self.name

    def __str__(self):
        return self.full_name

    def get_package_string(self):
        return self.get_full_name()

    full_name = property(fget=get_full_name)

class ControlParser(object):
    """
    Parser for debian/control files
    """
    def __init__(self, control_file):
        super(ControlParser, self).__init__()

        self.control_file = control_file

    def parse_dependency_line(self, line):
        """ Return dependency from Depends: line """
        AVAILABLE_DEPS = [VersionedDependency, Dependency]
        line = line[len("Depends:"):]
        dependencies = []
        dependency_candidates = line.split(",")
        for candidate in dependency_candidates:
            for klass in AVAILABLE_DEPS:
                deps = re.findall(klass.LINE_PATTERN, candidate)
                for dep in deps:
                    new_dep = klass(dep[0])
                    if dep[1]:
                        new_dep.extract_version_from_debversion(dep[1])
                    dependencies.append(new_dep)
                if deps:
                    break
        return dependencies

    def parse_package_line(self, line):
        line = line[len('Package:'):].split(',')
        packages = []
        for candidate in line:
            # this code can be shortened to oneliner, if one could do negative
            # lookahead assertion for character included in current pattern match
            # not supported, however, so groups are not containing exactly what they should
            #TODO: rewrite using tokenization/pyparsing
            package = re.match("\ ?(?P<name>[a-z0-9\-]+)(?!\.)(\-)?((?<=-)(?P<version>[0-9\-\.]+))?", candidate)
            if package:
                name = package.groupdict()['name']
                version = package.groupdict()['version']
                if name.endswith("-"):
                    name = name[:-1]
                packages.append(Package(name=name, version=version))
        return packages

    def get_dependencies(self):
        """ Return list of dependencies from control file """
        dependencies = []
        for line in self.control_file.splitlines():
            if line.startswith('Depends:'):
                dependencies.extend(self.parse_dependency_line(line))
        return dependencies

    def get_versioned_dependencies(self):
        deps = self.get_dependencies()
        return [dep for dep in deps if dep.is_versioned()]

    def get_packages(self):
        """ Return list of packages present in file """
        packages = []
        for line in self.control_file.splitlines():
            if line.startswith('Package:'):
                packages.extend(self.parse_package_line(line))
        return packages

    def check_downgrade(self, current_version, new_version):
        """
        Raise ValueError if new_version is lower then current_version
        """
        curr_tuple = map(int, current_version.split("."))
        new_tuple = map(int, new_version.split("."))


        for i in xrange(0, len(curr_tuple)):
            if len(new_tuple) < (i+1):
                raise ValueError("Attempt to downgrade %s to %s" % (
                    current_version,
                    new_version,
                ))
            elif new_tuple[i] > curr_tuple[i]:
                return True
            elif (new_tuple[i] < curr_tuple[i]):
                raise ValueError("Attempt to downgrade %s to %s" % (
                    current_version,
                    new_version,
                ))
        return True

    def get_dependency_merge(self, current_dependencies, new_dependencies):
        """
        Merge old dependencies with new one. If current dependency has version specified
        and it's in new_dependencies as well, replace it with it's version.

        Dependency and VersionedDependency with same name is not considered as a conflict

        Otherwise, leave it untouched.
        """
        deps = []
        for current_dep in current_dependencies:
            if current_dep.version:
                candidates = [i for i in new_dependencies if i.name == current_dep.name and i.version]
                if len(candidates) > 1:
                    raise ValueError(u"More then one dependency with same name")
                if len(candidates) == 1 and candidates[0].version:
                        if current_dep.version:
                            self.check_downgrade(current_dep.version, candidates[0].version)
                        current_dep.update_version(candidates[0].version)
            deps.append(current_dep)
            
        return deps


    def replace_dependencies(self, dependencies):
        """
        In my control file, replace version of dependencies with exact version
        """
        new_control_file = []
        for line in self.control_file.splitlines():
            if line.startswith('Depends:'):
                new_deps = self.get_dependency_merge(current_dependencies=self.parse_dependency_line(line),
                        new_dependencies=dependencies)
                dep_string = u", ".join(
                    [i.get_dependency_string() for i in new_deps]
                )
                if dep_string:
                    line = u"Depends: %s" % dep_string
                else:
                    line = u"Depends:"
            new_control_file.append(line)

        self.control_file = u'\n'.join(new_control_file)
        # newline at the and of the file is good manner
        self.control_file += u'\n'

    def replace_versioned_packages(self, version):
        """
        In my control file, replace versioned packages with updated version (preferably mine)
        """
        new_control_file = []
        dependencies = self.get_dependencies()
        new_deps = []
        
        for line in self.control_file.splitlines():
            if line.startswith('Package:'):
                packages = self.parse_package_line(line)
                for package in packages:
                    if package.version:
                        package.version = version
                string = u", ".join(
                    [i.get_package_string() for i in packages]
                )
                if string:
                    line = u"Package: %s" % string

                # and every versioned package is also becoming new dependency that must be updated
                # it makes on sense to include non-versioned ones for replacement (as they'll be merged from original)
                for package in packages:
                    if package.version:
                        new_deps.append(Dependency(name=package.name, version=package.version, sign='='))

            new_control_file.append(line)


        self.control_file = u'\n'.join(new_control_file)
        # newline at the and of the file is good manner
        self.control_file += u'\n'

        # and now, replace the dependencies
        self.replace_dependencies(new_deps)


def fetch_new_dependencies(repository):
    repo = fetch_repository(
        repository=repository['url'], branch=repository['branch']
    )
    deps = get_new_dependencies(repo)
    #rmtree(repo)

    return deps

def get_new_dependencies(dir):
    parser = ControlParser(open(os.path.join(dir, 'debian', 'control')).read())
    packages = parser.get_packages()

    version = ".".join(map(str, compute_version(get_git_describe(repository_directory=dir, fix_environment=True))))
    deps = [Dependency(str(package), version) for package in packages]

    return deps


def replace_versioned_packages(control_path, version, workdir=None):
    workdir = workdir or os.curdir
    f = open(control_path)
    parser = ControlParser(f.read())
    f.close()

    parser.replace_versioned_packages(version)

    f = open(control_path, 'w')
    f.write(parser.control_file)
    f.close


def replace_versioned_debian_files(debian_path, original_version, new_version):
    f = open(os.path.join(debian_path, 'control'))
    parser = ControlParser(f.read())
    f.close()
    versioned_deps = parser.get_versioned_dependencies()
    for path, dirs, files in walk(debian_path):
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
    f = open(control_path)
    meta_parser = ControlParser(f.read())
    f.close()

    deps_from_repositories = []

    current_meta_version = None
    for package in meta_parser.get_versioned_dependencies():
        if package.version:
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

    meta_parser.replace_dependencies(deps_from_repositories)

    f = open(control_path, 'w')
    f.write(meta_parser.control_file)
    f.close()

    # if versioned packages present, replace'em
    if current_meta_version:
        replace_versioned_debian_files(debian_path=dirname(control_path), original_version=current_meta_version, new_version=meta_version_string)
        replace_versioned_packages(control_path=control_path, version=meta_version_string)


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
