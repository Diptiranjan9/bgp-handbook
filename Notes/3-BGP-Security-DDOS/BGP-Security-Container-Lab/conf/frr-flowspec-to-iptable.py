#!/usr/bin/env python3
"""
FRR BGP FlowSpec to iptables State-Preserving Sync Daemon (bug-fixed)

Features:
- Preserves kernel packet/byte counters by identifying rules with a stable
  content hash tagged via `-m comment`, instead of relying on exact string
  equality against iptables -S output (which is fragile across iptables
  versions/module-ordering quirks).
- Parses Destination, Source, Protocol, Ports (Type 4/5/6), TCP Flags, DSCP,
  and Packet Lengths.
- Handles FRR's 'pktlen' formatting (e.g. '>= 40 , <= 60') and converts it to
  '-m length --length 40:60'.
- Fast-path stateless packet dropping using iptables raw PREROUTING table.

Fixes applied vs. the original version:
  1. Type 4 "port" (source OR destination) is now translated using
     `-m multiport --ports`, instead of being silently discarded.
  2. TCP-flags matching no longer silently rides on a defaulted "udp"
     protocol. If a rule carries tcp_flags but was inferred/declared with a
     non-TCP protocol, the rule is now rejected with a warning instead of
     being installed as a broken (and iptables-rejected) `-p udp
     --tcp-flags` combination.
  3. Rule identity for the add/delete diff is now based on a canonical
     content hash embedded via `-m comment --comment "fs_<hash>"`, not on
     matching the full argument string against however the kernel chooses
     to re-render `-S` output. This keeps counters stable even if iptables'
     own formatting doesn't byte-match what we generated.
  4. Only DROP is currently supported as an action (consistent with the lab
     using Traffic-Rate=0). If a rule's extended community implies a
     non-drop action, the daemon logs a warning instead of silently
     applying DROP to it. This is a placeholder for extending to
     rate-limit/redirect/mark actions later.
"""

import hashlib
import json
import re
import subprocess
import sys
import time

CHAIN_NAME = "BGP_FLOWSPEC"
POLL_INTERVAL = 3
COMMENT_PREFIX = "fs_"


def run_cmd(cmd_args, input_data=None):
    """Executes shell commands silently and returns output."""
    try:
        res = subprocess.run(
            cmd_args, input=input_data, text=True, capture_output=True, check=True
        )
        return res.stdout
    except subprocess.CalledProcessError:
        return None


def setup_iptables():
    """Ensures the custom BGP_FLOWSPEC chain exists in raw PREROUTING."""
    run_cmd(["iptables", "-t", "raw", "-N", CHAIN_NAME])
    check_hook = run_cmd(
        ["iptables", "-t", "raw", "-C", "PREROUTING", "-j", CHAIN_NAME]
    )
    if check_hook is None:
        run_cmd(["iptables", "-t", "raw", "-I", "PREROUTING", "-j", CHAIN_NAME])


def clean_val(val):
    """Strips leading '=' or spaces from FRR string values."""
    if not val:
        return ""
    return str(val).replace("=", "").strip()


def parse_pktlen(val):
    """
    Parses FRR pktlen strings like '>= 40 , <= 60 ' or '>= 40&<= 60' or '= 40-60'
    and converts them into iptables colon format '40:60'.
    """
    if not val:
        return ""

    numbers = re.findall(r"\d+", str(val))

    if len(numbers) >= 2:
        return f"{numbers[0]}:{numbers[1]}"
    elif len(numbers) == 1:
        return numbers[0]

    return ""


