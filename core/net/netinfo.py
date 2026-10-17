"""
Local network interface info.

Uses stdlib only:
    * socket            — routing trick for primary IP
    * subprocess        — ipconfig / ifconfig / ip for details
    * platform          — OS detection

Public API:
    get_primary_ipv4()   -> str
    get_default_gateway()-> str
    get_netmask_for(ip)  -> str
    get_interfaces()     -> list[dict]
    NetInfo              — small cache class
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
import sys
from typing import Optional


IS_WINDOWS = sys.platform.startswith("win")
IS_MAC     = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")


# ---------------------------------------------------------------------------
# Subprocess helper — no black console window on Windows
# ---------------------------------------------------------------------------
def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if IS_WINDOWS else 0,  # CREATE_NO_WINDOW
        )
        # Windows: cp866 is the default OEM codepage for RU locale
        enc = "cp866" if IS_WINDOWS else "utf-8"
        return out.decode(enc, errors="replace")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Primary IP / gateway / netmask
# ---------------------------------------------------------------------------
def get_primary_ipv4() -> str:
    """
    Return the primary IPv4 address.

    Trick: open a UDP socket "to" 8.8.8.8 (no packet is actually sent),
    ask the OS which local address it would use. Works on any OS.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_default_gateway() -> str:
    """Best-effort default gateway."""
    if IS_WINDOWS:
        out = _run(["route", "print", "0.0.0.0"])
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                return parts[2]

    elif IS_LINUX:
        out = _run(["ip", "route"])
        for line in out.splitlines():
            if line.startswith("default"):
                parts = line.split()
                if "via" in parts:
                    return parts[parts.index("via") + 1]

    elif IS_MAC:
        out = _run(["netstat", "-rn"])
        for line in out.splitlines():
            if line.startswith("default"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]

    return ""


def get_netmask_for(ip: str) -> str:
    """Best-effort netmask lookup for the given IP."""
    if not ip:
        return ""

    if IS_WINDOWS:
        out = _run(["ipconfig"])
        current_ip = ""
        current_mask = ""
        for raw in out.splitlines():
            line = raw.rstrip()
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key_l = key.strip().lower()
            val = val.strip().split("(")[0].strip()

            if "ipv4" in key_l or "ip-адрес" in key_l:
                current_ip = val
            elif "subnet mask" in key_l or "маска подсети" in key_l:
                current_mask = val
                if current_ip == ip:
                    return current_mask

    elif IS_LINUX or IS_MAC:
        # try to find /<prefix> after the IP in `ip addr` output
        out = _run(["ip", "addr"] if IS_LINUX else ["ifconfig"])
        for line in out.splitlines():
            if ip in line:
                m = re.search(r"/(\d+)", line)
                if m:
                    prefix = int(m.group(1))
                    mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
                    return ".".join(
                        str((mask_int >> (8 * i)) & 0xFF) for i in reversed(range(4))
                    )

    return ""


# ---------------------------------------------------------------------------
# Per-interface details
# ---------------------------------------------------------------------------
def get_interfaces() -> list[dict]:
    """
    Return a list of interfaces. Each entry is a dict:
        {
            "name": "...",
            "ip": "...",
            "mask": "...",
            "gw": "...",
            "mac": "...",
            "type": "Ethernet" | "Wi-Fi" | "Loopback" | "Other",
        }
    """
    if IS_WINDOWS:
        return _parse_windows()
    return _parse_unix()


def _classify(name: str) -> str:
    n = name.lower()
    if "wi-fi" in n or "wireless" in n or "wlan" in n or "беспроводная" in n:
        return "Wi-Fi"
    if "ethernet" in n or "local area" in n or "ethernet" in n:
        return "Ethernet"
    if "loopback" in n or "петля" in n:
        return "Loopback"
    if "virtual" in n or "vmware" in n or "virtualbox" in n or "hyper-v" in n:
        return "Virtual"
    return "Other"


