#!/bin/bash
# Demarre la veille trading le matin : Chrome TradingView (port 9222),
# Mac maintenu eveille, et lien avec l'app Claude Code.
# Usage : bash ~/trading/kasper/demarrer-veille.sh   (laisser la fenetre ouverte)
export PATH="$HOME/.local/bin:$PATH"

echo "1/3 Chrome TradingView..."
if curl -s http://localhost:9222/json/version >/dev/null; then
  echo "    deja ouvert sur le port 9222."
else
  # Les trois options --disable-* empechent Chrome de figer le graphique
  # quand la fenetre est en arriere-plan.
  open -na "Google Chrome" --args --remote-debugging-port=9222 \
    --user-data-dir="$HOME/chrome-tv-debug" \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-backgrounding-occluded-windows \
    https://www.tradingview.com/chart/
  for i in $(seq 1 20); do
    curl -s http://localhost:9222/json/version >/dev/null && break
    sleep 1
  done
fi
if curl -s http://localhost:9222/json/version >/dev/null; then
  echo "    OK : port 9222 joignable."
else
  echo "    ECHEC : Chrome ne repond pas sur le port 9222. Arret."
  exit 1
fi

echo "2/3 Mac maintenu eveille tant que cette fenetre reste ouverte."
echo "3/3 Lien avec l'app Claude Code (Ctrl+C pour tout arreter)."
cd "$HOME/claudeverstradingview" || exit 1
exec caffeinate -dimsu claude remote-control --spawn=same-dir
