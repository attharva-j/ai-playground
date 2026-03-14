#!/bin/bash

set -e

case $(uname -m) in
    x86_64)
        ARCH=amd64 ;;
    aarch64|arm64)
        ARCH=arm64 ;;
esac

LATEST_VERSION=$(curl --silent https://api.github.com/repos/tofuutils/tenv/releases/latest | jq -r .tag_name)
BASE_URL=https://github.com/tofuutils/tenv/releases/download/$LATEST_VERSION/tenv_$LATEST_VERSION

# Get checksum files
curl --silent -OL ${BASE_URL}_checksums.txt
curl --silent -OL ${BASE_URL}_checksums.txt.sig
curl --silent -OL ${BASE_URL}_checksums.txt.pem

# Get DEB files
curl --silent -OL ${BASE_URL}_${ARCH}.deb
curl --silent -OL ${BASE_URL}_${ARCH}.deb.sig
curl --silent -OL ${BASE_URL}_${ARCH}.deb.pem

# Verify signatures
cosign \
    verify-blob \
    --certificate-identity "https://github.com/tofuutils/tenv/.github/workflows/release.yml@refs/tags/${LATEST_VERSION}" \
    --signature "tenv_${LATEST_VERSION}_checksums.txt.sig" \
    --certificate "tenv_${LATEST_VERSION}_checksums.txt.pem" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    "tenv_${LATEST_VERSION}_checksums.txt"

cosign \
    verify-blob \
    --certificate-identity "https://github.com/tofuutils/tenv/.github/workflows/release.yml@refs/tags/${LATEST_VERSION}" \
    --signature "tenv_${LATEST_VERSION}_${ARCH}.deb.sig" \
    --certificate "tenv_${LATEST_VERSION}_${ARCH}.deb.pem" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    "tenv_${LATEST_VERSION}_${ARCH}.deb"

dpkg -i "tenv_${LATEST_VERSION}_${ARCH}.deb"
tenv --version

