FROM mcr.microsoft.com/devcontainers/base:jammy

COPY ./scripts/zsroot.crt /usr/local/share/ca-certificates/

RUN sudo apt-get install -y ca-certificates && sudo update-ca-certificates
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
ENV AWS_CA_BUNDLE=$NODE_EXTRA_CA_CERTS
ENV REQUESTS_CA_BUNDLE=$NODE_EXTRA_CA_CERTS

# Go for Cosign Instalation
COPY ./scripts/install-go.sh /opt/devcontainer-scripts/install-go.sh
RUN bash /opt/devcontainer-scripts/install-go.sh
ENV PATH=$PATH:/usr/local/go/bin

# Cosign for Verification
COPY ./scripts/install-cosign.sh /opt/devcontainer-scripts/install-cosign.sh
RUN bash /opt/devcontainer-scripts/install-cosign.sh

# tenv for OpenTofu Version Management
COPY ./scripts/install-tenv.sh /opt/devcontainer-scripts/install-tenv.sh
RUN bash /opt/devcontainer-scripts/install-tenv.sh

# Python
COPY ./scripts/install-python.sh /opt/devcontainer-scripts/install-python.sh
RUN bash /opt/devcontainer-scripts/install-python.sh
RUN /usr/local/py-utils/bin/pipx install pre-commit

# TFLint
COPY ./scripts/install-tflint.sh /opt/devcontainer-scripts/install-tflint.sh
RUN bash /opt/devcontainer-scripts/install-tflint.sh

# TFDocs
COPY ./scripts/install-tfdocs.sh /opt/devcontainer-scripts/install-tfdocs.sh
RUN bash /opt/devcontainer-scripts/install-tfdocs.sh

# OPA
COPY ./scripts/install-opa.sh /opt/devcontainer-scripts/install-opa.sh
RUN bash /opt/devcontainer-scripts/install-opa.sh

# AWS CLI
COPY ./devcontainers-features/src/aws-cli /opt/devcontainer-scripts/aws-cli
RUN cd /opt/devcontainer-scripts/aws-cli && bash install.sh

# kubectl
COPY ./scripts/install-kubectl.sh /opt/devcontainer-scripts/install-kubectl.sh
RUN bash /opt/devcontainer-scripts/install-kubectl.sh

# kiro
USER vscode
RUN curl -fsSL https://cli.kiro.dev/install | bash

# # helm
# COPY ./scripts/install-helm.sh /opt/devcontainer-scripts/install-helm.sh
# RUN bash /opt/devcontainer-scripts/install-helm.sh
