#!/usr/bin/env python3
"""Poll lumen-test Hypit render every INTERVAL; stop RunPods when done; write timing report."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOST = os.environ.get("LUMEN_TEST_HOST", "root@142.93.248.163")
PROJECT_ID = os.environ.get("LUMEN_WATCH_PROJECT", "420ba25207ac45b5a8cd7069b129c63f")
RENDER_ID = os.environ.get("LUMEN_WATCH_RENDER", "4731525b097540c6811dd3817c24e122")
INTERVAL = int(os.environ.get("LUMEN_WATCH_INTERVAL", "600"))
MAX_HOURS = float(os.environ.get("LUMEN_WATCH_MAX_HOURS", "6"))
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("LUMEN_WATCH_OUT", str(ROOT / "output" / "runpod-gen-timing-report.md")))
LOG = Path(os.environ.get("LUMEN_WATCH_LOG", str(ROOT / "output" / "runpod-gen-monitor.log")))
WEB_POD = "hufsgfs9f7gpga"
HYPIT_POD = os.environ.get("HYPIT_POD_ID", "nxi1rfwb94eufx")
STOP_HYPIT = os.environ.get("LUMEN_STOP_HYPIT", "1") == "1"
STOP_WEB = os.environ.get("LUMEN_STOP_WEB", "1") == "1"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{utcnow()} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def ssh(script: str, timeout: int = 90) -> str:
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST, "bash", "-s"],
        input=script,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")
    if r.returncode != 0:
        raise RuntimeError(f"ssh rc={r.returncode}: {out[-1500:]}")
    return out


def hypit_key() -> str | None:
    pat = re.compile(r"rpa_[A-Za-z0-9_\-]{20,}")
    root = Path(
        "/Users/akatruk_macbook/.cursor/projects/"
        "Users-akatruk-macbook-Documents-github-lumen-3-0/agent-transcripts/"
        "1492dcf3-d1d7-40d0-883d-5c640bd08663"
    )
    for p in root.rglob("*"):
        if p.suffix not in {".jsonl", ".md"}:
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for m in pat.findall(text):
            if m.endswith("6gn2"):
                return m
    return None


def gql(api_key: str, query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.runpod.io/graphql?api_key=" + api_key,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "lumen-ops/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode())
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"])[:500])
    return data.get("data") or {}


def web_key_via_ssh() -> str:
    out = ssh(
        "set -a; source /opt/lumen-rebuild/.env; set +a; "
        "python3 -c 'import os; print(os.environ.get(\"RUNPOD_API_KEY\",\"\"))'",
        timeout=40,
    )
    key = out.strip().splitlines()[-1].strip()
    if not key.startswith("rpa_"):
        raise RuntimeError("web RUNPOD_API_KEY missing")
    return key


def snapshot() -> dict:
    remote = f"""
