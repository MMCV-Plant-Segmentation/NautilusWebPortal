FROM ubuntu:26.04

RUN apt-get update -y && apt-get install -y curl unzip

USER ubuntu
WORKDIR /home/ubuntu
RUN mkdir -p .local/bin

ARG KUBECTL_VERSION=v1.36.0
RUN curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    install -m 0755 kubectl .local/bin/kubectl && \
    rm kubectl

ARG KUBELOGIN_VERSION=v1.35.2
RUN curl --location --output kubelogin.zip \
      "https://github.com/int128/kubelogin/releases/download/${KUBELOGIN_VERSION}/kubelogin_linux_amd64.zip" && \
    unzip -p kubelogin.zip kubelogin > .local/bin/kubectl-oidc_login && \
    chmod 0755 .local/bin/kubectl-oidc_login && \
    rm kubelogin.zip
