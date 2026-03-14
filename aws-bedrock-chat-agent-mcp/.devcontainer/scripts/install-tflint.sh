#!/bin/bash

set -e

tempdir=$(mktemp -d)
cd $tempdir

case $(uname -m) in
    x86_64)
        ARCH=amd64 ;;
    aarch64|arm64)
        ARCH=arm64 ;;
esac

VERSION=v0.58.0
BASE_URL=https://github.com/terraform-linters/tflint/releases/download/$VERSION
PACKAGE_NAME=tflint_$(uname | awk '{print tolower($0)}')_$ARCH.zip

curl -fsSLO $BASE_URL/checksums.txt
curl -fsSLO $BASE_URL/checksums.txt.keyless.sig
curl -fsSLO $BASE_URL/checksums.txt.pem

cosign \
    verify-blob \
    --certificate-identity "https://github.com/terraform-linters/tflint/.github/workflows/release.yml@refs/tags/$VERSION" \
    --signature checksums.txt.keyless.sig \
    --certificate checksums.txt.pem \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    checksums.txt


# Download the appropriate package
curl -fsSLO "$BASE_URL/$PACKAGE_NAME"
sha256sum --ignore-missing -c checksums.txt
unzip $PACKAGE_NAME
sudo mv tflint /usr/local/bin/tflint
cd -
rm -rf $tempdir

# Verify installation
tflint --version