set -euo pipefail
export BASE=/mnt/volume_nyc1_1791446889637/lumen/{PROJECT_ID}/renders/{RENDER_ID}
export PROJECT_ID={PROJECT_ID}
export RENDER_ID={RENDER_ID}
python3 <<'PY'
import json, os, subprocess, time, urllib.request
from pathlib import Path
base = Path(os.environ["BASE"])
pid = os.environ["PROJECT_ID"]
rid = os.environ["RENDER_ID"]
out = {{
  "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "project_id": pid,
  "render_id": rid,
  "files": {{}},
  "hypit_worker": False,
  "speech_worker": False,
  "web_gpu": {{}},
  "runtime_hint": None,
  "idle_with_artifacts": False,
  "done_hard": False,
  "done_reason": [],
  "newest_mp4": [],
  "journal_tail": "",
  "journal_complete": False,
}}
if base.exists():
  for rel in [
    "assembled.mp4","visual.mp4","sound-mix.mp4","music-mix.mp4","cut.mp4",
    "final.mp4","delivery.mp4","picture.mp4","output.mp4",
    "hypit/visual.mp4","hypit/cut.mp4","hypit/source.mp4",
  ]:
    path = base / rel
    if path.exists():
      st = path.stat()
      out["files"][rel] = {{
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)),
      }}
  rt = base / "hypit" / "hypit.runtime.json"
  if rt.exists():
    try:
      d = json.loads(rt.read_text())
      out["runtime_hint"] = {{k: d.get(k) for k in list(d)[:30] if not isinstance(d.get(k), (dict, list))}}
    except Exception as e:
      out["runtime_hint"] = {{"error": str(e)}}
  mp4s = sorted(base.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
  out["newest_mp4"] = [
    {{"path": str(p.relative_to(base)), "bytes": p.stat().st_size,
      "mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(p.stat().st_mtime))}}
    for p in mp4s
  ]

env = {{}}
for line in Path("/opt/lumen-rebuild/.env").read_text().splitlines():
  if "=" in line and not line.strip().startswith("#"):
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")
key = env.get("RUNPOD_API_KEY", "")
body = json.dumps({{"query": "{{ myself {{ currentSpendPerHr pods {{ id name desiredStatus runtime {{ uptimeInSeconds gpus {{ gpuUtilPercent memoryUtilPercent }} ports {{ ip publicPort privatePort isIpPublic type }} }} }} }} }}"}}).encode()
req = urllib.request.Request(
  "https://api.runpod.io/graphql?api_key=" + key,
  data=body,
  headers={{"Content-Type": "application/json", "User-Agent": "lumen-ops/1.0"}},
  method="POST",
)
with urllib.request.urlopen(req, timeout=45) as r:
  me = json.loads(r.read().decode())["data"]["myself"]
out["spend_web"] = me.get("currentSpendPerHr")
for p in me.get("pods") or []:
  rt = p.get("runtime") or {{}}
  g = ((rt.get("gpus") or [{{}}])[0])
  out["web_gpu"][p["name"]] = {{
    "id": p["id"], "status": p["desiredStatus"],
    "uptime": rt.get("uptimeInSeconds"),
    "gpu": g.get("gpuUtilPercent"), "mem": g.get("memoryUtilPercent"),
  }}
web = next(x for x in me["pods"] if x["name"] == "lumen-web-gpu")
ports = (web.get("runtime") or {{}}).get("ports") or []
ssh = next((x for x in ports if x.get("privatePort") == 22 and x.get("isIpPublic")), None)
if ssh and web.get("desiredStatus") == "RUNNING":
  cmd = [
    "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "IdentitiesOnly=yes",
    "-i", "/opt/lumen-rebuild/data/gpu/id_ed25519", "-p", str(ssh["publicPort"]), "root@" + ssh["ip"],
    "ps -eo etime,cmd | grep -iE 'hypit|_worker|lumen-speech|ffmpeg|svrun' | grep -v grep | head -40; echo MARK; "
    "ls -lt /opt/lumen-web-job 2>/dev/null | head -12",
  ]
  try:
    ps = subprocess.check_output(cmd, text=True, timeout=50)
  except Exception as e:
    ps = "ssh_fail " + str(e)
  out["web_ps"] = ps[-3500:]
  out["hypit_worker"] = ("_worker" in ps) or ("hypit.mjs" in ps)
  out["speech_worker"] = ("lumen-speech" in ps) or ("runtime.py" in ps)

reason = []
for cand in [base / "final.mp4", base / "delivery.mp4", base / "picture.mp4", base / "hypit" / "final.mp4"]:
  if cand.exists() and cand.stat().st_size > 100000:
    reason.append("file:" + cand.name)
visual = base / "hypit" / "visual.mp4"
assembled = base / "assembled.mp4"
out["idle_with_artifacts"] = bool(
  visual.exists() and assembled.exists() and (not out["hypit_worker"]) and (not out["speech_worker"])
  and max(visual.stat().st_mtime, assembled.stat().st_mtime) > time.time() - 6 * 3600
)
try:
  j = subprocess.check_output(
    ["journalctl", "-u", "lumen-worker", "--since", "6 hours ago", "--no-pager"],
    text=True, timeout=30,
  )
except Exception:
  j = ""
out["journal_complete"] = (pid[:8] in j) and ("complete" in j.lower())
out["journal_failed"] = (pid[:8] in j) and ("failed" in j.lower())
out["journal_tail"] = "\\n".join(j.strip().splitlines()[-20:])
out["done_hard"] = bool(reason)
out["done_reason"] = reason
print(json.dumps(out, ensure_ascii=False))
PY
"""
    raw = ssh(remote, timeout=120)
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise RuntimeError("no snapshot json: " + raw[-800:])


def stop_pods() -> dict:
    result: dict = {"web": None, "hypit": None}
    if STOP_WEB:
        try:
            key = web_key_via_ssh()
            st = gql(key, "{ myself { pods { id name desiredStatus } } }")
            pods = (st.get("myself") or {}).get("pods") or []
            web = next((p for p in pods if p["id"] == WEB_POD or p.get("name") == "lumen-web-gpu"), None)
            if web and web.get("desiredStatus") == "RUNNING":
                gql(
                    key,
                    "mutation($id:String!){ podStop(input:{podId:$id}){ id desiredStatus } }",
                    {"id": web["id"]},
                )
                result["web"] = "stopped:" + web["id"]
            else:
                result["web"] = "already:" + str((web or {}).get("desiredStatus"))
            pic = next((p for p in pods if p.get("name") == "lumen-picture"), None)
            if pic:
                result["picture_left"] = pic.get("desiredStatus")
        except Exception as e:
            result["web"] = f"error:{e}"
    if STOP_HYPIT:
        try:
            key = hypit_key()
            if not key:
                result["hypit"] = "no_key"
            else:
                st = gql(key, "{ myself { pods { id name desiredStatus } } }")
                pods = (st.get("myself") or {}).get("pods") or []
                hyp = next(
                    (p for p in pods if p["id"] == HYPIT_POD or p.get("name") == "lumen-hypit-4090"),
                    None,
                )
                if hyp and hyp.get("desiredStatus") == "RUNNING":
                    gql(
                        key,
                        "mutation($id:String!){ podStop(input:{podId:$id}){ id desiredStatus } }",
                        {"id": hyp["id"]},
                    )
                    result["hypit"] = "stopped:" + hyp["id"]
                else:
                    result["hypit"] = "already:" + str((hyp or {}).get("desiredStatus"))
        except Exception as e:
            result["hypit"] = f"error:{e}"
    return result


def write_report(start: float, checks: list, stop: dict, final: dict, finished: bool, reason: str) -> None:
    end = time.time()
    lines = [
        "# RunPod generation timing report",
        "",
        f"- Started watch: {datetime.fromtimestamp(start, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Finished watch: {utcnow()}",
        f"- Wall time: {(end - start) / 60:.1f} min",
        f"- Project: `{PROJECT_ID}`",
        f"- Render: `{RENDER_ID}`",
        f"- Poll interval: {INTERVAL}s",
        f"- Generation finished: **{finished}** ({reason or 'n/a'})",
        f"- Stop actions: `{json.dumps(stop)}`",
        "",
        "## Checks",
        "",
    ]
    for i, c in enumerate(checks):
        lines.append(f"### Check {i + 1} @ {c.get('ts')}")
        lines.append(
            f"- hypit_worker={c.get('hypit_worker')} speech_worker={c.get('speech_worker')} "
            f"spend_web={c.get('spend_web')} idle_artifacts={c.get('idle_with_artifacts')}"
        )
        for name, info in (c.get("web_gpu") or {}).items():
            lines.append(
                f"- {name}: {info.get('status')} up={info.get('uptime')}s "
                f"gpu%={info.get('gpu')} mem%={info.get('mem')}"
            )
        files = c.get("files") or {}
        if files:
            lines.append("- files: " + ", ".join(f"{k}({v.get('bytes')})" for k, v in files.items()))
        if c.get("newest_mp4"):
            top = c["newest_mp4"][0]
            lines.append(f"- newest_mp4: {top.get('path')} {top.get('bytes')} @ {top.get('mtime')}")
        lines.append("")
    slim = {k: final.get(k) for k in final if k not in ("web_ps", "journal_tail")}
    lines.append("## Final snapshot")
    lines.append("```json")
    lines.append(json.dumps(slim, indent=2, ensure_ascii=False)[:4000])
    lines.append("```")
    if final.get("web_ps"):
        lines.extend(["", "## Last web-gpu processes", "```", str(final.get("web_ps"))[-2000:], "```"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    log(f"report_written {OUT}")


def is_finished(snap: dict, seen_work: bool, idle_streak: int) -> tuple[bool, str]:
    if snap.get("done_hard"):
        return True, "hard:" + ",".join(snap.get("done_reason") or [])
    if seen_work and snap.get("journal_failed") and not snap.get("hypit_worker") and not snap.get("speech_worker"):
        return True, "job_failed"
    if seen_work and snap.get("idle_with_artifacts") and idle_streak >= 2:
        return True, "workers_idle_with_artifacts"
    if seen_work and not snap.get("hypit_worker") and not snap.get("speech_worker"):
        if snap.get("journal_complete"):
            return True, "journal_complete"
    return False, ""


def main() -> int:
    start = time.time()
    log(f"monitor_start interval={INTERVAL}s project={PROJECT_ID} render={RENDER_ID}")
    checks: list[dict] = []
    seen_work = False
    idle_streak = 0
    deadline = start + MAX_HOURS * 3600
    final: dict = {}
    finished = False
    reason = ""

    while time.time() < deadline:
        try:
            snap = snapshot()
        except Exception as e:
            log(f"snapshot_error {e}")
            time.sleep(min(INTERVAL, 120))
            continue
        checks.append(snap)
        final = snap
        if snap.get("hypit_worker") or snap.get("speech_worker"):
            seen_work = True
            idle_streak = 0
        elif seen_work and snap.get("idle_with_artifacts"):
            idle_streak += 1
        elif seen_work and not snap.get("hypit_worker") and not snap.get("speech_worker"):
            idle_streak += 1
        else:
            idle_streak = 0

        log(
            f"check#{len(checks)} hypit={snap.get('hypit_worker')} speech={snap.get('speech_worker')} "
            f"idle={snap.get('idle_with_artifacts')} streak={idle_streak} "
            f"web={((snap.get('web_gpu') or {}).get('lumen-web-gpu') or {}).get('status')} "
            f"gpu%={((snap.get('web_gpu') or {}).get('lumen-web-gpu') or {}).get('gpu')}"
        )

        ok, reason = is_finished(snap, seen_work, idle_streak)
        if ok:
            finished = True
            break
        time.sleep(INTERVAL)

    stop: dict
    if finished:
        log(f"stopping_pods reason={reason}")
        stop = stop_pods()
        log(f"stop_result {stop}")
        time.sleep(5)
        try:
            snap2 = snapshot()
            checks.append(snap2)
            final = snap2
        except Exception as e:
            log(f"post_stop_snapshot_error {e}")
    else:
        log("timeout_or_no_finish — not stopping pods")
        stop = {"skipped": True, "reason": "not_finished"}

    write_report(start, checks, stop, final, finished, reason)
    print(f"\nREPORT: {OUT}\nfinished={finished} reason={reason} stop={stop}")
    return 0 if finished else 2


if __name__ == "__main__":
    sys.exit(main())
