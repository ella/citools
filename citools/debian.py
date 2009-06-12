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
        for line in self.control_file:
            if line.startswith('Depends:'):
                dependencies.extend(self.parse_dependency_line(line))
        return dependencies

    def replace_dependencies(self):
        pass