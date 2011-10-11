from datetime import datetime
import os
from os.path import join, exists
from subprocess import check_call

from citools.build import rename_template_files as _rename_template_files, replace_template_files, get_common_variables

from paver.easy import *
from paver.setuputils import _get_distribution

@task
@consume_args
@needs('unit', 'integrate')
def test():
    """ Run whole testsuite """

def djangonize_test_environment(test_project_module):

    sys.path.insert(0, options.rootdir)
    sys.path.insert(0, join(options.rootdir, "tests"))
    if exists(join(options.rootdir, "tests", test_project_module)):
        sys.path.insert(0, join(options.rootdir, "tests", test_project_module))

    os.environ['DJANGO_SETTINGS_MODULE'] = "%s.settings" % test_project_module

def run_tests(test_project_module, nose_args, nose_run_kwargs=None):
    djangonize_test_environment(test_project_module)

    import nose

    os.chdir(join(options.rootdir, "tests", test_project_module))

    argv = ["--with-django"] + nose_args

    nose_run_kwargs = nose_run_kwargs or {}

    nose.run_exit(
        argv = ["nosetests"] + argv,
        defaultTest = test_project_module,
        **nose_run_kwargs
    )

@task
@consume_args
def unit(args, nose_run_kwargs=None):
    """ Run unittests """
    run_tests(test_project_module="unit_project", nose_args=args, nose_run_kwargs=nose_run_kwargs)

@task
@consume_args
def integrate(args, nose_run_kwargs=None):
    """ Run integration tests """
    run_tests(test_project_module="example_project", nose_args=["--with-selenium", "--with-djangoliveserver"]+args, nose_run_kwargs=nose_run_kwargs)

@task
@consume_args
def integrate_project(args):
    """ Run integration tests """
    
    djangonize_test_environment(options.project_module)

    os.chdir(join(options.rootdir, "tests"))

    import nose

    nose.run_exit(
        argv = ["nosetests", "--with-django", "--with-selenium", "--with-djangoliveserver"]+args,
        defaultTest = "tests"
    )


@task
def install_dependencies():
    sh('pip install -r requirements.txt')

@task
def bootstrap():
    options.virtualenv = {'packages_to_install' : ['pip']}
    call_task('paver.virtual.bootstrap')
    sh("python bootstrap.py")
    path('bootstrap.py').remove()


    print '*'*80
    if sys.platform in ('win32', 'winnt'):
        print "* Before running other commands, You now *must* run %s" % os.path.join("bin", "activate.bat")
    else:
        print "* Before running other commands, You now *must* run source %s" % os.path.join("bin", "activate")
    print '*'*80

@task
@needs('citools.paver.install_dependencies')
def prepare():
    """ Prepare complete environment """

@task
def bump():
    """
    Bump most-minor tagged version. Assumes git.
    
    Bump is completed only since last release. This is assumed to have
    $projectname-[digit]* format. If not, it shall be configured
    as options.release_tag_format.
    """

    if getattr(options, "release_tag_format", False):
        format = release_tag_format
    else:
        format = "%s-[0-9]*" % options.name

    from citools.version import get_git_describe, compute_version
    version = compute_version(get_git_describe(accepted_tag_pattern=format))

    new_version = list(version[:-1])
    new_version[len(new_version)-1] += 1

    tag = options.name + "-" + ".".join(map(str, new_version))

    sh('git tag -a %s -m "paver bump to version %s"' % (tag, tag))

@task
@cmdopts([
    ('accepted-tag-pattern=', 't', 'Tag pattern passed to git describe for version recognition'),
    ('datetime-mode', 'd', 'Version is set by last commit datetime'),
])
def compute_version_git(options):
    if not getattr(options, 'datetime_mode', False):
        print compute_version_git_number(options)
    else:
        from citools.version import get_git_head_tstamp

        tstamp = int(get_git_head_tstamp())
        if not tstamp:
            raise Exception("Git log parsing error")
        commit_dtime = datetime.fromtimestamp(tstamp)
        print commit_dtime.strftime("%Y-%m-%d-%H%M")

def compute_version_git_number(options):
    from citools.version import get_git_describe, compute_version, get_branch_suffix, retrieve_current_branch
    if not getattr(options, "accepted_tag_pattern", None):
        options.accepted_tag_pattern = "%s-[0-9]*" % options.name

    dist = _get_distribution()

    current_git_version = get_git_describe(accepted_tag_pattern=options.accepted_tag_pattern)
    branch_suffix = get_branch_suffix(dist.metadata, retrieve_current_branch())

    options.version = compute_version(current_git_version)
    dist.metadata.version = options.version_str = '.'.join(map(str, options.version))

    dist.metadata.branch_suffix = options.branch_suffix = branch_suffix

    return options.version_str

