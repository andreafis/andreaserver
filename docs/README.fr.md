# AndreaServer

**Le petit serveur de la maison.** AndreaServer transforme un mini PC sous DietPi en serveur domestique complet, en une seule commande.

[🇮🇹 Italiano](../README.md) · [🇬🇧 English](README.en.md) · [🇩🇪 Deutsch](README.de.md) · 🇫🇷 Français · [🇯🇵 日本語](README.ja.md)

## Ce qui est installé

| Quoi | À quoi ça sert | Où |
|---|---|---|
| Pi-hole | bloque la publicité sur tout le réseau | `http://IP/admin` |
| Jellyfin | films et musique sur TV, téléphone, navigateur | `http://IP:8096` |
| Samba | dossier partagé sur le réseau | `\\IP\Media` |
| WireGuard et OpenVPN | accès à la maison depuis l'extérieur | `dietpi-software` |
| Console web | état du serveur, graphiques, boutons | `http://IP:8088` |
| Bannière | résumé du serveur à chaque connexion | à la connexion |
| Shell texte | fenêtres, menus et souris dans le terminal | commande `D` |

Commandes rapides : `A` bannière · `D` Shell · `M` moniteur · `K` arrêter Jellyfin · `k` redémarrer Jellyfin · `R` redémarrage · `backup-server` sauvegarde de la configuration.

## Installation

1. Installez [DietPi](https://dietpi.com) (Debian) sur le mini PC et terminez le premier démarrage.
2. Branchez et montez les disques externes avec `dietpi-drive_manager`.
3. En root :

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/andreafis/andreaserver/main/bootstrap.sh) --lang fr
```

L'installation demande la langue, les disques, la ville pour la météo, le nom du dossier partagé et les mots de passe. Pendant l'installation des programmes, DietPi peut poser quelques questions (par exemple pour les VPN).

Sans questions : copiez `andreaserver.conf.example`, remplissez-le et lancez `./install.sh --config ma.conf`.

## Ce qu'il ne contient PAS

Le dépôt ne contient ni clés, ni mots de passe, ni jetons, ni adresses du domicile, ni données personnelles. Les clés VPN, mots de passe et certificats sont créés à neuf sur chaque machine. La configuration locale se trouve dans `/etc/andreaserver/andreaserver.conf` et ne doit pas être publiée. Avant chaque publication : `tools/check-secrets.sh`.

## À savoir

- Dérivé d'un serveur x86_64 sous DietPi 10 (Debian 12). L'installateur n'a pas encore été testé sur une machine vierge. DietPi est requis : sur une Debian nue, l'installateur s'arrête.
- Le dossier partagé peut être ouvert sans mot de passe (choix à l'installation) : à réserver à un réseau domestique de confiance.
- La bannière, la console web et le Shell sont pour l'instant en italien ; l'installateur et la documentation existent en cinq langues.
- Mettre à jour les fichiers de AndreaServer après un `git pull` : `/opt/andreaserver/install.sh --files-only`.

## Licence

[MIT](../LICENSE)
