#!/bin/bash
# AndreaServer - installatore.
# Trasforma una DietPi appena installata in un server di casa completo:
# Pi-hole, Jellyfin, Samba, OpenVPN, WireGuard, console web, banner, Shell testuale.
#
#   ./install.sh                  procedura guidata
#   ./install.sh --lang en        lingua: it en de fr ja
#   ./install.sh --config FILE    senza domande, usa un andreaserver.conf già pronto
#   ./install.sh --files-only     ricopia solo i file di AndreaServer (dopo un aggiornamento)
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONF_DIR=/etc/andreaserver
CONF=$CONF_DIR/andreaserver.conf
LOG=/var/tmp/andreaserver-install.log
DIETPI_SOFTWARE="pihole sambaserver openvpn wireguard jellyfin dropbear dietpiramlog git"
APT_EXTRA="btop htop mc nano jq curl ffmpeg smartmontools qrencode rsync python3 whiptail"

LANG_CODE=""; PRESET=""; FILES_ONLY=0
while [ $# -gt 0 ]; do
  case $1 in
    --lang) LANG_CODE=${2:-}; shift 2 ;;
    --config) PRESET=${2:-}; shift 2 ;;
    --files-only) FILES_ONLY=1; shift ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

# ---------- lingua ----------
if [ -z "$LANG_CODE" ] && [ -r "$CONF" ]; then LANG_CODE=$(sed -n 's/^ANDREASERVER_LANG=//p' "$CONF" | tr -d '"'); fi
if [ -z "$LANG_CODE" ] && [ -z "$PRESET" ] && command -v whiptail >/dev/null && [ -t 0 ]; then
  LANG_CODE=$(whiptail --title "AndreaServer" --menu "Lingua / Language / Sprache / Langue / 言語" 14 60 5 \
    it "Italiano" en "English" de "Deutsch" fr "Français" ja "日本語" 3>&1 1>&2 2>&3) || exit 1
fi
[ -r "$HERE/lang/${LANG_CODE:-it}.sh" ] || LANG_CODE=it
# shellcheck disable=SC1090
. "$HERE/lang/$LANG_CODE.sh"

die()  { echo "✗ $*" >&2; exit 1; }
step() { echo; echo "■ $*"; }
box()  { whiptail --title "$T_TITLE" --msgbox "$1" 16 74; }
ask()  { whiptail --title "$T_TITLE" --inputbox "$1" 12 74 "${2:-}" 3>&1 1>&2 2>&3; }
pass() { whiptail --title "$T_TITLE" --passwordbox "$1" 12 74 3>&1 1>&2 2>&3; }
confirm() { whiptail --title "$T_TITLE" --yesno "$1" 12 74; }

[ "$(id -u)" = 0 ] || die "$T_NEED_ROOT"
[ -x /boot/dietpi/dietpi-software ] || die "$T_NEED_DIETPI"

