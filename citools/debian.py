import re

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
            dependencies.extend([i[0] for i in deps])
        return dependencies

    def get_dependencies(self):
        """ Return list of dependencies from control file """
        dependencies = []
        for line in self.control_file:
            if line.startswith('Depends:'):
                print line
                dependencies.extend(self.parse_dependency_line(line))
        return dependencies

def update_dependency_versions(repositories, control_path):
    pass

