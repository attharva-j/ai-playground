#!/bin/bash

tempdir=$(mktemp -d)
cd $tempdir

case $(uname -m) in
    x86_64)
        ARCH=amd64 ;;
    aarch64|arm64)
        ARCH=arm64 ;;
esac

echo 'ae403e3b0355dac23d70f1b082a9da4eff9c3592daae5523b4eedd5ebc2badd4  opa_darwin_arm64_static.sha256
e024b928f0059fec3a4ccfa47ed824e908312f84f4872d5b2f5d55c96d12af1d  opa_linux_amd64_static.sha256
a253ffaf933f8a5020a066c38cbeaed56bc22556418470c48040be955be78522  opa_linux_arm64_static.sha256' > checksums.txt

VERSION=v1.4.2
BASE_URL=https://github.com/open-policy-agent/opa/releases/download/$VERSION
BASE_PACKAGE=opa_$(uname | awk '{print tolower($0)}')_${ARCH}_static

curl -fsSLO $BASE_URL/$BASE_PACKAGE.sha256
sha256sum --ignore-missing -c checksums.txt
curl -fsSLO $BASE_URL/$BASE_PACKAGE
sha256sum -c $BASE_PACKAGE.sha256
chmod +x $BASE_PACKAGE
mv $BASE_PACKAGE /usr/local/bin/opa

cd -
rm -rf $tempdir