# ---------- rilevamento ----------
detect() {
  NIC=$(ip -4 route show default | awk '{print $5; exit}')
  NIC=${NIC:-eth0}
  local cidr
  cidr=$(ip -4 -o addr show dev "$NIC" | awk '{print $4; exit}')
  LAN_IP=${cidr%/*}
  LAN_NET=$(python3 -c 'import ipaddress,sys; print(ipaddress.ip_interface(sys.argv[1]).network)' "$cidr" 2>/dev/null || echo "${LAN_IP%.*}.0/24")
}
disk_of() {  # disco fisico che contiene un punto di montaggio (es. sda), "none" se non c'è
  local src pk
  src=$(findmnt -no SOURCE "$1" 2>/dev/null | grep '^/dev/' | head -1) || true
  [ -n "$src" ] || { echo none; return; }
  pk=$(lsblk -no PKNAME "$src" 2>/dev/null | head -1)
  echo "${pk:-none}"
}
pick_mount() {  # $1 = domanda, $2 = valore se "nessuno"
  local items=() line
  while read -r line; do
    [ -n "$line" ] && items+=("${line%% *}" "${line#* }")
  done < <(findmnt -rno TARGET,SIZE,FSTYPE -t ext4,ext3,hfsplus,exfat,ntfs,ntfs3,vfat,btrfs,xfs,fuseblk | grep -E '^/(mnt|media)/' || true)
  items+=("$2" "$T_NONE")
  whiptail --title "$T_TITLE" --menu "$1" 18 74 8 "${items[@]}" 3>&1 1>&2 2>&3
}
clean() { printf '%s' "$1" | tr -cd "[:alnum:] ._'-"; }

# ---------- procedura guidata ----------
wizard() {
  box "$T_WELCOME"
  if confirm "$T_DISKS_INFO"; then /boot/dietpi/dietpi-drive_manager || true; fi
  MEDIA_MOUNT=$(pick_mount "$T_MEDIA_Q" /mnt/media) || die "$T_CANCEL"
  INDEX_MOUNT=$(pick_mount "$T_INDEX_Q" /) || die "$T_CANCEL"

  CITY=$(clean "$(ask "$T_CITY_Q" "Roma")") || die "$T_CANCEL"
  local geo
  geo=$(curl -sf -m 8 -G "https://geocoding-api.open-meteo.com/v1/search" \
        --data-urlencode "name=$CITY" --data-urlencode "count=1" 2>/dev/null \
        | jq -r '.results[0] | "\(.latitude) \(.longitude)"' 2>/dev/null) || geo=""
  if [[ $geo =~ ^-?[0-9.]+\ -?[0-9.]+$ ]]; then
    LAT=${geo% *}; LON=${geo#* }
  else
    LAT=$(ask "$T_CITY_FAIL $T_LAT_Q" "41.9") || die "$T_CANCEL"
    LON=$(ask "$T_LON_Q" "12.5") || die "$T_CANCEL"
  fi
  [[ $LAT =~ ^-?[0-9.]+$ && $LON =~ ^-?[0-9.]+$ ]] || { LAT=41.9; LON=12.5; }

  SHARE_NAME=$(clean "$(ask "$T_SHARE_Q" "Media")") || die "$T_CANCEL"
  SHARE_NAME=${SHARE_NAME// /_}; SHARE_NAME=${SHARE_NAME:-Media}
  if confirm "$T_GUEST_Q"; then SHARE_GUEST=yes; else SHARE_GUEST=no; fi

  CONSOLE_PW=$(pass "$T_CONSOLE_PW_Q") || die "$T_CANCEL"
  PIHOLE_PW=$(pass "$T_PIHOLE_PW_Q") || die "$T_CANCEL"

  DUCK_DOMAIN=""; DUCK_TOKEN=""
  if confirm "$T_DUCK_Q"; then
    DUCK_DOMAIN=$(clean "$(ask "$T_DUCK_DOMAIN_Q" "")") || true
    DUCK_TOKEN=$(clean "$(pass "$T_DUCK_TOKEN_Q")") || true
  fi

  confirm "$(printf "$T_SUMMARY" "$NIC" "$LAN_IP" "$LAN_NET" "$MEDIA_MOUNT" "$INDEX_MOUNT" "$CITY" "$LAT" "$LON" "$SHARE_NAME" "$SHARE_GUEST" "${DUCK_DOMAIN:--}")" \
    || die "$T_CANCEL"
}

save_conf() {
  mkdir -p "$CONF_DIR"; chmod 700 "$CONF_DIR"
  DISK_SYS=$(disk_of /); DISK_MEDIA=$(disk_of "$MEDIA_MOUNT"); DISK_INDEX=$(disk_of "$INDEX_MOUNT")
  [ "$DISK_INDEX" = "$DISK_SYS" ] && DISK_INDEX=none
  [ "$DISK_MEDIA" = "$DISK_SYS" ] && DISK_MEDIA=none
  umask 077
  cat > "$CONF" <<EOF
# AndreaServer - configurazione di questa macchina (NON va messa su GitHub)
ANDREASERVER_LANG="$LANG_CODE"
NIC="$NIC"
LAN_IP="$LAN_IP"
LAN_NET="$LAN_NET"
MEDIA_MOUNT="$MEDIA_MOUNT"
INDEX_MOUNT="$INDEX_MOUNT"
DISK_SYS="$DISK_SYS"
DISK_MEDIA="$DISK_MEDIA"
DISK_INDEX="$DISK_INDEX"
CITY="$CITY"
LAT="$LAT"
LON="$LON"
SHARE_NAME="$SHARE_NAME"
SHARE_GUEST="$SHARE_GUEST"
DUCK_DOMAIN="$DUCK_DOMAIN"
DUCK_TOKEN="$DUCK_TOKEN"
EOF
  umask 022
}

# ---------- copia dei file con i valori di questa macchina ----------
render() {  # $1 sorgente  $2 destinazione  $3 permessi
  mkdir -p "$(dirname "$2")"
  sed -e "s|@@MEDIA_MOUNT@@|$MEDIA_MOUNT|g" \
      -e "s|@@INDEX_MOUNT@@/|${INDEX_MOUNT%/}/|g" -e "s|@@INDEX_MOUNT@@|$INDEX_MOUNT|g" \
      -e "s|@@LAN_IP@@|$LAN_IP|g" -e "s|@@LAN_NET@@|$LAN_NET|g" -e "s|@@NIC@@|$NIC|g" \
      -e "s|@@DISK_SYS@@|$DISK_SYS|g" -e "s|@@DISK_MEDIA@@|$DISK_MEDIA|g" -e "s|@@DISK_INDEX@@|$DISK_INDEX|g" \
      -e "s|@@CITY@@|$CITY|g" -e "s|@@LAT@@|$LAT|g" -e "s|@@LON@@|$LON|g" \
      -e "s|@@SHARE_NAME@@|$SHARE_NAME|g" -e "s|@@SHARE_GUEST@@|$SHARE_GUEST|g" "$1" > "$2"
  chmod "$3" "$2"
}
deploy_files() {
  local f rel mode
  while read -r f; do
    rel=${f#"$HERE/files"}
    case $rel in
      /etc/dshell/*) [ -e "$rel" ] && continue; mode=644 ;;   # non sovrascrive i tuoi elenchi
      /usr/local/bin/*) mode=755 ;;
      *) mode=644 ;;
    esac
    render "$f" "$rel" "$mode"
  done < <(find "$HERE/files" -type f ! -name '.*')
  ln -sf dshell /usr/local/bin/D
  ln -sf jellyfin-stop /usr/local/bin/K        # K = ferma Jellyfin
  ln -sf jellyfin-restart /usr/local/bin/k     # k = riavvia Jellyfin
  mkdir -p "$MEDIA_MOUNT"
  touch /root/.hushlogin
}

# ---------- passi ----------
install_software() {
  apt-get update -qq
  # shellcheck disable=SC2086
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $APT_EXTRA
  # shellcheck disable=SC2086
  /boot/dietpi/dietpi-software install $DIETPI_SOFTWARE
}
configure_pihole() {
  command -v pihole-FTL >/dev/null || return 0
  systemctl disable --now lighttpd 2>/dev/null || true      # la porta 80 è di Pi-hole
  pihole-FTL --config dns.upstreams '["8.8.8.8","1.1.1.1","208.67.222.222"]' >/dev/null
  pihole-FTL --config dns.interface "$NIC" >/dev/null
  pihole-FTL --config dns.queryLogging false >/dev/null
  pihole-FTL --config database.maxDBdays 2 >/dev/null
  pihole-FTL --config database.DBinterval 86400 >/dev/null
  pihole-FTL --config webserver.port "80,8489s" >/dev/null
  local url
  while read -r url; do
    [[ $url == http* ]] || continue
    pihole-FTL sqlite3 /etc/pihole/gravity.db \
      "INSERT OR IGNORE INTO adlist (address, enabled, comment) VALUES ('$url', 1, 'AndreaServer');" || true
  done < "$HERE/templates/pihole-adlists.txt"
  [ -n "${PIHOLE_PW:-}" ] && pihole setpassword "$PIHOLE_PW" >/dev/null
  systemctl restart pihole-FTL
  pihole -g >/dev/null 2>&1 || true
}
configure_samba() {
  [ -d /etc/samba ] || return 0
  [ -e /etc/samba/smb.conf ] && [ ! -e /etc/samba/smb.conf.prima-di-andreaserver ] && cp -a /etc/samba/smb.conf /etc/samba/smb.conf.prima-di-andreaserver
  render "$HERE/templates/smb.conf" /etc/samba/smb.conf 644
  systemctl restart smbd nmbd 2>/dev/null || true
}
configure_console() {
  mkdir -p /etc/console-andreaserver; chmod 700 /etc/console-andreaserver
  if [ -n "${CONSOLE_PW:-}" ]; then
    printf '%s\n' "$CONSOLE_PW" > /etc/console-andreaserver/password
  elif [ ! -s /etc/console-andreaserver/password ]; then
    head -c 12 /dev/urandom | base64 | tr -d '/+=' > /etc/console-andreaserver/password
    GENERATED_PW=1
  fi
  chmod 600 /etc/console-andreaserver/password
  systemctl daemon-reload
  systemctl enable --now console-andreaserver >/dev/null 2>&1 || true
  systemctl restart console-andreaserver || true
}
configure_duckdns() {
  [ -n "${DUCK_DOMAIN:-}" ] && [ -n "${DUCK_TOKEN:-}" ] || return 0
  mkdir -p /root/duckdns
  install -m 700 "$HERE/templates/duck.sh" /root/duckdns/duck.sh
  ( crontab -l 2>/dev/null | grep -v 'duckdns/duck.sh'; echo '*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1' ) | crontab -
}

# ---------- esecuzione ----------
if [ "$FILES_ONLY" = 1 ]; then
  [ -r "$CONF" ] || die "$T_NO_CONF"
  # shellcheck disable=SC1090
  . "$CONF"
  step "$T_STEP_FILES"; deploy_files; configure_console
  echo "✓ $T_DONE"; exit 0
fi

step "$T_PREREQ"
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq whiptail python3 curl jq >>"$LOG" 2>&1

detect
if [ -n "$PRESET" ]; then
  [ -r "$PRESET" ] || die "$T_NO_CONF"
  # shellcheck disable=SC1090
  . "$PRESET"
  CONSOLE_PW=${CONSOLE_PW:-}; PIHOLE_PW=${PIHOLE_PW:-}
else
  wizard
fi
save_conf

step "$T_STEP_SOFT";     install_software
step "$T_STEP_FILES";    deploy_files
step "$T_STEP_PIHOLE";   configure_pihole
step "$T_STEP_SAMBA";    configure_samba
step "$T_STEP_SERVICES"; configure_console; configure_duckdns

echo
echo "✓ $T_DONE"
# shellcheck disable=SC2059
printf "$T_DONE_DETAILS\n" "$LAN_IP" "$LAN_IP" "$LAN_IP" "$SHARE_NAME"
[ "${GENERATED_PW:-0}" = 1 ] && echo "$T_PW_GENERATED /etc/console-andreaserver/password"
exit 0