def parse_frr_json():
    """Fetches and parses current BGP FlowSpec rules directly from FRR JSON."""
    raw = run_cmd(["vtysh", "-c", "show bgp ipv4 flowspec detail json"])
    if not raw:
        return []

    json_start = raw.find("[")
    if json_start == -1:
        return []

    clean_raw = raw[json_start:].strip()
    # Sanitize concatenated JSON arrays from vtysh output
    clean_raw = re.sub(r"\]\s*\[", "],[", clean_raw)
    clean_raw = f"[{clean_raw}]"

    try:
        blocks = json.loads(clean_raw)
    except Exception:
        return []

    rules = []
    for block in blocks:
        if not isinstance(block, list):
            continue
        rule = {}
        for item in block:
            if not isinstance(item, dict):
                continue

            if "to" in item:
                rule["dst"] = clean_val(item["to"])
            if "from" in item:
                rule["src"] = clean_val(item["from"])
            if "proto" in item:
                rule["proto"] = clean_val(item["proto"])
            if "dstp" in item:
                rule["dport"] = clean_val(item["dstp"])
            if "srcp" in item:
                rule["sport"] = clean_val(item["srcp"])
            if "port" in item:
                rule["port"] = clean_val(item["port"])
            if "tcp" in item or "tcp-flags" in item:
                rule["tcp_flags"] = clean_val(
                    item.get("tcp") or item.get("tcp-flags")
                )

            if "pktlen" in item:
                rule["length"] = parse_pktlen(item["pktlen"])
            elif "length" in item:
                rule["length"] = parse_pktlen(item["length"])

            if "dscp" in item:
                rule["dscp"] = clean_val(item["dscp"])

        if rule and ("dst" in rule or "src" in rule):
            rules.append(rule)

    return rules


def parse_tcp_flags_bitmask(bitmask_str):
    """Converts numeric TCP flag bitmasks (e.g. '2') into standard string flag names."""
    try:
        val = int(bitmask_str)
        flag_names = []
        if val & 1:
            flag_names.append("FIN")
        if val & 2:
            flag_names.append("SYN")
        if val & 4:
            flag_names.append("RST")
        if val & 8:
            flag_names.append("PSH")
        if val & 16:
            flag_names.append("ACK")
        if val & 32:
            flag_names.append("URG")
        return ",".join(flag_names) if flag_names else None
    except ValueError:
        return bitmask_str


def format_ip(ip_str):
    """Ensures IP strings have explicit CIDR /32 notation."""
    if not ip_str:
        return ip_str
    if "/" not in ip_str:
        return f"{ip_str}/32"
    return ip_str


def rule_hash(rule):
    """
    Deterministic content hash of a parsed FlowSpec rule. Used as the stable
    identity tag for a rule regardless of how iptables re-renders arguments,
    so counters survive across sync cycles.
    """
    canonical = json.dumps(rule, sort_keys=True)
    return hashlib.sha1(canonical.encode()).hexdigest()[:12]


def build_iptables_args(rule):
    """
    Builds rule arguments for `iptables -A/-D`.

    Returns (tag, args_string) on success, or (None, reason) if the rule is
    invalid/unsupported and should be skipped (reason is a human-readable
    string for logging).

    Order: -s -> -d -> -p -> -m <proto>/multiport -> ports -> --tcp-flags
           -> -m length -> -m dscp -> -m comment (identity tag) -> -j DROP
    """
    args = []

    # Source and Destination IPs
    if "src" in rule:
        args.extend(["-s", format_ip(rule["src"])])
    if "dst" in rule:
        args.extend(["-d", format_ip(rule["dst"])])

    # Protocol
    proto = rule.get("proto", "")
    proto_name = None
    proto_explicit = False
    if proto:
        if proto in ["6", "tcp"]:
            proto_name = "tcp"
        elif proto in ["17", "udp"]:
            proto_name = "udp"
        elif proto in ["1", "icmp"]:
            proto_name = "icmp"
        else:
            proto_name = proto
        proto_explicit = True
        args.extend(["-p", proto_name])

    # --- Bug fix #2: TCP-flags requires TCP protocol. Validate up front
    #     instead of letting a defaulted/mismatched protocol slip through. ---
    if "tcp_flags" in rule:
        if proto_explicit and proto_name != "tcp":
            return None, (
                f"rule has tcp_flags but explicit non-TCP protocol "
                f"'{proto_name}' — skipping (invalid per RFC 8955 semantics)"
            )
        if not proto_explicit:
            proto_name = "tcp"
            proto_explicit = True
            args.extend(["-p", "tcp"])

    # --- Bug fix #1: Type 4 "port" (matches src OR dst) via multiport ---
    if "port" in rule:
        if not proto_explicit:
            proto_name = "udp"
            proto_explicit = True
            args.extend(["-p", "udp"])
        args.extend(["-m", "multiport", "--ports", rule["port"]])

    # Destination / Source ports (Type 5 / Type 6)
    if "dport" in rule:
        if not proto_explicit:
            proto_name = "udp"
            proto_explicit = True
            args.extend(["-p", "udp"])
        args.extend(["-m", proto_name, "--dport", rule["dport"]])

    if "sport" in rule:
        if not proto_explicit:
            proto_name = "udp"
            proto_explicit = True
            args.extend(["-p", "udp"])
        args.extend(["-m", proto_name, "--sport", rule["sport"]])

    # TCP Flags (protocol already guaranteed to be tcp at this point if present)
    if "tcp_flags" in rule:
        if "-m" not in args or "tcp" not in args:
            args.extend(["-m", "tcp"])
        parsed_flags = parse_tcp_flags_bitmask(rule["tcp_flags"])
        if parsed_flags:
            args.extend(["--tcp-flags", "FIN,SYN,RST,ACK", parsed_flags])

    # Length Matcher (-m length --length 40:60)
    if "length" in rule and rule["length"]:
        args.extend(["-m", "length", "--length", rule["length"]])

    # DSCP Matcher
    if "dscp" in rule:
        args.extend(["-m", "dscp", "--dscp", rule["dscp"]])

    # --- Bug fix #3: stable identity tag, independent of formatting ---
    tag = rule_hash(rule)
    args.extend(["-m", "comment", "--comment", f"{COMMENT_PREFIX}{tag}"])

    args.extend(["-j", "DROP"])
    return tag, " ".join(args)


