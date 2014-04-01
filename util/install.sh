#!/usr/bin/env bash

# EasyOVS install script for Ubuntu, Debian, CentOS and Fedora

# Fail on error
set -e

# Fail on unset var usage
set -o nounset

# Get directory containing easyovs folder
EASYOVS_DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd -P )"

# Set up build directory, which by default is the working directory
#  unless the working directory is a subdirectory of easyovs,
#  in which case we use the directory containing easyovs
BUILD_DIR="$(pwd -P)"
case $BUILD_DIR in
  $EASYOVS_DIR/*) BUILD_DIR=$EASYOVS_DIR;; # currect directory is a subdirectory
  *) BUILD_DIR=$BUILD_DIR;;
esac

# Attempt to identify Linux release
DIST=Unknown
RELEASE=Unknown
CODENAME=Unknown
ARCH=`uname -m`
if [ "$ARCH" = "x86_64" ]; then ARCH="amd64"; fi
if [ "$ARCH" = "i686" ]; then ARCH="i386"; fi

test -e /etc/debian_version && DIST="Debian"
grep Ubuntu /etc/lsb-release &> /dev/null && DIST="Ubuntu"
if [ "$DIST" = "Ubuntu" ] || [ "$DIST" = "Debian" ]; then
    install='sudo apt-get -y install'
    remove='sudo apt-get -y remove'
    pkginst='sudo dpkg -i'
    # Prereqs for this script
    if ! which lsb_release &> /dev/null; then
        $install lsb-release
    fi
fi
test -e /etc/fedora-release && DIST="Fedora"
test -e /etc/centos-release && DIST="CentOS"
if [ "$DIST" = "Fedora" -o  "$DIST" = "CentOS" ]; then
    install='sudo yum -y install'
    remove='sudo yum -y erase'
    pkginst='sudo rpm -ivh'
    # Prereqs for this script
    if ! which lsb_release &> /dev/null; then
        $install redhat-lsb-core
    fi
fi
if which lsb_release &> /dev/null; then
    DIST=`lsb_release -is`
    RELEASE=`lsb_release -rs`
    CODENAME=`lsb_release -cs`
fi
echo "Detected Linux distribution: $DIST $RELEASE $CODENAME $ARCH"

if [ "$DIST" = "Ubuntu" -o "$DIST" = "Debian" ]; then
    KERNEL_NAME=`uname -r`
    KERNEL_HEADERS=linux-headers-${KERNEL_NAME}
elif [ "$DIST" = "Fedora" -o  "$DIST" = "CentOS" ]; then
    KERNEL_NAME=`uname -r`
    KERNEL_HEADERS=kernel-headers-${KERNEL_NAME}
else
    echo "Install.sh currently supports Ubuntu, Debian, CentOS and Fedora."
    exit 1
fi

# Install EasyOVS deps
function eovs_deps {
    echo "Installing EasyOVS dependencies"
    if [ "$DIST" = "Fedora" -o "$DIST" = "CentOS" ]; then
        $install gcc make  python-setuptools help2man \
         pyflakes pylint python-pep8
    else
        $install gcc make python-setuptools help2man \
            pyflakes pylint pep8
    fi

    echo "Installing EasyOVS core"
    pushd $EASYOVS_DIR/easyOVS
    sudo make install
    popd
}

# Install EasyOVS developer dependencies
function eovs_dev {
    echo "Installing EasyOVS developer dependencies"
    $install doxygen doxypy
}

function all {
    echo "Installing all packages except for -e (Developer dependencies such as doxypy)..."
    eovs_deps
    # Skip eovs_dev (doxypy) because it's huge
    # eovs_dev
    echo "EasyOVS Installation Done!"
    echo "Enjoy EasyOVS!"
}

function usage {
    printf '\nUsage: %s [-abcdfhikmnprtvwx03]\n\n' $(basename $0) >&2

    printf 'This install script attempts to install useful packages\n' >&2
    printf 'for EasyOVS. It should work on Ubuntu 11.10+ or CentOS 6.5+\n' >&2
    printf 'If you run into trouble, try\n' >&2
    printf 'installing one thing at a time, and looking at the \n' >&2
    printf 'specific installation function in this script.\n\n' >&2

    printf 'options:\n' >&2
    printf -- ' -a: (default) install (A)ll packages - good luck!\n' >&2
    printf -- ' -e: install EasyOVS d(E)veloper dependencies\n' >&2
    printf -- ' -h: print this (H)elp message\n' >&2
    printf -- ' -o: install Easy(O)VS dependencies + core files\n' >&2
    printf -- ' -s <dir>: place dependency (S)ource/build trees in <dir>\n' >&2
    exit 2
}

if [ $# -eq 0 ]
then
    all
else
    while getopts 'abcdefhikmnprs:tvwx03' OPTION
    do
      case $OPTION in
      a)    all;;
      e)    eovs_dev;;
      h)    usage;;
      o)    eovs_deps;;
      s)    mkdir -p $OPTARG; # ensure the directory is created
            BUILD_DIR="$( cd -P "$OPTARG" && pwd )"; # get the full path
            echo "Dependency installation directory: $BUILD_DIR";;
      ?)    usage;;
      esac
    done
    shift $(($OPTIND - 1))
fi
