"""
This script take list of packages from operation list and list of packages from preprodution
then do diff and send residual packages to production repo
Using fab compare_vs_production:args,host=cleanmachine_address execute_diff_packages:args,host=preproduction_address upload_packages:args,host=cleanmachine_address 
Example fab compare_vs_production:hp9fe1.cent,centrum-mypage-auto,host=clean.dev.chservices.cz execute_diff_packages:host=cms-hp9fe.dev.chservices.cz upload_packages:host=clean.dev.chservices.cz
"""
import sys
import string
import urllib
from datetime import datetime

import paramiko
from fabric.api import run, abort
#from fabric.contrib.console import confirm
#from fabric.api import run

#config for uploading packages
PROJECT = "mypage"
TODAY =  datetime.now().strftime("%y%m%d-%H%M")
SCHEME = "ftp"
URL = "localapt.centrum.cz"
LDIR = "/var/cache/apt/archives/"
RDIR = "lenny/apps/centrum-%s-all" % (PROJECT,)

#This is the tuple of url from repo for packages that not be in diff dpkg -l 
DISABLE_URL = (
	      "http://debian.repo.chservices.cz",
	      "http://security.repo.chservices.cz",
	      "http://apt.repo.chservices.cz",
	      "http://backports.repo.chservices.cz",
)

def download_diff_packages(diff_packages_list, project, project_version=''):
    """
    This function install projet and download packages from diff list 
    """
    try:
        run('rm /var/cache/apt/archives/*.deb')
    except:
        print "\nwarning: can not remove non-existent files or directory\n"
    
    install_project(project, project_version)
    
    DIFF_PACKAGES_LIST = diff_packages_list
    download_packages = ""

    for record_key in DIFF_PACKAGES_LIST:
        package, version = DIFF_PACKAGES_LIST[record_key]
        if version != None:
            download_packages = download_packages + " %s=%s" % (package,version)
        else:
            download_packages = download_packages + " %s" % (package,)

    output = run('apt-get install --force-yes -y --download-only%s' % (download_packages,))

    ls_out = run("ls /var/cache/apt/archives/ | grep '.deb'")
    
    ls_out = string.replace(ls_out, "\r", "")
    ls_out = string.split(ls_out, "\n")
    
    while True:
        print "\n"
        for package in ls_out:
            print "%s" % (package)
        print "\nbalicky jsou stazene ve /var/cache/apt/archives/\n"
        
        answer = raw_input('Chces uploadnout tyto baliky, oznacit baliky k odebrani, oznacit baliky k uploadu, neuploadovat (y/d/c/n): ')
        if answer == 'y':
            break
        elif answer == 'd':
            packages = raw_input('zadej baliky oddelene strednikem: ')
            packages = string.split(packages, ";")
            for package in packages:
                try:
                    ls_out.remove(package)
                except ValueError:
                    print "\nW: Balik %s nebyl v seznamu" % (package)
        elif answer == 'c':
            packages = raw_input('zadej baliky oddelene strednikem: ')
            packages = string.split(packages, ";")
            upload_packages = []
            error = 0
            for package in packages:
                if package in ls_out:
                    upload_packages.append(package)
                else:
                    print "\nW: Balik %s nebyl v seznamu" % (package)
                    error = 1
            if error == 0:
                ls_out = upload_packages
        elif answer == 'n':
            print "\nEXIT: Baliky nebudou uploadnuty\n"
            sys.exit(1)
        else:
            print "\nW: Spatna volba"
            continue
    
    return ls_out