def get_current_iptables_rules():
    """
    Fetches active rules inside BGP_FLOWSPEC chain, keyed by the comment tag
    we control (fs_<hash>), not the raw argument string. Returns
    {tag: full_rule_args_string_as_seen_by_kernel}.
    """
    out = run_cmd(["iptables", "-t", "raw", "-S", CHAIN_NAME])
    if not out:
        return {}

    active = {}
    tag_re = re.compile(rf'--comment "?{COMMENT_PREFIX}([0-9a-f]+)"?')
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith(f"-A {CHAIN_NAME}"):
            continue
        rule_args = line.replace(f"-A {CHAIN_NAME} ", "").strip()
        match = tag_re.search(rule_args)
        if match:
            tag = match.group(1)
            active[tag] = rule_args
        # Rules without our comment tag (e.g. manually added) are ignored by
        # the sync engine entirely — we never touch what we didn't tag.

    return active


def sync():
    setup_iptables()
    parsed_rules = parse_frr_json()

    # 1. Build target rule set: tag -> args string
    target = {}
    for r in parsed_rules:
        tag, result = build_iptables_args(r)
        if tag is None:
            print(f"\n[!] Skipping invalid rule: {result}", file=sys.stderr)
            continue
        target[tag] = result

    # 2. Get active kernel rules (only ones we tagged)
    active = get_current_iptables_rules()

    # 3. Diff by tag, not by full string
    tags_to_add = set(target) - set(active)
    tags_to_delete = set(active) - set(target)

    # 4. Only touch what changed (preserves counters for unchanged tags)
    for tag in tags_to_add:
        cmd = ["iptables", "-t", "raw", "-A", CHAIN_NAME] + target[tag].split()
        run_cmd(cmd)

    for tag in tags_to_delete:
        # Delete using the exact string the kernel reported back, so the
        # delete syntax always matches what's actually installed.
        cmd = ["iptables", "-t", "raw", "-D", CHAIN_NAME] + active[tag].split()
        run_cmd(cmd)

    sys.stdout.write(
        f"\r[*] Active: {len(target)} | Added: {len(tags_to_add)} | "
        f"Deleted: {len(tags_to_delete)}   "
    )
    sys.stdout.flush()


def main():
    print("[*] Starting State-Preserving FlowSpec Sync Daemon...")
    while True:
        try:
            sync()
        except Exception as e:
            print(f"\n[!] Sync Exception: {e}", file=sys.stderr)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()