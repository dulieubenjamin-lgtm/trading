#!/usr/bin/env bash
# Routine papier live : rafraichir le cache, regarder, archiver.
#
# Les trois etapes vont ensemble et dans cet ordre. Les separer invite a lancer
# la veille sur un cache perime -- ce que le script detecte, mais autant ne pas
# avoir a le detecter.
#
# POURQUOI CE SCRIPT COMMITE TOUT SEUL
# ------------------------------------
# La garantie centrale du protocole est que le PLAN precede l'ISSUE. Elle ne
# vaut que si l'horodatage est exterieur : c'est l'historique git qui en fait
# une preuve, pas la memoire de l'operateur. Un plan ecrit puis commite « quand
# j'y penserai » ne prouve plus rien -- et le jour ou l'on y pense le moins est
# precisement celui ou le trade est en cours.
#
# Le commit est donc mecanique, immediat, et fait avant que l'issue soit connue.
set -euo pipefail
cd "$(dirname "$0")"

python3 outils/telecharger.py --symbole XAU/USD --intervalle 5min --incremental
echo
# La veille sort en 3 quand le cache est perime : ce n'est pas une panne, et il
# reste un passage a archiver. On ne laisse passer que ce code-la.
code=0
python3 outils/veille.py || code=$?
if [ "$code" -ne 0 ] && [ "$code" -ne 3 ]; then
    exit "$code"
fi

# On n'ajoute que ce que la routine produit. Jamais -A : le depot peut contenir
# du travail en cours qui ne regarde pas la veille.
git add donnees/cache journal/papier-live 2>/dev/null || true
if git diff --cached --quiet; then
    exit "$code"
fi

plans=$(git diff --cached --name-only --diff-filter=A | grep '\.plan\.md$' || true)
if [ -n "$plans" ]; then
    message="plan: $(basename "$plans" .plan.md) — ecrit avant l'issue"
else
    message="veille: $(date -u '+%Y-%m-%d %H:%M')Z"
fi

git commit -q -m "$message"
echo "   commite : $message"
if git push -q origin HEAD 2>/dev/null; then
    echo "   pousse."
else
    echo "   PUSH ECHOUE (hors ligne ?). Le commit local existe et fait foi ;"
    echo "   relancer 'git push origin main' des que possible."
fi
exit "$code"
