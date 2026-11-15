#!/bin/bash
# Controlla che nel repository non ci siano segreti o dati personali.
# Da eseguire prima di ogni pubblicazione:  tools/check-secrets.sh
cd "$(dirname "$0")/.." || exit 1
bad=0
check() {  # $1 descrizione  $2 espressione regolare  $3 (facoltativo) testo da ignorare
  local out
  out=$(grep -rnIE --exclude-dir=.git --exclude=check-secrets.sh -e "$2" . | grep -vF -e "${3:-@@mai@@}" | cut -c1-140)
  if [ -n "$out" ]; then echo "✗ $1"; echo "$out" | sed 's/^/    /'; bad=1; else echo "✓ $1"; fi
}
check "chiavi private"                  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
check "chiavi WireGuard"                '(PrivateKey|PresharedKey|PublicKey) *= *[A-Za-z0-9+/]{43}='
check "token o password valorizzati"    '(token|password|passwd|pwhash)[A-Za-z_]* *[=:] *["'"'"']?[A-Za-z0-9$+/_-]{12,}'
check "UUID di dischi o token"          '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
check "indirizzi IP di casa"            '192\.168\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+'
check "indirizzi e-mail"                '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|it|org|net)\b'
check "nomi DuckDNS reali"              '[a-z0-9-]+\.duckdns\.org' 'www.duckdns.org'
check "chiavi SSH"                      'ssh-(rsa|ed25519) AAAA'
for f in $(find . -path ./.git -prune -o -type f \( -name '*.key' -o -name '*.pem' -o -name '*.ovpn' -o -name 'andreaserver.conf' -o -name '*.tar.gz' \) -print); do
  echo "✗ file da non pubblicare: $f"; bad=1
done
[ $bad = 0 ] && echo "Tutto pulito." || echo "TROVATO QUALCOSA: non pubblicare finché non è risolto."
exit $bad
