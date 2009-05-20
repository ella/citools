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
