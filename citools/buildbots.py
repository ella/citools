from distutils.command.config import config
import logging

from buildbot.steps import shell

__all__ = (
    "DatabaseBackupRestore", "CriticalTest", "DatabaseBackupRestore",
    "AptitudeInstall", "DatabaseMigrate", "GitSetVersion", "BuildDebianPackage",
)

class CriticalShellCommand(shell.ShellCommand):
    warnOnFailure = 1
    flunkOnFailure = 1
    haltOnFailure = 1

class CriticalTest(shell.Test):
    name = "test"
    description = ["running tests"]
    descriptionDone = ["tested"]
    warnOnFailure = 1
    flunkOnFailure = 1
    haltOnFailure = 1

class DatabaseBackupRestore(CriticalShellCommand):
    name = "restore backup"
    description = ["restoring backup"]
    descriptionDone = ["backup restored"]
    command = ["citools", "restore_backup"]

    def __init__(self, citools_config, command=None, **kwargs):
        if not command:
            command = [i for i in self.command]
            command.append("--config=%s" % citools_config)

        CriticalShellCommand.__init__(self, command=command, **kwargs)

class AptitudeInstall(CriticalShellCommand):
    name = "install package"
    description = ["installing package"]
    descriptionDone = ["package installed"]
    command = ["aptitude", "install", "-r", "-y"]

    def __init__(self, package_name, command=None, use_sudo=True, allow_untrusted=True, **kwargs):
        if not command:
            if use_sudo:
                command = ['sudo']
            else:
                command = []
            command += [i for i in self.command]
            command.append(package_name)
            if allow_untrusted and '--allow-untrusted' not in command:
                command.append('--allow-untrusted')
        CriticalShellCommand.__init__(self, command=command, **kwargs)


class DatabaseMigrate(CriticalShellCommand):
    name = "migrating database"
    description = ["migrating database"]
    descriptionDone = ["database migrated"]
    command = None

    def __init__(self, manage_command, command=None, **kwargs):
        if not command:
            command = [manage_command, "migrate"]
        CriticalShellCommand.__init__(self, command=command, **kwargs)

class GitSetVersion(CriticalShellCommand):
    name = "update version"
    description = ["setting version"]
    descriptionDone = ["version set"]
    command = ["python", "setup.py", "compute_version_git"]

class BuildDebianPackage(CriticalShellCommand):
    name = "build debian package"
    description = ["building debian package"]
    descriptionDone = ["package build"]
    command = ["python", "setup.py", "bdist_deb"]

class GitPingMaster(CriticalShellCommand):
    name = "ping another master"
    description = ["pinging another master"]
    descriptionDone = ["master ping'd"]
    command = ["python", "setup.py", "buildbot_ping_git"]


def validate_meta_buildbot(dist, attr, value):
    pass

def buildbot_ping_git(host, port, branch):
    """
    Ping our meta repository to emulate new change and trigger build suite.

    We don't want to download meta repository to get informations, so we create
    fakes with tip et al.
    """
    from twisted.spread import pb
    from twisted.cred import credentials
    from twisted.internet import reactor

    master = "%s:%s" % (host, port)

    f = pb.PBClientFactory()
    d = f.login(credentials.UsernamePassword("change", "changepw"))
    reactor.connectTCP(host, port, f)

    def connect_failed(error):
        logging.error("Could not connect to %s: %s"
            % (master, error.getErrorMessage()))
        return error

    def cleanup(res):
        reactor.stop()

    def add_change(remote, branch):
        change = {
            'revision': "FETCH_HEAD",
            'who' : 'BuildBot',
            'comments': "Dependency changed, sending dummy commit",
            'branch': branch,
            'category' : 'auto',
            'files' : [
                'CHANGELOG'
            ],
        }
        d = remote.callRemote('addChange', change)
        return d

    def connected(remote, branch):
        return add_change(remote, branch)

    d.addErrback(connect_failed)
    d.addCallback(connected, branch)
    d.addBoth(cleanup)

    reactor.run()





class BuildbotPingGit(config):
    """
    Ping another buildbot. Heavily based on git_buildbot.py used in post-receive hooks
    """
    description = "Ping Buildbot Master as if it's HEAD repository was received"
    user_options = [
    ]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        master_config = self.distribution.buildbot_meta_master
        if master_config.has_key('branch'):
            branch = master_config['branch']
        else:
            branch = "master"

        buildbot_ping_git(master_config['host'], master_config['port'], branch)

