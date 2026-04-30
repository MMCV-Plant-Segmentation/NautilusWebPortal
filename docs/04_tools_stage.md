# Tools Build Stage

Extract kubectl and kubelogin installation into a dedicated `tools/Dockerfile` so those layers cache independently from the Python app.

## Motivation

The main `Dockerfile` currently has ~12 lines of `RUN` commands to download and install `kubectl` and `kubelogin`. These are stable, self-contained binaries that rarely change — but they sit in the middle of the Ubuntu image's layer stack, meaning any change to those lines (e.g. a version bump) forces every subsequent layer to rebuild. Moving them to their own Bake target isolates their cache entirely.

## Approach

Add `tools/Dockerfile` (Ubuntu 26.04, same base as `app`):

```dockerfile
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
```

Add `tools` target to `docker-bake.hcl` and declare it as a named context for `app`:

```hcl
target "tools" {
  context    = "./tools"
  dockerfile = "Dockerfile"
}

target "app" {
  context  = "."
  contexts = {
    frontend-build = "target:frontend"
    tools-build    = "target:tools"
  }
  tags = ["nautiluswebportal-nwp:latest"]
}
```

Replace the kubectl/kubelogin `RUN` blocks in the main `Dockerfile` with two `COPY` lines, and drop `unzip` from apt (only needed in the tools stage now):

```dockerfile
COPY --from=tools-build /home/ubuntu/.local/bin/kubectl       .local/bin/kubectl
COPY --from=tools-build /home/ubuntu/.local/bin/kubectl-oidc_login .local/bin/kubectl-oidc_login
```

## kubectl pinning

`KUBECTL_VERSION` is now an `ARG` defaulting to `v1.36.0` (current stable as of 2026-04-30). To upgrade: bump the `ARG` default in `tools/Dockerfile`. To override at build time: `docker buildx bake --set tools.args.KUBECTL_VERSION=v1.37.0`.

## Implementation order

1. Create `tools/Dockerfile`
2. Update `docker-bake.hcl`
3. Update main `Dockerfile` (remove kubectl/kubelogin/unzip blocks; add two `COPY --from=tools-build`)
4. Update `CLAUDE.md` Docker build section to mention the tools stage
5. Verify `docker buildx bake` succeeds
6. Commit
