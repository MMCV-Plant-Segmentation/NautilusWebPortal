```sh
# --- One-time setup on Calliope ---

# Create the shared directory used for the auth socket
$ sudo mkdir -p /var/nwp && sudo chmod 777 /var/nwp

# Install the nwp-connect script
$ sudo cp nwp-connect /usr/local/bin/nwp-connect && sudo chmod 755 /usr/local/bin/nwp-connect


# --- Build and start the portal ---

# Build the image and start the container (add --build to force a rebuild)
$ docker compose up -d

# To stop the portal:
$ docker compose down


# --- Add a user (once per user, inside the container) ---

# Open a shell in the running container
$ docker compose exec portal bash

# (Within the container) Create the kubernetes configuration folder
$ mkdir ~/Downloads

# (Outside the container) Open the following URL in the browser: https://nrp.ai/config

# (Outside the container) Copy the config from the host into the container
$ tar --create --file=- --directory ~/Downloads/ config | docker compose exec --user ubuntu portal sh -c "tar --extract --file=- --directory ~/Downloads/ --no-same-owner --no-same-permissions"

# (Within the container) Add a user with the configuration file you just copied.
$ uv run kubewrapper.py add_user <username> ~/Downloads/config

# (Within the container) Trigger the log in process with a dummy command.
$ uv run kubewrapper.py run_as <username> get nodes


# --- Accessing the portal ---

# From your local machine, run this — it sets up the SSH tunnel and prints a login URL.
# Open the URL in your browser within 60 seconds.
$ ssh -L 8080:localhost:5000 calliope.rnet.missouri.edu nwp-connect


# --- Useful commands ---

# View live logs
$ docker compose logs -f

# Open a shell in the running container
$ docker compose exec portal bash
```
