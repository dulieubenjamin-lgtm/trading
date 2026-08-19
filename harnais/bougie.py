"""Structure de bougie. Horodatage TOUJOURS en UTC, timezone-aware.

Aucune fonction de ce paquet n'accepte un datetime naif : c'est la premiere
ligne de defense contre le probleme de fuseau documente dans
donnees/twelve-data-constat.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Bougie:
    ts: datetime      # debut de la bougie, UTC aware
    ouverture: float
    haut: float
    bas: float
    cloture: float

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None or self.ts.utcoffset() is None:
            raise ValueError(f"horodatage naif interdit : {self.ts!r}")
        if self.ts.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError(f"horodatage non-UTC : {self.ts!r}")
        if not (self.bas <= self.ouverture <= self.haut
                and self.bas <= self.cloture <= self.haut):
            raise ValueError(f"OHLC incoherent : {self}")

    @property
    def amplitude(self) -> float:
        return self.haut - self.bas

    @property
    def corps(self) -> float:
        return abs(self.cloture - self.ouverture)

    @property
    def haussiere(self) -> bool:
        return self.cloture > self.ouverture

    @property
    def meche_haute(self) -> float:
        return self.haut - max(self.ouverture, self.cloture)

    @property
    def meche_basse(self) -> float:
        return min(self.ouverture, self.cloture) - self.bas
