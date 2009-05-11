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
            command = self.command
            command.append("-c")
            command.append(citools_config)

        super(AptitudeInstall, self).__init__(command=command, **kwargs)

class AptitudeInstall(CriticalShellCommand):
    name = "install package"
    description = ["installing package"]
    descriptionDone = ["package installed"]
    command = ["aptitude", "install"]

    def __init__(self, package_name, command=None, **kwargs):
        if not command:
            command = self.command
            command.append(package_name)
        super(AptitudeInstall, self).__init__(command=command, **kwargs)


class DatabaseMigrate(CriticalShellCommand):
    name = "migrating database"
    description = ["migrating database"]
    descriptionDone = ["database migrated"]
    command = None

    def __init__(self, manage_command, command=None, **kwargs):
        if not command:
            command = [manage_command, "migrate"]
        super(DatabaseMigrate, self).__init__(command=command, **kwargs)

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