@task
@needs('compute_version_git')
def compute_version(options):
    pass

@task
def update_debian_version(options):
    from citools.debian.commands import update_debianization
    update_debianization(options.version)

@task
def replace_version(options):
    from citools.version import replace_inits, replace_scripts, replace_version_in_file

    replace_inits(options.version, options.packages)
    # replace_scripts(options.version, options.py_modules)

    replace_version_in_file(options.version, 'setup.py')

    if os.path.exists('pavement.py'):
        replace_version_in_file(options.version, 'pavement.py')


@task
def build_debian_package(options):
    check_call(['dpkg-buildpackage', '-rfakeroot-tcp', '-us', '-uc'])

@task
#@needs(['create_debian_package'])
@cmdopts([
    ('ftp-host=', 'o', 'FTP host (for debian package upload)'),
    ('ftp-port=', 'p', 'FTP port (for debian package upload)'),
    ('ftp-user=', 'u', 'FTP username (for debian package upload)'),
    ('ftp-password=', 'w', 'FTP password (for debian package upload)'),
    ('ftp-directory=', 'd', 'FTP directory (in which to packages directories are) (for debian package upload)'),
    ('forgive-no-packages', 'n', 'It is OK to upload even if there are no packages'),
])
def upload_debian_package(options):
    import os
    from ftplib import FTP

    from citools.debian.commands import get_packages_names, get_package_path
    from citools.ftp import upload_package
    
    packages = get_packages_names()

    if len(packages) == 0:
        raise ValueError("Not uploading: no package recognized")

    if not getattr(options, "version_str", None):
        call_task("compute_version")

    print u"Uploading packages %s" % packages
    for package_name in packages:
        package_path = get_package_path(package_name, options.name, current_version=options.version_str)
        upload_package(options.ftp_host, options.ftp_user, options.ftp_password, \
            options.ftp_directory.split("/"), package_path, package_name, port=getattr(options, "ftp_port", 21))

@task
def rename_template_files():
    _rename_template_files(root_directory=os.curdir, variables=get_common_variables(_get_distribution()))

@task
def replace_templates():
    replace_template_files(
        root_directory=os.curdir,
        variables=get_common_variables(_get_distribution()),
        subdirs=getattr(options, "template_files_directories", None)
    )


@task
@needs([
        'compute_version',
        'replace_version',
        'replace_templates',
        'rename_template_files',
        'update_debian_version',
        'build_debian_package'
])
def create_debian_package(options):
    pass

@task
@cmdopts([
    ('host=', 'o', 'Buildmaster hostname'),
    ('port=', 'p', 'Buildmaster port'),
    ('branch=', 'b', 'Branch with change'),
])
def ping_buildmaster():
    from citools.buildbots import buildbot_ping_git
    from citools.version import retrieve_current_branch

    if not getattr(options, "branch", None):
        options.branch = retrieve_current_branch()

    buildbot_ping_git(options.host, int(options.port), options.branch)


@task
@cmdopts([
    ('production-machine=', 'p', 'Production machine'),
    ('clean-machine=', 'c', 'Clean machine'),
    ('production-backend-machine=', 'b', 'Production backend machine'),
    ('enabled-architectures=', 'a', 'Enabled architectures')
])
def install_production_packages(options):
    production_machine = getattr(options, "production_machine", None)
    clean_machine = getattr(options, "clean_machine")
    production_backend_machine = getattr(options, "production_backend_machine", None)
    enabled_architectures = getattr(options, "enabled_architectures", None)
    fabfile_name = getattr(options, "fabfile_name", '')
    # import your fabfile
    if fabfile_name != '':
        fabfile = import_fabfile(fabfile_name)
    else:
        fabfile = import_fabfile()
    # invoke fabric task
    args = (clean_machine, production_machine, production_backend_machine, enabled_architectures)
    options.packages_list = fab(clean_machine, 
				fabfile['install_production_packages'], 
				resolve,
				args
				)


@task
@cmdopts([
    ('preproduction-machine=', 'r', 'Preproduction machine'),
    ('unwanted-packages=', 'n', 'Unwanted packages'),
    ('section-packages=', 's', 'Enabled packages section'),
    ('disable-urls=', 'l', 'Disable urls for debian repo')
])
@needs('install_production_packages')
def execute_diff_packages(options):
    preproduction_machine = getattr(options, "preproduction_machine")
    unwanted_packages = getattr(options, "unwanted_packages", '')
    section_packages = getattr(options, "section_packages", ".*")
    disable_urls = getattr(options, "disable_urls", '')
    fabfile_name = getattr(options, "fabfile_name", '')
    # import your fabfile
    if fabfile_name != '':
        fabfile = import_fabfile(fabfile_name)
    else:
        fabfile = import_fabfile()
    # invoke fabric task
    args = (options.packages_list, unwanted_packages, section_packages, disable_urls)
    options.diff_packages_list = fab(preproduction_machine, 
				 fabfile['execute_diff_packages'], 
				 resolve,
				 args 
				 )


