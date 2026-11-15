# AndreaServer

**Il piccolo server di casa.** AndreaServer trasforma un mini PC con DietPi in un server domestico completo con un solo comando.

🇮🇹 Italiano · [🇬🇧 English](docs/README.en.md) · [🇩🇪 Deutsch](docs/README.de.md) · [🇫🇷 Français](docs/README.fr.md) · [🇯🇵 日本語](docs/README.ja.md)

## Cosa installa

| Cosa | A cosa serve | Dove |
|---|---|---|
| Pi-hole | blocca la pubblicità su tutta la rete | `http://IP/admin` |
| Jellyfin | film e musica su TV, telefono, browser | `http://IP:8096` |
| Samba | cartella condivisa in rete | `\\IP\Media` |
| WireGuard e OpenVPN | accesso a casa da fuori | `dietpi-software` |
| Console web | stato del server, grafici, pulsanti | `http://IP:8088` |
| Banner | riepilogo del server a ogni accesso | al login |
| Shell testuale | finestre, menu e mouse nel terminale | comando `D` |

Comandi rapidi: `A` banner · `D` Shell · `M` monitor · `K` ferma Jellyfin · `k` riavvia Jellyfin · `R` riavvio · `backup-server` backup della configurazione.

## Installazione

1. Installa [DietPi](https://dietpi.com) (Debian) sul mini PC e completa il primo avvio.
2. Collega e monta i dischi esterni con `dietpi-drive_manager`.
3. Da root:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/andreafis/andreaserver/main/bootstrap.sh)
```

La procedura chiede lingua, dischi, città per il meteo, nome della cartella condivisa e password. Durante l'installazione dei programmi DietPi può fare qualche domanda (per esempio per le VPN).

Senza domande: copia `andreaserver.conf.example`, compilalo e lancia `./install.sh --config mio.conf`.

## Cosa NON contiene

Nel repository non ci sono chiavi, password, token, indirizzi di casa né dati personali. Chiavi VPN, password e certificati vengono creati nuovi su ogni macchina. La configurazione locale sta in `/etc/andreaserver/andreaserver.conf` e non va pubblicata. Prima di ogni pubblicazione: `tools/check-secrets.sh`.

## Da sapere

- Ricavato da un server x86_64 con DietPi 10 (Debian 12). L'installatore non è ancora stato provato su una macchina pulita. Serve DietPi: su Debian puro l'installatore si ferma.
- La cartella condivisa può essere aperta senza password (scelta durante l'installazione): va bene solo su una rete di casa fidata.
- Banner, console web e Shell sono per ora in italiano; installatore e documentazione sono in cinque lingue.
- Aggiornare i file di AndreaServer dopo un `git pull`: `/opt/andreaserver/install.sh --files-only`.

## Licenza

[MIT](LICENSE)
