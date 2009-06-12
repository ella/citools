import re

__all__ = ("Dependency", "ControlParser")

class Dependency(object):
    """
    Dependency in the debian package
    """
    def __init__(self, name, version=None, sign=None):
        super(Dependency, self).__init__()
        
        self.name = name
        self.version = version
        self.sign = sign

        if not self.sign and version:
            self.sign = u'='

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

class ControlParser(object):
    """
    Parser for debian/control files
    """
    def __init__(self, control_file):
        super(ControlParser, self).__init__()

        self.control_file = control_file

    def parse_dependency_line(self, line):
        """ Return dependency from Depends: line """
        #TODO: Better parsing, especially when we will need image-<version> package
        line = line[len("Depends:"):]
        dependencies = []
        dependency_candidates = line.split(",")
        for candidate in dependency_candidates:
            deps = re.findall("(?P<name>[a-z0-9\-]+)(?P<version>\ \([\=\>\<]+\ [0-9\-\.]+\))?", candidate)
            for dep in deps:
                new_dep = Dependency(dep[0])
                if dep[1]:
                    new_dep.extract_version_from_debversion(dep[1])
                dependencies.append(new_dep)
        return dependencies

    def get_dependencies(self):
        """ Return list of dependencies from control file """
        dependencies = []
        for line in self.control_file.splitlines():
            if line.startswith('Depends:'):
                dependencies.extend(self.parse_dependency_line(line))
        return dependencies

    def check_downgrade(self, current_version, new_version):
        """
        Raise ValueError if new_version is lower then current_version
        """
        curr_tuple = current_version.split(".")
        new_tuple = new_version.split(".")


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
        Otherwise, leave it untouched.
        """
        deps = []
        for current_dep in current_dependencies:
            if current_dep.version:
                candidates = [i for i in new_dependencies if i.name == current_dep.name]
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


def update_dependency_versions(repositories, control_path):
    pass
