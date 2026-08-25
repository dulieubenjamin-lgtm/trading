#!/usr/bin/env bash
# Routine papier live : rafraichir le cache, puis regarder.
#
# Les deux commandes vont ensemble et dans cet ordre. Les separer invite a
# lancer la veille sur un cache perime -- ce que le script detecte, mais
# autant ne pas avoir a le detecter.
set -euo pipefail
cd "$(dirname "$0")"

python3 outils/telecharger.py --symbole XAU/USD --intervalle 5min --incremental
echo
python3 outils/veille.py
