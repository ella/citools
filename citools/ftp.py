from ftplib import FTP, error_perm
import os

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
