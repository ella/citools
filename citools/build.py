from distutils.command.config import config
import os
from shutil import copytree

from citools.git import fetch_repository

def copy_images(repositories, static_dir):
    """
    For every repository, copy images from "static" dir in downloaded repository
    to static_dir/project, if directory exists
    """
    for repository in repositories:
        dir = fetch_repository(repository['url'], workdir=os.curdir, branch=repository['branch'])
        package_static_dir = os.path.join(dir, repository['package_name'], 'static')
        if os.path.exists(package_static_dir):
            copytree(package_static_dir, os.path.join(static_dir, repository['package_name']))
    
class CopyDependencyImages(config):

    description = "copy all dependency static files into one folder"

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
