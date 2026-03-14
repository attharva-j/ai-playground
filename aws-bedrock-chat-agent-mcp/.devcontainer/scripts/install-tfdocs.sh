#!/bin/bash

set -e

case $(uname -m) in
    x86_64)
        ARCH=amd64 ;;
    aarch64|arm64)
        ARCH=arm64 ;;
esac

CHECKSUMS_SHASUM='834a5c68a5b44593a2a9da13bda3407b85d2d0e165c8c20cb7a8e4dc18b0e84c  terraform-docs-v0.20.0.sha256sum'
VERSION=v0.20.0
BASE_PACKAGE_NAME=terraform-docs-$VERSION
BASE_URL=https://github.com/terraform-docs/terraform-docs/releases/download/$VERSION
TGZ_PACKAGE_NAME=$BASE_PACKAGE_NAME-$(uname | awk '{print tolower($0)}')-$ARCH.tar.gz

tempdir=$(mktemp -d)
cd $tempdir
curl -fsSLO $BASE_URL/$BASE_PACKAGE_NAME.sha256sum
echo $CHECKSUMS_SHASUM | sha256sum -c
curl -fsSLO $BASE_URL/$TGZ_PACKAGE_NAME
sha256sum --ignore-missing -c $BASE_PACKAGE_NAME.sha256sum
tar -xzf $TGZ_PACKAGE_NAME
chmod +x terraform-docs
sudo mv terraform-docs /usr/local/bin/terraform-docs
cd -
rm -rf $tempdir