def _parse_windows() -> list[dict]:
    out = _run(["ipconfig", "/all"])
    result: list[dict] = []

    current: dict = {}
    last_gw = ""

    for raw in out.splitlines():
        line = raw.rstrip()
        if not line.strip():
            # block boundary → flush
            if current.get("ip"):
                current.setdefault("gw", last_gw)
                result.append(current)
            current = {}
            last_gw = ""
            continue

        stripped = line.strip()
        low = stripped.lower()

        # header: "Адаптер Ethernet: ..." / "Ethernet adapter ...:"
        if (
            (stripped.endswith(":") and "adapter" in low)
            or (stripped.endswith(":") and "адаптер" in low)
            or ("adapter" in low and ":" in stripped)
        ):
            if current.get("ip"):
                current.setdefault("gw", last_gw)
                result.append(current)
            name = stripped.rstrip(":").strip()
            # "Адаптер Ethernet Ethernet:" → keep only last part
            if ":" in name:
                name = name.split(":")[-1].strip()
            current = {"name": name, "type": _classify(name)}
            last_gw = ""
            continue

        if ":" not in line:
            continue

        key, val = line.split(":", 1)
        key_l = key.strip().lower()
        val = val.strip()

        if "ipv4" in key_l or "ip-адрес" in key_l:
            current["ip"] = val.split("(")[0].strip()
        elif "subnet mask" in key_l or "маска подсети" in key_l:
            current["mask"] = val
        elif "default gateway" in key_l or "основной шлюз" in key_l:
            if val:
                last_gw = val
                current["gw"] = val
        elif "physical address" in key_l or "физический адрес" in key_l:
            current["mac"] = val
        elif "description" in key_l or "описание" in key_l:
            current["description"] = val

    if current.get("ip"):
        current.setdefault("gw", last_gw)
        result.append(current)

    return result


def _parse_unix() -> list[dict]:
    """
    Simple parser for `ip addr` (Linux) or `ifconfig` (macOS).
    Not as detailed as Windows, but enough to show IP/mask/MAC.
    """
    result: list[dict] = []
    if IS_LINUX:
        out = _run(["ip", "-o", "addr"])
        for line in out.splitlines():
            # "2: eth0    inet 192.168.1.5/24 brd ... scope global eth0"
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[1]
            if parts[2] != "inet":
                continue
            addr = parts[3]
            ip, _, prefix = addr.partition("/")
            try:
                prefix_i = int(prefix)
                mask_int = (0xFFFFFFFF << (32 - prefix_i)) & 0xFFFFFFFF
                mask = ".".join(
                    str((mask_int >> (8 * i)) & 0xFF) for i in reversed(range(4))
                )
            except Exception:
                mask = ""
            result.append({
                "name": name,
                "type": _classify(name),
                "ip": ip,
                "mask": mask,
            })
    else:
        # macOS: ifconfig
        out = _run(["ifconfig"])
        current: dict = {}
        for line in out.splitlines():
            if line and not line[0].isspace():
                if current.get("ip"):
                    result.append(current)
                name = line.split(":")[0]
                current = {"name": name, "type": _classify(name)}
                continue
            if "inet " in line and "127.0.0.1" not in line:
                m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    current["ip"] = m.group(1)
                m2 = re.search(r"netmask (0x[0-9a-f]+)", line)
                if m2:
                    nm = int(m2.group(1), 16)
                    current["mask"] = ".".join(
                        str((nm >> (8 * i)) & 0xFF) for i in reversed(range(4))
                    )
        if current.get("ip"):
            result.append(current)

    # enrich with gateway for the primary interface
    gw = get_default_gateway()
    primary_ip = get_primary_ipv4()
    for iface in result:
        if iface.get("ip") == primary_ip and gw:
            iface["gw"] = gw
            break

    return result


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class NetInfo:
    """Small cache — refresh on demand."""

    def __init__(self) -> None:
        self._ip = ""
        self._mask = ""
        self._gw = ""
        self._interfaces: list[dict] = []
        self.refresh()

    def refresh(self) -> None:
        self._ip = get_primary_ipv4()
        self._mask = get_netmask_for(self._ip)
        self._gw = get_default_gateway()
        self._interfaces = get_interfaces()

    @property
    def ip(self) -> str:
        return self._ip

    @property
    def mask(self) -> str:
        return self._mask

    @property
    def gw(self) -> str:
        return self._gw

    @property
    def interfaces(self) -> list[dict]:
        return self._interfaces

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def hostname() -> str:
        try:
            return socket.gethostname()
        except Exception:
            return ""

    @staticmethod
    def fqdn() -> str:
        try:
            return socket.getfqdn()
        except Exception:
            return ""

    @staticmethod
    def dns_servers() -> list[str]:
        """Best-effort DNS server list."""
        if IS_WINDOWS:
            out = _run(["ipconfig", "/all"])
            servers: list[str] = []
            capture = False
            for line in out.splitlines():
                low = line.lower()
                if "dns servers" in low or "dns-серверы" in low:
                    capture = True
                    if ":" in line:
                        after = line.split(":", 1)[1].strip()
                        if after and after[0].isdigit():
                            servers.append(after)
                    continue
                if capture:
                    if ":" in line:
                        continue
                    val = line.strip()
                    if val and val[0].isdigit():
                        servers.append(val)
                    else:
                        capture = False
            # de-dup preserving order
            seen = set()
            unique = []
            for s in servers:
                if s not in seen:
                    seen.add(s)
                    unique.append(s)
            return unique
        return []