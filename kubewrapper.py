import json, os, shutil, subprocess, sys


def kubeconfig_path(username):
    return os.path.expanduser(f"~/.kube/users/{username}/config")


def add_user(username, source_config_path):
    dest = kubeconfig_path(username)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(source_config_path, dest)

    env = {**os.environ, "KUBECONFIG": dest}

    args = json.loads(subprocess.check_output(
        ["kubectl", "config", "view", "--raw", "-o", "jsonpath={.users[?(@.name=='oidc')].user.exec.args}"],
        env=env,
    ))
    args += [
        "--skip-open-browser",
        "--grant-type=device-code",
        "--token-cache-storage=disk",
        f"--token-cache-dir={os.path.expanduser(f'~/.kube/users/{username}/token-cache')}",
    ]

    flags = [f'--exec-arg="{a}"' for a in args]
    subprocess.run(["kubectl", "config", "set-credentials", "oidc"] + flags, env=env)


def run_as(username, kubectl_args):
    env = {**os.environ, "KUBECONFIG": kubeconfig_path(username)}
    subprocess.run(["kubectl"] + kubectl_args, env=env)


def parse_args():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <command> [args...]")
        print("Commands:")
        print("  add_user <username> <config-path>")
        print("  run_as <username> <kubectl-args...>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add_user":
        if len(sys.argv) != 4:
            print(f"Usage: {sys.argv[0]} add_user <username> <config-path>")
            sys.exit(1)
        add_user(username=sys.argv[2], source_config_path=sys.argv[3])

    elif command == "run_as":
        if len(sys.argv) < 4:
            print(f"Usage: {sys.argv[0]} run_as <username> <kubectl-args...>")
            sys.exit(1)
        run_as(username=sys.argv[2], kubectl_args=sys.argv[3:])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    parse_args()
