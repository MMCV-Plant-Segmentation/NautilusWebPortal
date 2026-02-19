```sh
$ docker image build --tag nautilus-web-portal .
# `docker image list` should now display `nautilus-web-portal:latest`

$ docker container run --interactive --tty --rm nautilus-web-portal
```