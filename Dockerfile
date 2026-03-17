FROM ubuntu:26.04

RUN apt-get update -y
RUN apt-get install -y curl
RUN apt-get install -y unzip

USER ubuntu
WORKDIR /home/ubuntu

RUN mkdir -p .local/bin
ENV PATH="$PATH:/home/ubuntu/.local/bin"

# Install `kubectl` according to the instructions here:
# https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-kubectl-binary-with-curl-on-linux

# TODO: At some point KUBECTL_VERSION should be pinned
RUN KUBECTL_VERSION="$(curl -L -s https://dl.k8s.io/release/stable.txt)" && curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
RUN install -m 0755 kubectl ~/.local/bin/kubectl
RUN rm kubectl

# Download `kubelogin` from GitHub released (https://github.com/int128/kubelogin/releases)
# I don't know of a way to get the latest version for this, so we're effectively pinned anyway!
# TODO: switch to using install here too
RUN mkdir kubelogin_install_dir
ENV KUBELOGIN_DOWNLOAD_LINK=https://github.com/int128/kubelogin/releases/download/v1.35.2/kubelogin_linux_amd64.zip
RUN curl --location --output kubelogin_install_dir/kubelogin.zip "${KUBELOGIN_DOWNLOAD_LINK}"
RUN unzip -p kubelogin_install_dir/kubelogin.zip kubelogin > kubelogin_install_dir/kubectl_kubelogin
RUN install -m 0755 kubelogin_install_dir/kubectl_kubelogin ~/.local/bin/kubectl-oidc_login
RUN rm -r kubelogin_install_dir

# Install uv so that we can use python
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY kubewrapper.py /home/ubuntu/