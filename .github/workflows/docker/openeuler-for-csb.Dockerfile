# syntax=docker/dockerfile:1
#
# Base image. Allow the caller to override it via env
#
ARG BASE_IMAGE=openeuler/openeuler:24.03-lts-sp3

FROM ${BASE_IMAGE}

#
# Install all required packages for CSB to work
#
RUN dnf install -y glibc-all-langpacks cmake perf sysstat sudo gcc \
                   moby-engine moby-client hiredis-devel jq \
                   hostname python3 python3-pip iproute lshw ethtool \
                   nvme-cli hdparm libcgroup-tools sudo git bubblewrap

#
# Reduce container disk space by dropping dnf data
#
RUN dnf clean all

#
# Docker-specific setup: install disable PAM authentication on sudo
#
RUN set -eux; \
    echo 'auth sufficient pam_permit.so' > /etc/pam.d/sudo && \
    echo 'account sufficient pam_permit.so' >> /etc/pam.d/sudo && \
    echo 'session sufficient pam_permit.so' >> /etc/pam.d/sudo && \
    echo 'Double check if sudo works' | sudo tee /tmp/sudo_test.txt

#
# Create a temp dir with venv on it.
#

WORKDIR /src
COPY . .

RUN ./scripts/prepare.sh
RUN mv ./venv /venv
RUN rm -rf /src .cache/pip/

WORKDIR /home/csb

VOLUME /home/csb

#
# Add an entry point. Helpful for tests
#

CMD ["bash"]
