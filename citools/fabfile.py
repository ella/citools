"""
This script take list of packages from operation list and list of packages from preprodution
then do diff and send residual packages to production repo
Using fab compare_vs_production:args,host=cleanmachine_address execute_diff_packages:args,host=preproduction_address upload_packages:args,host=cleanmachine_address 
Example fab compare_vs_production:hp9fe1.cent,centrum-mypage-auto,host=clean.dev.chservices.cz execute_diff_packages:host=cms-hp9fe.dev.chservices.cz upload_packages:host=clean.dev.chservices.cz
"""

import string
import urllib
from datetime import datetime

from fabric.api import *
from fabric.contrib.console import confirm
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

DIFF_PACKAGES_LIST = {}
PACKAGES_LIST = {}

def download_diff_packages():
    """
    This function download packages from diff list 
    """
    global DIFF_PACKAGES_LIST

    for record_key in DIFF_PACKAGES_LIST:
	package, version = DIFF_PACKAGES_LIST[record_key]
	output = run('apt-get install --force-yes -y --download-only %s=%s' % (package,version))

    ls_out = run('ls /var/cache/apt/archives/')
    print ls_out
    print "\nbalicky jsou stazene ve /var/cache/apt/archives/\n"

def upload_packages(domain_username=''):
    """
    This function uploaded packages to operation repo and it is running on clean machine 
    Has one argument the windows domain name 
    """
    download_diff_packages()

    if domain_username =='':
	USER = raw_input('domain user name: ')
    else:
	USER = domain_username
    
    output = run('lftp %(scheme)s://%(user)s@%(url)s -e "\n\
		  set ftp:ssl-protect-data yes\n\
		  lcd %(ldir)s\n\
		  mkdir -p %(rdir)s\n\
		  cd %(rdir)s\n\
		  mkdir -p %(today)s\n\
		  cd %(today)s\n\
		  mput *deb\n\
		  ls\n\
		  exit" | awk "{print $9}"' % {
			    "scheme": SCHEME,
			    "user": USER,
			    "url": URL,
			    "ldir": LDIR,
			    "rdir": RDIR,
			    "today": TODAY
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

def install_production_packages(production_machine, spectator_password)
    """
    This function get dpkg -l from url from production and install it including versions
    """
    global PACKAGES_LIST

    if spectator_password =='':
	PASSWORD = raw_input('spectator password: ')
    else:
	PASSWORD = spectator_password

    dpkgl_file = urllib.urlopen('http://spectator:%s@cml.tunel.chservices.cz/cgi-bin/dpkg.pl?host=%s' % (PASSWORD, production_machine))
    PACKAGES_LIST = getlistpackages(dpkgl_file)

    for record_key in PACKAGES_LIST:
	package, version = PACKAGES_LIST[record_key]
	output = run('apt-get install --force-yes -y %s=%s' % (package,version))
	if output.return_code != 0:
	    abort("Aborting, can not install %s in version %s." % (package,version))



def install_project(project, project_version):
     """
    This function take -be, -fe, -img for given project, if the version is not given we get the latest version from devel repository
    """
    if project_version != '':
	specific_version = "="
    else:
	specific_version = ""
    run('apt-get install --force-yes -y %s-img%s%s' % (project, specific_version, project_version))
    run('apt-get install --force-yes -y %s-be%s%s' % (project, specific_version, project_version))
    run('apt-get install --force-yes -y %s-fe%s%s' % (project, specific_version, project_version))


def execute_diff_packages(unwanted_packages='mypage;ella'):
    """
    This function execute diff preproduction and production dpkg -l list and remove packages from diff that are in standard debian repository
    it is running on preproduction machine
    """
    execute_diff()
    clean_diff(unwanted_packages)

def execute_diff():
    """
    This function execute diff local and production dpkg -l list
    """
    global DIFF_PACKAGES_LIST
    global PACKAGES_LIST

    local_dpkgl = run("dpkg -l | grep '^ii  ' | sed 's/^ii  //' | sed 's/ \{2,\}/;/g'")
    packages_list_local = getlistpackageslocal(local_dpkgl)
    
    for record in packages_list_local:
	if PACKAGES_LIST.has_key(record) == False:
	    DIFF_PACKAGES_LIST[record] = packages_list_local[record]
	elif packages_list_local[record][1] != PACKAGES_LIST[record][1]:
	    DIFF_PACKAGES_LIST[record] = packages_list_local[record]

def clean_diff(unwanted_packages):
    """
    This function remove packages from diff that are in standard debian repository 
    """
    global DIFF_PACKAGES_LIST

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
	url = run("apt-cache policy %s | grep http:// | sed 's/ \{2,\}//'" % (DIFF_PACKAGES_LIST[record][0]))
	try:
	    url = string.split(url, " ")[1]
	except IndexError:
	    continue
	if url in DISABLE_URL:
	    delete_records.append(record)
    
    for record in delete_records:
	del(DIFF_PACKAGES_LIST[record])
    

def compare_vs_production(production_machine, project, project_version='', spectator_password=''):
    """
    This function send packages to operation repository, this is difference local dpkg -l and dpkg -l from URL 
    First argument is the name of production_machine for that you want dpkg -l
    Second argument is the name of project
    Third and fourth are optional, third is project version and fourth is windows domain user name
    """

    # This script is running on clear machine
    # get dpkg -l from url from production and install it including versions
    install_production_packages(production_machine, spectator_password)
    
    # Take -be, -fe, -img for given project, if the version is not given we get the latest version from devel repository
    run('rm /var/cache/apt/archives/* &>/dev/null')
    install_project(project, project_version)
