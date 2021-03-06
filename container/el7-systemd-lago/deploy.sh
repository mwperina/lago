#!/bin/bash -ex

shopt -s failglob
readonly rpm_dir="${1:?}"

(
    cd "$rpm_dir"
    rpms=(epel-release centos-release-qemu-ev)
    rpms+=($(ls *.rpm))
    yum install -y "${rpms[@]}"
    for pkg in "${rpms[@]}"; do
        rpm -V "${pkg%.rpm}"
    done
)

yum clean all
install -d -m 775 /lago-envs
