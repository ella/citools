import os
import sys
from os.path import join, exists
from subprocess import check_call

from paver.easy import *

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
])
def compute_version_git(options):
    from citools.version import get_git_describe, compute_version

    if not getattr(options, "accepted_tag_pattern", None):
        options.accepted_tag_pattern = "%s-[0-9]*" % options.name

    current_git_version = get_git_describe(accepted_tag_pattern=options.accepted_tag_pattern)

    options.version = compute_version(current_git_version)
    options.version_str = '.'.join(map(str, options.version))

    print options.version_str

@task
@needs('compute_version_git')
def compute_version(options):
    pass

@task
def update_debian_version(options):
    from citools.debian.commands import update_debianization
    update_debianization(options.version)

@task
@needs(['compute_version'])
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
@needs(['replace_version', 'update_debian_version', 'build_debian_package'])
#@cmdopts([
#    ('upload-ftp', 'l', 'Upload packages to FTP server'),
#])
def create_debian_package(options):
    pass
#    if getattr(options, "upload_ftp", None):
#        call_task(upload_debian_package(options))

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
@consume_args
def record_packages(args):
    production_machine = args[0]
    preproduction_machine = args[1]
    clean_machine = args[2]
    project = args[3]
    try:
        project_version = args[4] + ","
    except IndexError:
        project_version = ''
    try:
        spectator_password = args[5] + ","
    except IndexError:
        spectator_password = ""
    try:
        unwanted_packages = args[6] + ","
    except IndexError:
        unwanted_packages = 'mypage;ella'
    try:
        domain_username = args[7]
    except IndexError:
        domain_username = ''

    sh('fab compare_vs_production:%(pm)s,%(p)s,%(pv)s%(sp)shost=%(cm)s execute_diff_packages:%(up)shost=%(prem)s upload_packages:%(du)shost=%(cm)s' % {
	"pm" : production_machine,
	"p" : project,
	"pv" : project_version,
	"sp" : spectator_password,
	"cm" : clean_machine,
	"up" : unwanted_packages,
	"prem" : preproduction_machine,
	"du" : domain_username
    })

@task
@consume_args
def install_production_packages(args):
    production_machine = args[0]
    clean_machine = args[1]
    try:
        spectator_password = args[2]+","
    except IndexError:
        spectator_password = ''
    sh('fab install_production_packages:%(pm)s,%(sp)shost=%(cm)s' % {
	"pm" : production_machine,
	"cm" : clean_machine,
	"sp" : spectator_password
    })

@task
@consume_args
def install_project(args):
    clean_machine = args[0]
    project = args[1]
    try:
        project_version = args[2]+","
    except IndexError:
        project_version = ''
    sh('fab install_project:%(p)s,%(pv)shost=%(cm)s' % {
	"cm" : clean_machine,
	"p" : project,
	"pv" : project_version
    })

@task
@consume_args
def compare_vs_production(args):
    production_machine = args[0]
    clean_machine = args[1]
    project = args[2]
    try:
        project_version = args[3] + ","
    except IndexError:
        project_version = ''
    try:
        spectator_password = args[4] + ","
    except IndexError:
        spectator_password = ''
    sh('fab compare_vs_production:%(pm)s,%(p)s,%(pv)s%(sp)shost=%(cm)s' % {
	"pm" : production_machine,
	"p" : project,
	"pv" : project_version,
	"cm" : clean_machine,
	"sp" : spectator_password
    })

@task
@consume_args
def execute_diff_packages(args):
    production_machine = args[0]
    preproduction_machine = args[1]
    clean_machine = args[2]
    project = args[3]
    try:
        project_version = args[4] + ","
    except IndexError:
        project_version = ''
    try:
        spectator_password = args[5] + ","
    except IndexError:
        spectator_password = ""
    try:
        unwanted_packages = args[6] + ","
    except IndexError:
        unwanted_packages = 'mypage;ella'
    sh('fab compare_vs_production:%(pm)s,%(p)s,%(pv)s%(sp)shost=%(cm)s execute_diff_packages:%(up)shost=%(prem)s' % {
	"pm" : production_machine,
	"p" : project,
	"pv" : project_version,
	"sp" : spectator_password,
	"cm" : clean_machine,
	"up" : unwanted_packages,
	"prem" : preproduction_machine
    })

@task
@consume_args
def download_diff_packages(args):
    production_machine = args[0]
    preproduction_machine = args[1]
    clean_machine = args[2]
    project = args[3]
    try:
        project_version = args[4] + ","
    except IndexError:
        project_version = ''
    try:
        spectator_password = args[5] + ","
    except IndexError:
        spectator_password = ""
    try:
        unwanted_packages = args[6] + ","
    except IndexError:
        unwanted_packages = 'mypage;ella'
    sh('fab compare_vs_production:%(pm)s,%(p)s,%(pv)s%(sp)shost=%(cm)s execute_diff_packages:%(up)shost=%(prem)s download_diff_packages:host=%(cm)s' % {
	"pm" : production_machine,
	"p" : project,
	"pv" : project_version,
	"sp" : spectator_password,
	"cm" : clean_machine,
	"up" : unwanted_packages,
	"prem" : preproduction_machine
    })
