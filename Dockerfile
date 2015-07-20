# This will generate an image with the easyOVS installed.
# see: https://github.com/yeasy/easyOVS

FROM ubuntu:14.04
MAINTAINER Baohua Yang

ENV DEBIAN_FRONTEND noninteractive
ENV TZ Asia/Shanghai

USER root

# install needed software
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
RUN apt-get update && \
apt-get install pep8 pyflakes python2.7-dev python-pip git openvswitch-switch -y && \
rm -rf /var/cache/apt/

# update the pypi mirror
RUN mkdir ~/.pip/ && echo "[global]" > ~/.pip/pip.conf && \
echo "index-url = http://mirrors.aliyun.com/pypi/simple/" >> ~/.pip/pip.conf

RUN git clone https://github.com/yeasy/easyOVS.git master && \
bash easyOVS/util/install.sh

VOLUME ["/var/run/openvswitch/"]

CMD [ "/usr/local/bin/easyovs" ]