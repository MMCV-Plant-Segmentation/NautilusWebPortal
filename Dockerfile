FROM ubuntu:26.04

RUN apt-get update -y && apt-get install -y curl

USER ubuntu
WORKDIR /home/ubuntu

RUN mkdir -p .local/bin
ENV PATH="$PATH:/home/ubuntu/.local/bin"

COPY --from=tools-build /home/ubuntu/.local/bin/kubectl          .local/bin/kubectl
COPY --from=tools-build /home/ubuntu/.local/bin/kubectl-oidc_login .local/bin/kubectl-oidc_login

# Install uv so that we can use python
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies (before copying app code for layer caching).
# --no-install-project skips building the local package (source not present yet).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Create the folder where the database will live (here so that ubuntu owns the file)
RUN mkdir -p ~/nwp

# Copy application code, then install the project itself (no new downloads needed)
COPY nautilus_web_portal/ ./nautilus_web_portal/
COPY app.py kubewrapper.py ./
RUN uv sync --frozen

COPY --from=frontend-build /app/dist ./frontend/dist

CMD ["uv", "run", "python", "app.py"]
