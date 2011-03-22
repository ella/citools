from __future__ import with_statement

from distutils.command.config import config
from distutils.core import Command
from distutils.errors import DistutilsSetupError

from itertools import chain
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

def _replace_template(file_path, variables):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            from jinja2 import Template
            rendered = Template(f.read().decode('utf-8')).render(**variables)
        
        f = open(file_path, 'w')
        f.write(rendered.encode('utf-8'))
        f.close()

def replace_template_files(root_directory, variables=None, template_files=None, subdirs=None):
    """
    For given root_directory, walk through files specified in template_files (or default ones)
    and every file in given subdirectories ('debian' by default, pass [] to skip this step). 
    Treat them as jinja2 templates, overwriting current content with rendered one,
    using variables provided in given variables argument (or default ones, mostly retrieved from git repo). 
    """
    variables = variables or {
        'branch' : retrieve_current_branch(repository_directory=root_directory, fix_environment=True),
    }
    
    templates = template_files or ["requirements.txt", "setup.py", "pavement.py"]
    
    for template in templates:
        fp = os.path.join(root_directory, template)
        _replace_template(fp, variables)
    
    if subdirs is None:
        subdirs = ['debian']

    if subdirs:
        for subdir in subdirs:
            dp = os.path.join(*list(chain([root_directory], subdir.split('/'))))
            print dp
            if os.path.exists(dp):
                for file in os.listdir(dp):
                    fp = os.path.join(root_directory, subdir, file)
                    if os.path.isfile(fp):
                        _replace_template(fp, variables)
        
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
            if os.path.exists(fp) and os.path.isfile(fp):
                if not os.access(fp, os.R_OK|os.W_OK):
                    logging.error("Not handling file %s, unsufficient permissions (rw required)" % str(fp))
                
                newname = Template(fn).render(**variables)
                
                os.rename(fp, os.path.join(os.path.join(root_directory, dir, newname)))

def get_common_variables(distribution):
    variables = {
        'version' : distribution.get_version()
    }
    
    probe = getattr(distribution.metadata, "template_attributes", [
        "branch_suffix",
        "dependency_versions",
    ])
    
    for var in probe:
        if hasattr(distribution.metadata, var):
            variables[var] = getattr(distribution.metadata, var)
    
    return variables

def validate_template_files_directories(dist, attr, value):
    pass
#     if not isinstance(value, list):
#        raise DistutilsSetupError(
#            "%s must be a list or iterable" % (attr,value)
#        )


class ReplaceTemplateFiles(Command):
    description = "Inside files parsed as jinja2 templates, do in-place replacement of given variables"

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        replace_template_files(
            root_directory=os.curdir,
            variables=get_common_variables(self.distribution),
            subdirs=getattr(self.distribution, "template_files_directories", None)
        )

class RenameTemplateFiles(Command):
    description = "Files named using jinja2 syntax, rename them using variable substitution."

    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        rename_template_files(root_directory=os.curdir, variables=get_common_variables(self.distribution))
