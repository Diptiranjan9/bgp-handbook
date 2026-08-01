#!/usr/bin/env python3

import json
import subprocess
import glob
import os
import sys

# ----------------------------
# SSH user mapping
# ----------------------------
SSH_USERS = {
    "cisco_iol": "admin",
    "juniper_crpd": "root",
    "arista_ceos": "admin",
}

SSH_KINDS = set(SSH_USERS.keys())

# ----------------------------
# Find topology file
# ----------------------------

topos = glob.glob("*.yml") + glob.glob("*.yaml")

if len(topos) == 0:
    print("No .yml topology found.")
    sys.exit(1)

if len(topos) > 1:
    print("Multiple topology files found:")
    for f in topos:
        print(f"  {f}")
    sys.exit(1)

TOPO = topos[0]

print(f"Using topology: {TOPO}")

# ----------------------------
# Inspect topology
# ----------------------------

output = subprocess.check_output(
    [
        "containerlab",
        "inspect",
        "-t",
        TOPO,
        "--format",
        "json",
    ],
    text=True,
)

labs = json.loads(output)

nodes = []

for lab in labs.values():
    nodes.extend(lab)

# Sort by node name
nodes.sort(key=lambda x: x["name"])

# ----------------------------
# Create tmux sessions
# ----------------------------

for node in nodes:

    kind = node["kind"]
    full_name = node["name"]

    # Remove "clab-<labname>-"
    session = full_name.split("-", 2)[-1]

    subprocess.run(
        ["tmux", "kill-session", "-t", session],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if kind in SSH_KINDS:

        ip = node["ipv4_address"].split("/")[0]
        user = SSH_USERS[kind]

        cmd = (
            f"ct ssh "
            f"-o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null "
            f"{user}@{ip}"
        )

    else:
        # Every other node is treated as a Linux container
        cmd = f"ct docker exec -it {full_name} bash"

    print(f"{session:<20} -> {cmd}")

    subprocess.run(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            session,
            cmd,
        ]
    )

print("\nCreated tmux sessions:\n")

subprocess.run(["tmux", "ls"])
#close all tmux session
#tmux ls | cut -d: -f1 | xargs -I {} tmux kill-session -t {}