FROM ubuntu:26.04

RUN apt-get update -y
RUN apt-get install -y curl

WORKDIR /home/ubuntu

# Install `kubectl` according to the instructions here:
# https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-kubectl-binary-with-curl-on-linux

# TODO: At some point KUBECTL_VERSION should be pinned
RUN KUBECTL_VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)" && curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
RUN install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

RUN mkdir -p /home/ubuntu/.local/bin
ENV PATH="$PATH:/home/ubuntu/.local/bin"

# Download `kubelogin` from GitHub released (https://github.com/int128/kubelogin/releases)
# I don't know of a way to get the latest version for this, so we're effectively pinned anyway!
ENV KUBELOGIN_DOWNLOAD_LINK=https://github.com/int128/kubelogin/releases/download/v1.35.2/kubelogin_linux_amd64.zip
RUN curl --location --output /home/ubuntu/.local/bin/kubectl-oidc_login "${KUBELOGIN_DOWNLOAD_LINK}"

