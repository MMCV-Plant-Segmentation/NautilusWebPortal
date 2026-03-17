```sh
# Build the docker image
$ docker image build --tag nautilus-web-portal .
# `docker image list` should now display `nautilus-web-portal:latest`

# Instantiate a temporary container using that image and open an interactive shell within it
## --interactive --tty means that the shell you get put in will accept input, including terminal escape sequences
## --rm means the container is temporary and will be deleted when you kill it
## --name specifies the name to give the container so you can reference it
## (Alternatively you can fetch the ID with: docker container ls --quiet --filter 'ancestor=nautilus-web-portal')
$ docker container run --interactive --tty --rm --name nwp-container nautilus-web-portal

# (Within the container) Create the kubernetes configuration folder
$ mkdir ~/Downloads

# (Outside the container) Open the following URL in the browser: https://nrp.ai/config

# (Outside the container) Copy the config from the host into 
$ tar --create --file=- --directory ~/Downloads/ config | docker exec --interactive --user ubuntu nwp-container sh -c "tar --extract --file=- --directory ~/Downloads/ --no-same-owner --no-same-permissions"

# This doesn't work because of annoying ownership issues:
# $ docker container cp ~/Downloads/config nwp-container:/home/ubuntu/.kube/config

# (Within the container) Add a user with the configuration file you just copied.
$ uv run kubewrapper.py add_user <username> ~/Downloads/config

# (Within the container) Finally, trigger the log in process with a dummy command.
$ uv run kubewrapper.py run_as <username> get nodes

# If you ever need to open a second shell this might be useful:
$ docker container exec --interactive --tty nwp-container bash
```