@task
@cmdopts([
    ('project=', 'j', 'Project'),
    ('project-version=', 'v', 'Project version'),
    ('project-config=', 'f', 'Project config'),
    ('project-only=', 'o', 'Project packages only'),
    ('prompt-type=', 'e', 'Type of prompt for selecting packages')
])
@needs('execute_diff_packages')
def download_diff_packages(options):
    clean_machine = getattr(options, "clean_machine")
    project = getattr(options, "project")
    project_version = getattr(options, "project_version", '')
    project_config = getattr(options, "project_config", True)
    project_only = getattr(options, "project_only", 'no')
    prompt_type = getattr(options, "prompt_type", 'b')
    fabfile_name = getattr(options, "fabfile_name", '')
    # import your fabfile
    if fabfile_name != '':
        fabfile = import_fabfile(fabfile_name)
    else:
        fabfile = import_fabfile()
    # invoke fabric task
    args = (options.diff_packages_list, project, project_version, project_config, project_only, prompt_type)
    options.packages_for_upload = fab(clean_machine, 
				 fabfile['download_diff_packages'], 
				 resolve,
				 args
				 )
  

@task
@cmdopts([
    ('domain-username=', 'd', 'Domain username'),
    ('directory-structure=', 't', 'Directory structure for upload packages'),
    ('upload-url=', 'u', 'Url for upload')
])
@needs('download_diff_packages')
def upload_packages(options):
    clean_machine = getattr(options, "clean_machine")
    domain_username = getattr(options, "domain_username", '')
    upload_url = getattr(options, "upload_url", '')
    directory_structure = getattr(options, "directory_structure", '')
    fabfile_name = getattr(options, "fabfile_name", '')
    # import your fabfile
    if fabfile_name != '':
        fabfile = import_fabfile(fabfile_name)
    else:
        fabfile = import_fabfile()
    # invoke fabric task
    args = (options.packages_for_upload,)
    kwargs = { "rdir" : directory_structure, "upload_url" : upload_url, "domain_username" :  domain_username }
    fab(clean_machine, fabfile['upload_packages'], resolve, args, kwargs)
    
    
# fabric wrapper snippets

def resolve(host):
    """write similar function for eg: resolving from aws or ssh_config"""
    from fabric.main import find_fabfile, load_fabfile
    from fabric.network import normalize
    from fabric import state

    return (host,) + normalize(host)

def fab(host, cmd, resolve=resolve, args=(), kwargs={}):
    """call one fabric task"""
    from fabric.main import find_fabfile, load_fabfile
    from fabric.network import normalize
    from fabric import state

    host_string, username, hostname, port = resolve(host)
    state.env.host_string = host_string
    state.env.host = hostname
    state.env.user = username
    state.env.port = port
    return cmd(*args, **kwargs)

def import_fabfile(fabfile='fabfile.py'):
    """ you have to call this first to enable fabric tasks"""
    from fabric.main import find_fabfile, load_fabfile
    from fabric.network import normalize
    from fabric import state

    state.env.fabfile = fabfile
    _, fabfile = load_fabfile(find_fabfile())
    return fabfile


@task
@needs('paver.doctools.html')
def publish_docs(options):
    """Build documentation and move it into docroot"""
    builtdocs = path("docs") / options.sphinx.builddir / "html"
    if getattr(options, "docroot", None):
        destdir = options.docroot
    else:
        destdir = path(getattr(options, "docroot", '/big/docs/')) / options.name
    if getattr(options, "doc_use_branch_dir", False):
        from citools.version import retrieve_current_branch
        branch = retrieve_current_branch()
        if branch != getattr(options, "doc_root_branch", "automation"):
            destdir = destdir / "branches" / branch

    destdir.rmtree()
    builtdocs.move(destdir)
    destdir.chmod(getattr(options, "doc_dir_chmod", 0777))

    for dirpath, dirnames, filenames in os.walk(destdir):
        for d in dirnames:
            os.chmod(join(dirpath, d), getattr(options, "doc_dir_chmod", 0777))
        for f in filenames:
            os.chmod(join(dirpath, f), getattr(options, "doc_file_chmod", 0444))
