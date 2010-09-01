from ftplib import error_perm
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
@cmdopts([
    ('ftp-host=', 'o', 'FTP host (for debian package upload)'),
    ('ftp-port=', 'p', 'FTP port (for debian package upload)'),
    ('ftp-user=', 'u', 'FTP username (for debian package upload)'),
    ('ftp-password=', 'w', 'FTP password (for debian package upload)'),
    ('ftp-directory=', 'd', 'FTP directory (in which to packages directories are) (for debian package upload)'),
    ('forgive-no-packages', 'f', 'It is OK to upload even if there are no packages'),
])
def upload_debian_package(options):
    import os, re
    from ftplib import FTP
    
    def get_packages_names():
        control = os.path.join('debian', 'control')
        if not os.path.exists(control):
            raise ValueError("Cannot find debian/control")
        packages = []
        version_pattern = re.compile("^(Package\:){1}(\s)*(?P<name>[\w\-\.]+).*(\s)*$")
        for line in open(control, 'r'):
            match = re.match(version_pattern, line)
            if match:
                packages.append(match.groupdict()['name'])
        return packages


    def get_package_path(package_name, module_name, current_version=None):
        """ Return filesystem path to debian package build by bdist_deb"""
        if not current_version:
            #FIXME: not to hardcode
            format = "%s-[0-9]*" % module_name
            current_version = '.'.join(map(str, compute_version(get_git_describe(accepted_tag_pattern=format))))
        package_name = u"%(name)s_%(version)s_%(arch)s.deb" % {
            'name' : package_name,
            'version' : current_version,
            'arch' : 'all'
        }
        return os.path.normpath(os.path.join(os.curdir, os.pardir, package_name))

    def upload_package(host, username, password, directory, package_path, package_name, port=21):
        ftp = FTP()
        ftp.connect(host, port)
        try:
            ftp.login(username, password)

            for dir in directory:
                try:
                    ftp.cwd(dir)
                except error_perm:
                    # probably not exists, try again
                    ftp.mkd(dir)
                    ftp.cwd(dir)

            if package_name not in ftp.nlst():
                ftp.mkd(package_name)

            ftp.cwd(package_name)

            file = open(package_path, "rb")
            ftp.storbinary('STOR ' + os.path.basename(package_path), file)
            file.close()

        finally:
            ftp.quit()


    packages = get_packages_names()

    if len(packages) == 0:
        raise ValueError("Not uploading: no package recodnized")

    if not getattr(options, "version_str", None):
        call_task("compute_version")

    print u"Uploading packages %s" % packages
    for package_name in packages:
        package_path = get_package_path(package_name, options.name, current_version=options.version_str)
        upload_package(options.ftp_host, options.ftp_user, options.ftp_password, \
            options.ftp_directory.split("/"), package_path, package_name, port=getattr(options, "ftp_port", 21))

@task
@needs(['replace_version', 'update_debian_version', 'build_debian_package'])
@cmdopts([
    ('upload-ftp', 'f', 'Upload packages to FTP server'),
])
def create_debian_package(options):
    pass
#    if options.without_upload:
#        call_task(upload_debian_package(options))
