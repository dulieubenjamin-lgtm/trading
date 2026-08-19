"""VueMarche : l'acces a l'historique qui rend le look-ahead impossible.

Le mode replay de TradingView garantit l'aveuglement au futur par construction :
le graphique s'arrete a la bougie courante. Ici, le harnais dispose de tout
l'historique en memoire — rien n'empeche techniquement une regle de lire la
bougie suivante, et une telle erreur ne se voit pas dans les resultats : elle
les rend simplement excellents.

VueMarche retablit la garantie mecanique. Une regle ne recoit jamais la liste
des bougies, seulement une vue bornee a l'indice courant. Tout acces au-dela
leve RegardVersLeFutur.

Indexation : 0 = bougie courante, -1 = precedente, -2 = l'avant-precedente.
Volontairement differente de l'indexation Python, pour qu'on ne puisse pas
ecrire par reflexe un acces qui viserait le futur.
"""
from __future__ import annotations


class RegardVersLeFutur(IndexError):
    """Une regle a tente de lire une donnee posterieure a la bougie courante."""


class VueMarche:
    __slots__ = ("_bougies", "_i", "_series")

    def __init__(self, bougies, i: int, series: dict | None = None):
        self._bougies = bougies
        self._i = i
        self._series = series or {}

    @property
    def indice(self) -> int:
        return self._i

    @property
    def courante(self):
        return self._bougies[self._i]

    def __len__(self) -> int:
        return self._i + 1

    def __getitem__(self, decalage: int):
        if decalage > 0:
            raise RegardVersLeFutur(
                f"decalage {decalage} : 0 est la bougie courante, "
                f"les valeurs positives sont le futur"
            )
        idx = self._i + decalage
        if idx < 0:
            raise IndexError(f"decalage {decalage} : avant le debut de l'historique")
        return self._bougies[idx]

    def indicateur(self, nom: str, decalage: int = 0):
        """Valeur d'une serie pre-calculee, bornee par la meme regle."""
        if decalage > 0:
            raise RegardVersLeFutur(f"indicateur {nom!r}, decalage {decalage} : futur")
        idx = self._i + decalage
        if idx < 0:
            raise IndexError(f"indicateur {nom!r}, decalage {decalage} : avant le debut")
        if nom not in self._series:
            raise KeyError(f"serie inconnue : {nom!r} (connues : {sorted(self._series)})")
        return self._series[nom][idx]

    def fenetre(self, longueur: int):
        """Les `longueur` dernieres bougies, courante incluse, ordre chronologique."""
        if longueur <= 0:
            raise ValueError("longueur doit etre positive")
        debut = max(0, self._i + 1 - longueur)
        return self._bougies[debut: self._i + 1]
