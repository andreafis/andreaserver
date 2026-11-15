# Banner AndreaServer al login (per tornare al banner DietPi: rm questo file e /root/.hushlogin)
[[ $- == *i* ]] && shopt -q login_shell && [[ -x /usr/local/bin/banner-andreaserver ]] && /usr/local/bin/banner-andreaserver
