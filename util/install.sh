#!/usr/bin/env bash

# Installation script for Ubuntu, Debian, CentOS and Fedora

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

PROJ=easyovs
EXEC=bin/easyovs

#DO NOT CHANGE THE FOLLOWING PART


# Get the working directory of the project
WORK_DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../../easyOVS" && pwd -P )"

# Set up build directory, which by default is the working directory
# unless the working directory is a subdirectory,
# in which case we use the directory containing the project
BUILD_DIR="$(pwd -P)"
case $BUILD_DIR in
  $WORK_DIR/../*) BUILD_DIR=$WORK_DIR/../;; # currect directory is a
  # subdirectory
  *) BUILD_DIR=$BUILD_DIR;;
esac

# Attempt to identify Linux release
DIST=Unknown
RELEASE=Unknown
CODENAME=Unknown
ARCH=`uname -m`
if [ "$ARCH" = "x86_64" ]; then ARCH="amd64"; fi
if [ "$ARCH" = "i686" ]; then ARCH="i386"; fi

[ -e /etc/debian_version ] && DIST="Debian"
grep Ubuntu /etc/lsb-release &> /dev/null && DIST="Ubuntu"
if [ "$DIST" = "Ubuntu" ] || [ "$DIST" = "Debian" ]; then
    install='sudo apt-get -y install'
    remove='sudo apt-get -y remove'
    pkginst='sudo dpkg -i'
    [ -z `which lsb_release 2>/dev/null` ] &&  $install lsb-release >/dev/null
fi
[ -e /etc/fedora-release ] && DIST="Fedora"
[ -e /etc/centos-release ] && DIST="CentOS"
[ -e /etc/redhat-release ] && DIST="Redhat"
if [ "$DIST" = "Fedora" -o  "$DIST" = "CentOS"  -o  "$DIST" = "Redhat" ]; then
    install='sudo yum -y install'
    remove='sudo yum -y erase'
    pkginst='sudo rpm -ivh'
    # Prereqs for this script
    [ -z `which lsb_release 2>/dev/null` ] &&  $install redhat-lsb-core
    >/dev/null
fi

if [ "$DIST" = "Ubuntu" -o "$DIST" = "Debian" -o "$DIST" = "Fedora" -o "$DIST" = "CentOS" -o  "$DIST" = "Redhat" ]; then
	echo "Dist = $DIST"
    KERNEL_NAME=`uname -r`
    KERNEL_HEADERS=linux-headers-${KERNEL_NAME}
else
    echo "Currently only supports Ubuntu, Debian, CentOS, Redhat and Fedora."
    exit 1
fi

if which lsb_release &> /dev/null; then
    DIST_FULL=`lsb_release -is`
    RELEASE=`lsb_release -rs`
    CODENAME=`lsb_release -cs`
fi
echo "Detected Linux distribution: $DIST_FULL $RELEASE $CODENAME $ARCH"

# Install core
function core {
    echo "###Installing ${PROJ} core files, working dir is $WORK_DIR"
    pushd $WORK_DIR
    chmod a+x ${EXEC}
    [ -f /etc/easyovs.conf ] || cp $WORK_DIR/etc/easyovs.conf /etc/
    make install
    popd
}

# Install deps
function dep {
    echo "###Installing ${PROJ} dependencies"
	if [ "$DIST" = "Fedora" -o "$DIST" = "CentOS" -o  "$DIST" = "Redhat" ]; then
        $install gcc make python-devel python-setuptools python-pip pyflakes pylint python-pep8 > /dev/null
    elif [ "$DIST" = "Ubuntu" -o "$DIST" = "Debian" ]; then
        $install gcc make python-dev python-setuptools python-pip help2man pyflakes pylint pep8 >  /dev/null
    fi
}

# Install ${PROJ} developer dependencies
function dev {
    echo "###Installing ${PROJ} developer dependencies"
    $install doxygen doxypy
}

function all {
    echo "###Installing the dependencies and the core packages..."
    dep
    core
    # Skip dev (doxypy) because it's huge
    # dev
    if [ -f ~/keystonerc_admin ]; then
     source ~/keystonerc_admin
    else
     echo "To enable the OpenStack feature, please source your keystonerc_admin credentials."
    fi
    echo "Enjoy ${PROJ}!"
}

# Uninstall the package
function uninstall {
    echo "Uninstalling the package"
    pushd $WORK_DIR
    sudo make uninstall
    popd
}

function usage {
    printf '\nUsage: %s [-adehpsu]\n\n' $(basename $0) >&2

    printf 'This install script attempts to install useful packages\n' >&2
    printf 'for ${PROJ}. It should work on Ubuntu 11.10+ or CentOS 6.5+\n' >&2
    printf 'If run into trouble, try installing one thing at a time,\n' >&2
    printf 'and looking at the specific function in this script.\n\n' >&2

    printf 'options:\n' >&2
    printf -- ' -a: (default) install (A)ll packages - good luck!\n' >&2
    printf -- ' -e: install ${PROJ} d(E)veloper dependencies\n' >&2
    printf -- ' -h: print this (H)elp message\n' >&2
    printf -- ' -p: install ${PROJ} de(P)endencies\n' >&2
    printf -- ' -s <dir>: place dependency (S)ource/build trees in <dir>\n' >&2
    printf -- ' -u: (U)pgrade, only install ${PROJ} core files\n' >&2
    printf -- ' -d: (D)elete, uninstall the package\n' >&2
    exit 2
}

if [ $# -eq 0 ]
then
    all
else
    while getopts 'adehpsu' OPTION
    do
      case $OPTION in
      a)    all;;
      d)    uninstall;;
      e)    dev;;
      h)    usage;;
      p)    dep;;
      s)    mkdir -p $OPTARG; # ensure the directory is created
            BUILD_DIR="$( cd -P "$OPTARG" && pwd )"; # get the full path
            echo "Dependency installation directory: $BUILD_DIR";;
      u)    core;;
      ?)    usage;;
      esac
    done
    shift $(($OPTIND - 1))
fi
