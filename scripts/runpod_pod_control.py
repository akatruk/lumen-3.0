"""Resume or stop one existing RunPod pod. Never create or terminate.

Usage (on a host that has RUNPOD_API_KEY in the environment):

  python3 scripts/runpod_pod_control.py status
  python3 scripts/runpod_pod_control.py resume
  python3 scripts/runpod_pod_control.py stop

Only the pinned Hypit pod is allowed (LUMEN_GPU_POD_ID or default
dznvwn90el5au4 / lumen-hypit-4090). lumen-web-gpu is left alone.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

DEFAULT_POD = "dznvwn90el5au4"
ALLOWED_NAME = "lumen-hypit-4090"
FORBIDDEN = {"hufsgfs9f7gpga"}


def allowed_pod():
    raw = (os.environ.get("LUMEN_GPU_POD_ID") or DEFAULT_POD).strip()
    if not raw:
        raise SystemExit("LUMEN_GPU_POD_ID is empty")
    if raw in FORBIDDEN:
        raise SystemExit("pod id is forbidden: " + raw)
    return raw


# Back-compat for importers / docs that read ALLOWED_POD at import time.
ALLOWED_POD = DEFAULT_POD


def _token():
    token = os.environ.get("RUNPOD_API_KEY") or ""
    if not token:
        raise SystemExit("RUNPOD_API_KEY missing")
    return token


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.runpod.io/graphql?api_key=" + _token(),
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "lumen-media/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data.get("data") or {}


def myself():
    data = gql(
        "{ myself { currentSpendPerHr clientBalance "
        "pods { id name desiredStatus runtime { ports { ip isIpPublic privatePort publicPort type } } } } }"
    )
    return data["myself"]


def find_pod(pods):
    pinned = allowed_pod()
    match = next((p for p in pods if p.get("id") == pinned), None)
    if not match:
        raise SystemExit("allowed pod not found: " + pinned)
    if match.get("name") and match["name"] != ALLOWED_NAME:
        raise SystemExit("pod name mismatch")
    for pod in pods:
        if pod.get("id") in FORBIDDEN:
            # leave alone; only note status
            pass
    return match


def ssh_endpoint(pod):
    runtime = pod.get("runtime") or {}
    for port in runtime.get("ports") or []:
        if port.get("type") == "tcp" and port.get("privatePort") == 22 and port.get("isIpPublic"):
            return port.get("ip"), port.get("publicPort")
    return None, None


def cmd_status():
    me = myself()
    pods = me.get("pods") or []
    pod = find_pod(pods)
    pinned = allowed_pod()
    ip, port = ssh_endpoint(pod)
    print(
        json.dumps(
            {
                "podId": pod["id"],
                "name": pod.get("name"),
                "desiredStatus": pod.get("desiredStatus"),
                "ssh": {"ip": ip, "port": port},
                "balance": me.get("clientBalance"),
                "spendPerHr": me.get("currentSpendPerHr"),
                "other": [
                    {"id": p["id"], "name": p.get("name"), "desiredStatus": p.get("desiredStatus")}
                    for p in pods
                    if p.get("id") != pinned
                ],
            },
            indent=2,
        )
    )


def cmd_resume():
    me = myself()
    pod = find_pod(me.get("pods") or [])
    pinned = allowed_pod()
    status = pod.get("desiredStatus")
    if status == "RUNNING":
        print("ALREADY_RUNNING", pod["id"])
        cmd_status()
        return
    if status != "EXITED":
        raise SystemExit("refuse to resume from status " + str(status))
    gql(
        "mutation($id: String!) { podResume(input: { podId: $id, gpuCount: 1 }) { id } }",
        {"id": pinned},
    )
    for _ in range(60):
        time.sleep(5)
        me = myself()
        pod = find_pod(me.get("pods") or [])
        ip, port = ssh_endpoint(pod)
        if pod.get("desiredStatus") == "RUNNING" and ip and port:
            print("RESUMED", pod["id"], ip, port)
            cmd_status()
            return
    raise SystemExit("resume timeout")


def cmd_stop():
    me = myself()
    pod = find_pod(me.get("pods") or [])
    pinned = allowed_pod()
    if pod.get("desiredStatus") == "EXITED":
        print("ALREADY_EXITED", pod["id"])
        cmd_status()
        return
    gql(
        "mutation($id: String!) { podStop(input: { podId: $id }) { id desiredStatus } }",
        {"id": pinned},
    )
    for _ in range(36):
        time.sleep(5)
        me = myself()
        pod = find_pod(me.get("pods") or [])
        if pod.get("desiredStatus") == "EXITED":
            print("STOPPED", pod["id"])
            cmd_status()
            return
    raise SystemExit("stop timeout")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"status", "resume", "stop"}:
        raise SystemExit("usage: runpod_pod_control.py status|resume|stop")
    {"status": cmd_status, "resume": cmd_resume, "stop": cmd_stop}[sys.argv[1]]()


if __name__ == "__main__":
    main()
