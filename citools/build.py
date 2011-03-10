from distutils.command.config import config
from distutils.core import Command


import logging
import os
from shutil import copytree

from citools.git import fetch_repository
from citools.version import retrieve_current_branch

logger = logging.getLogger(__name__)

def copy_images(repositories, static_dir):
    """
    For every repository, copy images from "static" dir in downloaded repository
    to static_dir/project, if directory exists
    """
    for repository in repositories:
        if repository.has_key('branch'):
            branch = repository['branch']
        else:
            branch = retrieve_current_branch(repository_directory=os.curdir, fix_environment=True)
        dir = fetch_repository(repository['url'], workdir=os.curdir, branch=branch)
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

def replace_template_files(root_directory, variables=None, template_files=None):
    """
    For given root_directory, walk through files specied in template_files (or default ones).
    Treat them as jinja2 templates, overwriting current content with rendered one,
    using variables provided in given variables argument (or default ones, mostly retrieved from git repo). 
    """
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(searchpath=root_directory))
    
    variables = variables or {
        'branch' : retrieve_current_branch(repository_directory=root_directory, fix_environment=True),
    }
    
    templates = template_files or ["requirements.txt", "setup.py", "pavement.py"]
    
    for template in templates:
        fp = os.path.join(root_directory, template)
        if os.path.exists(fp):
            t = env.get_template(template)
            rendered = t.render(**variables)
            
            f = open(fp, 'w')
            f.write(rendered)
            f.close()
        
def rename_template_files(root_directory, variables=None, subdirs=None):
    """
    In given root directory, walk through subdirs ("." allowed) and treat filename
    of every file present in given subdir as jinja2 template, renaming current
    file to new name, retrieved from rendering using variables given in variables
    argument (or default ones, mostly retrieved from git repo).
    """
    from jinja2 import Template
    
    variables = variables or {
        'branch' : retrieve_current_branch(repository_directory=root_directory, fix_environment=True),
    }
    
    subdirs = subdirs or ['debian']
    
    for dir in subdirs:
        if not os.access(os.path.join(root_directory, dir), os.W_OK):
            raise ValueError("Cannot rename files in %s, directory not writeable!" % str(os.path.join(root_directory, dir)))
        
        for fn in os.listdir(os.path.join(root_directory, dir)):
            fp = os.path.abspath(os.path.join(root_directory, dir, fn))
            if os.path.exists(fp):
                if not os.access(fp, os.R_OK|os.W_OK):
                    logging.error("Not handling file %s, unsufficient permissions (rw required)" % str(fp))
                
                newname = Template(fn).render(**variables)
                
                os.rename(fp, os.path.join(os.path.join(root_directory, dir, newname)))

class ReplaceTemplateFiles(config):

    description = ""

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        replace_template_files(root_directory=os.curdir, variables = {
            'version' : self.distribution.get_version()
        })

class RenameTemplateFiles(Command):

    description = ""

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        rename_template_files(root_directory=os.curdir, variables = {
            'version' : self.distribution.get_version()
        })
