# AndreaServer

**The little home server.** AndreaServer turns a mini PC running DietPi into a complete home server with a single command.

[🇮🇹 Italiano](../README.md) · 🇬🇧 English · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md)

## What it installs

| What | What it does | Where |
|---|---|---|
| Pi-hole | blocks ads on the whole network | `http://IP/admin` |
| Jellyfin | films and music on TV, phone, browser | `http://IP:8096` |
| Samba | network shared folder | `\\IP\Media` |
| WireGuard and OpenVPN | reach home from outside | `dietpi-software` |
| Web console | server status, charts, buttons | `http://IP:8088` |
| Banner | server summary at every login | at login |
| Text Shell | windows, menus and mouse in the terminal | command `D` |

Quick commands: `A` banner · `D` Shell · `M` monitor · `K` stop Jellyfin · `k` restart Jellyfin · `R` reboot · `backup-server` configuration backup.

## Installation

1. Install [DietPi](https://dietpi.com) (Debian) on the mini PC and complete the first boot.
2. Connect and mount external disks with `dietpi-drive_manager`.
3. As root:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/andreafis/andreaserver/main/bootstrap.sh) --lang en
```

The setup asks for language, disks, city for the weather, shared folder name and passwords. While software is being installed, DietPi may ask a few questions (for example for the VPNs).

Unattended: copy `andreaserver.conf.example`, fill it in and run `./install.sh --config my.conf`.

## What it does NOT contain

The repository holds no keys, passwords, tokens, home addresses or personal data. VPN keys, passwords and certificates are created fresh on every machine. Local configuration lives in `/etc/andreaserver/andreaserver.conf` and must not be published. Before every publish: `tools/check-secrets.sh`.

## Good to know

- Derived from an x86_64 server running DietPi 10 (Debian 12). The installer has not yet been tested on a clean machine. DietPi is required: on plain Debian the installer stops.
- The shared folder can be opened without a password (your choice during setup): only suitable for a trusted home network.
- Banner, web console and Shell are Italian-only for now; the installer and documentation come in five languages.
- To refresh AndreaServer's files after a `git pull`: `/opt/andreaserver/install.sh --files-only`.
