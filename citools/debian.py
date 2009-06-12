import re

__all__ = ("Dependency", "ControlParser")

class Dependency(object):
    """
    Dependency in the debian package
    """
    def __init__(self, name, version=None):
        super(Dependency, self).__init__()
        
        self.name = name
        self.version = version

    def get_dependency_string(self):
        if self.version:
            return u"%(name)s (= %(version)s)" % {
                'name' : self.name,
                'version' : self.version,
            }
        else:
            return self.name
        
    def __str__(self):
        return "%(name)s: %(version)s" % {
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
            dependencies.extend([Dependency(i[0]) for i in deps])
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
            if new_tuple[i] < curr_tuple[i]:
                raise ValueError("Attempt to downgrade %s to %s" % (
                    current_version,
                    new_version,
                ))

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
                        current_dep.version = candidates[0].version
            deps.append(current_dep)
            
        return deps


    def replace_dependencies(self, dependencies):
        """
        In my control file, replace version of dependencies with exact version
        """
        new_control_file = self.control_file
        
        for line in self.control_file:
            if line.startswith('Depends:'):
                line = u"Depends: %s" % ", ".join(
                    self.get_dependency_merge(current_dependencies=self.parse_dependency_line(line),
                        new_dependencies=dependencies)
                )
            new_control_file.append(line)

        self.control_file = new_control_file



