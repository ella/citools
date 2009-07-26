from distutils.cmd import Command

class PrepareSphinxHtmlDocumentation(Command):
    description = "Prepare sphinx's HTML documentation in given directory (dist/doc by default)"

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
        ("update_version_git", None),
        ("update_debian_version", None),
        ("update_dependency_versions", None),
        ("copy_dependency_images", None),
        ("bdist_deb", None),
    ]


#from sphinx.setup_command imor t