def upload_packages(packages_for_upload, domain_username='', rdir = '', upload_url = ''):
    """
    This function uploaded packages to operation repo and it is running on clean machine 
    Has one argument the windows domain name 
    """

    if domain_username =='':
        USER = raw_input('domain user name: ')
    else:
        USER = domain_username
    
    if rdir == '':
        rdir = RDIR
        
    if upload_url == '':
        url = URL
    
    
    packages_for_upload = string.join(packages_for_upload, " ")

    output = run('lftp %(scheme)s://%(user)s@%(url)s -e "\n\
		  set ftp:ssl-protect-data yes\n\
		  lcd %(ldir)s\n\
		  mkdir -p %(rdir)s\n\
		  cd %(rdir)s\n\
		  mkdir -p %(today)s\n\
		  cd %(today)s\n\
		  mput %(packages_for_upload)s\n\
		  ls\n\
		  exit" | awk "{print $9}"' % {
			    "scheme": SCHEME,
			    "user": USER,
			    "url": url,
			    "ldir": LDIR,
			    "rdir": rdir,
			    "today": TODAY,
			    "packages_for_upload": packages_for_upload
			    })
    if output.return_code != 0:
        abort("Aborting, can not upload packages:")
    print "\nbalicky jsou uploadnute v %s://%s/%s/%s" % (SCHEME,URL,RDIR,TODAY)


def getlistpackages(dpkgl_file):
    """
    This function process output of dpkg -l and return dictionary of installed software
    """

    result = {}
    for line in dpkgl_file:
        row = string.split(line, ";")
        if len(row) > 1:
            #package, version = checkversion(row[0], row[1])
            result[row[0]] = [row[0], row[1]]
    dpkgl_file.close()
    return result

def getlistpackageslocal(dpkgl_file):
    """
    This function process output of dpkg -l from URL and return dictionary of installed software
    """

    result = {}
    dpkgl_array = string.split(dpkgl_file, "\n")
    for line in dpkgl_array:
        row = string.split(line, ";")
        if len(row) > 1: 
            result[row[0]] = [row[0], row[1]]
    return result

def install_production_packages(clean_machine, production_machine, spectator_password=''):
    """
    This function get dpkg -l from url from production and install it including versions
    """
    sys_info = run("uname -a")
    sys_info = string.split(sys_info, " ")
    architecture = sys_info[-2]
    if string.find(architecture, "i386") == -1 and string.find(architecture, "i686") == -1:
        print "\nUnsupported architecture\n" 
        sys.exit(1)
    
    dpkgl_file = urllib.urlopen('http://spectator:%s@cml.tunel.chservices.cz/cgi-bin/dpkg.pl?host=%s' % (spectator_password, production_machine))
    PACKAGES_LIST = getlistpackages(dpkgl_file)

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    clean_machine = string.split(clean_machine, "@")
    client.connect(clean_machine[1],  username=clean_machine[0])
    local_list = {}
    local_list.update(PACKAGES_LIST)
    while True:
        install_packages = ""
        for key in local_list:
            package, version = local_list[key]
            if version != None:
                install_packages = install_packages + " %s=%s" % (package,version)
            else:
                install_packages = install_packages + " %s" % (package,)
	
        command_exec = 'apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" --force-yes -y%s' % (install_packages,)
        #print "\nPACK: "+command_exec+"\n"
        stdin, stdout, stderr = client.exec_command(command_exec)
        remote_error = None
	
        list_depends = []
	
        for o in stdout:
            if string.find(o, "Depends:") != -1:
                list_depends.append(o)
            print "\n" + str(o)

        for e in stderr:
            remote_error = e

        if remote_error != None:
            print "\n" + str(remote_error)
        else:
            break

        remote_error = string.split(remote_error," ")
        if remote_error[0] != "E:":
            client.close()
            break
        elif remote_error[1] == "Version":
            package = string.replace(remote_error[4], "'", "")
            local_list[package][1] = None
        elif remote_error[1] == "Broken":
            for element in list_depends:
                #print "\n" +str(element)+ "\n"
                if string.find(element, "is to be installed") != -1:
                    package = string.split(element, " ")[4]
                    backport_line = run("apt-cache policy %s | grep '~bpo' | sed 's/ \{2,\}//g'" % (package))
                    versions_list = string.replace(backport_line, "\n", " ")
                    versions_list = string.replace(versions_list, "\r", " ")
                    versions = string.split(versions_list, " ")
                    #print versions
                    for element in versions:
                        if string.find(element, "~bpo") != -1:
                            #print element
                            local_list[package][1] = element
                            break
        elif string.find(string.join(remote_error, " "), "has no installation candidate") != -1:
            package = remote_error[2]
            del(local_list[package])
        elif string.find(string.join(remote_error, " "), "Couldn't find package") != -1:
            package = string.replace(remote_error[-1], "\n", "")
            del(local_list[package])
        
        else:
            print "\nUnknown error"
            break
	
    client.close()
    return PACKAGES_LIST


