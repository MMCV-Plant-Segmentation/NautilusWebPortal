import json, subprocess, sys

args = json.loads(subprocess.check_output(["kubectl", "config", "view", "--raw", "-o", "jsonpath={.users[?(@.name=='oidc')].user.exec.args}"]))
args += ["--skip-open-browser", "--grant-type=device-code", "--token-cache-storage=disk"]

flags = [f'--exec-arg="{a}"' for a in args]
subprocess.run(["kubectl", "config", "set-credentials", "oidc"] + flags)