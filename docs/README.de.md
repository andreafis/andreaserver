# AndreaServer

**Der kleine Heimserver.** AndreaServer macht aus einem Mini-PC mit DietPi mit einem einzigen Befehl einen vollständigen Heimserver.

[🇮🇹 Italiano](../README.md) · [🇬🇧 English](README.en.md) · 🇩🇪 Deutsch · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md)

## Was installiert wird

| Was | Wozu | Wo |
|---|---|---|
| Pi-hole | blockiert Werbung im gesamten Netzwerk | `http://IP/admin` |
| Jellyfin | Filme und Musik auf TV, Handy, Browser | `http://IP:8096` |
| Samba | freigegebener Netzwerkordner | `\\IP\Media` |
| WireGuard und OpenVPN | Zugriff von unterwegs | `dietpi-software` |
| Web-Konsole | Serverstatus, Diagramme, Schaltflächen | `http://IP:8088` |
| Banner | Serverübersicht bei jeder Anmeldung | beim Login |
| Text-Shell | Fenster, Menüs und Maus im Terminal | Befehl `D` |

Kurzbefehle: `A` Banner · `D` Shell · `M` Monitor · `K` Jellyfin stoppen · `k` Jellyfin neu starten · `R` Neustart · `backup-server` Sicherung der Konfiguration.

## Installation

1. [DietPi](https://dietpi.com) (Debian) auf dem Mini-PC installieren und den ersten Start abschließen.
2. Externe Festplatten anschließen und mit `dietpi-drive_manager` einhängen.
3. Als root:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/andreafis/andreaserver/main/bootstrap.sh) --lang de
```

Die Einrichtung fragt nach Sprache, Festplatten, Stadt für das Wetter, Name der Freigabe und Passwörtern. Während der Installation der Programme stellt DietPi eventuell ein paar Fragen (zum Beispiel zu den VPNs).

Ohne Fragen: `andreaserver.conf.example` kopieren, ausfüllen und `./install.sh --config meine.conf` starten.

## Was NICHT enthalten ist

Das Repository enthält keine Schlüssel, Passwörter, Tokens, Heimadressen oder persönlichen Daten. VPN-Schlüssel, Passwörter und Zertifikate werden auf jedem Rechner neu erzeugt. Die lokale Konfiguration liegt in `/etc/andreaserver/andreaserver.conf` und darf nicht veröffentlicht werden. Vor jeder Veröffentlichung: `tools/check-secrets.sh`.

## Gut zu wissen

- Abgeleitet von einem x86_64-Server mit DietPi 10 (Debian 12). Der Installer wurde noch nicht auf einem frischen Rechner getestet. DietPi ist erforderlich: Auf reinem Debian bricht der Installer ab.
- Die Freigabe kann ohne Passwort geöffnet werden (Auswahl bei der Einrichtung): nur für ein vertrauenswürdiges Heimnetz geeignet.
- Banner, Web-Konsole und Shell gibt es vorerst nur auf Italienisch; Installer und Dokumentation liegen in fünf Sprachen vor.
- AndreaServer-Dateien nach einem `git pull` aktualisieren: `/opt/andreaserver/install.sh --files-only`.
