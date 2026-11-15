#!/bin/bash
# DuckDNS: aggiorna l'indirizzo pubblico. Dominio e token stanno in /etc/andreaserver/andreaserver.conf
. /etc/andreaserver/andreaserver.conf
echo url="https://www.duckdns.org/update?domains=${DUCK_DOMAIN}&token=${DUCK_TOKEN}&ip=" | curl -s -o ~/duckdns/duck.log -K -