def install_project(project, project_version=''):
    """
    This function take -be, -fe, -img for given project, if the version is not given we get the latest version from devel repository
    """
    DEPS='%s-config python-django=1.1.1-1~bpo50+1' %(project) 
    if project_version != '':
        run('apt-get install --force-yes -y %(project)s-img=%(project_version)s %(project)s-be=%(project_version)s %(project)s-fe=%(project_version)s %(DEPS)s' % {
	    "project" : project, 
	    "project_version" : project_version,
	    "DEPS" : DEPS
	    })
    else:
        run('apt-get install --force-yes -y %(project)s-img %(project)s-be %(project)s-fe %(DEPS)s' % {
	    "project" : project,
	    "DEPS" : DEPS
	    })


def execute_diff_packages(packages_list, unwanted_packages='mypage;ella'):
    """
    This function execute diff preproduction and production dpkg -l list and remove packages from diff that are in standard debian repository
    it is running on preproduction machine
    """
    DIFF_PACKAGES_LIST = execute_diff(packages_list)
    DIFF_PACKAGES_LIST = clean_diff(DIFF_PACKAGES_LIST, unwanted_packages)

    return DIFF_PACKAGES_LIST

def execute_diff(packages_list):
    """
    This function execute diff local and production dpkg -l list
    """
    DIFF_PACKAGES_LIST = {}
    PACKAGES_LIST = packages_list

    local_dpkgl = run("dpkg -l | grep '^ii  ' | sed 's/^ii  //' | sed 's/ \{2,\}/;/g'")
    packages_list_local = getlistpackageslocal(local_dpkgl)
    
    for record in packages_list_local:
        if PACKAGES_LIST.has_key(record) == False:
            DIFF_PACKAGES_LIST[record] = packages_list_local[record]
        elif packages_list_local[record][1] != PACKAGES_LIST[record][1]:
            DIFF_PACKAGES_LIST[record] = packages_list_local[record]

    return DIFF_PACKAGES_LIST

def clean_diff(diff_packages_list, unwanted_packages):
    """
    This function remove packages from diff that are in standard debian repository 
    """
    
    DIFF_PACKAGES_LIST = diff_packages_list
    # remove unwanted packages
    delete_records = []
    unwanted_records = string.split(unwanted_packages, ";")
    for record in DIFF_PACKAGES_LIST:
        for element in unwanted_records:
            if string.find(record, element) != -1:
                delete_records.append(record)

    # remove packages from standard debian repository
    for record in DIFF_PACKAGES_LIST:
        if record in delete_records:
            continue
        urls = run("apt-cache policy %s | grep http:// | sed 's/ \{2,\}//'" % (DIFF_PACKAGES_LIST[record][0]))
        if string.find(urls, "E: Cache is out of sync") != -1:
            delete_records.append(record)
            continue
        urls = string.split(urls, "\n")
        disable_url = 0
        enable_url = 0
        for url in urls:
            try:
                url = string.split(url, " ")[1]
            except IndexError:
                continue
            if url in DISABLE_URL:
                disable_url = disable_url + 1
            else:
                enable_url = enable_url + 1
        if disable_url > 0 and enable_url == 0:
            delete_records.append(record)
    
    for record in delete_records:
        del(DIFF_PACKAGES_LIST[record])
    # for debuging
    #for r in DIFF_PACKAGES_LIST:
    #    print "\n"+str(DIFF_PACKAGES_LIST[r])

    return DIFF_PACKAGES_LIST
