from distutils.command.config import config
import os
from shutil import rmtree, copytree

from citools.git import fetch_repository

def copy_images(repositories, static_dir):
    for repository in repositories:
        dir = fetch_repository(repository['url'], workdir=os.curdir, branch=repository['branch'])
        copytree(os.path.join(dir, repository['package_name'], 'static'), os.path.join(static_dir, repository['package_name']))
        rmtree(dir)



class CopyDependencyImages(config):
    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            copy_images(self.distribution.dependencies_git_repositories, 'static')
        except Exception:
            import traceback
            traceback.print_exc()
            raise
