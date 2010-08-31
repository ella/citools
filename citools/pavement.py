import os
import sys
from os.path import join, exists


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
def compute_version(options):
    from citools.version import get_git_describe, compute_version
    #FIXME
    format = "%s-[0-9]*" % options.name

    current_git_version = get_git_describe(accepted_tag_pattern=format)

    version = compute_version(current_git_version)
    version_str = '.'.join(map(str, version))

    print version_str

