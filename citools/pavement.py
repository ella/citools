from paver.easy import *

@task
@consume_args
@needs('unit', 'integrate')
def test():
    """ Run whole testsuite """

def djangonize_test_environment(test_project_module):

    sys.path.insert(0, abspath(join(dirname(__file__))))
    sys.path.insert(0, abspath(join(dirname(__file__), "tests")))
    sys.path.insert(0, abspath(join(dirname(__file__), "tests", test_project_module)))

    os.environ['DJANGO_SETTINGS_MODULE'] = "%s.settings" % test_project_module

def run_tests(test_project_module, nose_args):
    djangonize_test_environment(test_project_module)

    import nose

    os.chdir(abspath(join(dirname(__file__), "tests", test_project_module)))

    argv = ["--with-django"] + nose_args

    nose.run_exit(
        argv = ["nosetests"] + argv,
        defaultTest = test_project_module
    )

@task
@consume_args
def unit(args):
    """ Run unittests """
    run_tests(test_project_module="unit_project", nose_args=[]+args)

@task
@consume_args
def integrate(args):
    """ Run integration tests """
    run_tests(test_project_module="example_project", nose_args=["--with-selenium", "--with-djangoliveserver"]+args)


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
