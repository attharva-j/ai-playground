#!/bin/bash

set -e

export PATH=${PATH}:`go env GOPATH`/bin

tempdir=$(mktemp -d)
cd $tempdir

curl -o sigstore-root.json https://raw.githubusercontent.com/sigstore/root-signing/refs/heads/main/metadata/root_history/10.root.json
go install github.com/theupdateframework/go-tuf/cmd/tuf-client@latest
tuf-client init https://tuf-repo-cdn.sigstore.dev sigstore-root.json
case $(uname -m) in
    x86_64)
        ARCH=amd64 ;;
    aarch64|arm64)
        ARCH=arm64 ;;
esac
LATEST_VERSION=$(curl https://api.github.com/repos/sigstore/cosign/releases/latest | jq -r .tag_name | tr -d "v")
curl -o cosign-release.sig -L https://github.com/sigstore/cosign/releases/download/v$LATEST_VERSION/cosign-linux-$ARCH.sig
base64 -d cosign-release.sig > cosign-release.sig.decoded
tuf-client get https://tuf-repo-cdn.sigstore.dev artifact.pub > artifact.pub
curl -o cosign -L https://github.com/sigstore/cosign/releases/download/v$LATEST_VERSION/cosign-linux-$ARCH
openssl dgst -sha256 -verify artifact.pub -signature cosign-release.sig.decoded cosign
chmod +x cosign
mv cosign /usr/local/bin/cosign

cd -
rm -rf $tempdir
