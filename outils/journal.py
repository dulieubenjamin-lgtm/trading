"""Le journal : ou en est le protocole papier live.

    python3 outils/journal.py            # au terminal
    python3 outils/journal.py --html     # page a ouvrir dans le navigateur

CE QUE CE JOURNAL MONTRE, ET CE QU'IL REFUSE DE FAIRE
=====================================================
Il montre TOUT : chaque trade, le R moyen courant, la discipline de veille. Rien
n'est masque, et c'est deliberatement le contraire d'un tableau de bord qui
cacherait le resultat jusqu'a l'echeance.

Cacher serait a la fois condescendant et inefficace -- additionner dix nombres
visibles ne demande pas d'effort. Ce qui protege reellement d'une lecture
prematuree n'est pas le secret, c'est le CONTEXTE : a n = 12, l'intervalle de
confiance couvre a peu pres tout ce qui est concevable. Affiche a cote de la
moyenne, il rend la sur-interpretation difficile plutot qu'interdite.

Le journal affiche donc systematiquement l'intervalle avec la moyenne, et
rappelle ou se situent les bornes de decision pre-enregistrees. La discipline
vient de la regle d'arret ecrite d'avance, pas d'une donnee dissimulee.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

GEL = "specs/papier-live.json"
JOURNAL = Path("journal/papier-live")

# Quantiles de Student a 95 %, par degres de liberte. A petit n, utiliser 1,96
# retrecirait l'intervalle exactement la ou il doit etre large.
T95 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31,
       9: 2.26, 10: 2.23, 12: 2.18, 15: 2.13, 20: 2.09, 25: 2.06, 30: 2.04,
       40: 2.02, 60: 2.00, 120: 1.98}


def t95(df: int) -> float:
    if df < 1:
        return float("nan")
    for seuil in sorted(T95):
        if df <= seuil:
            return T95[seuil]
    return 1.96


def lire_entete(chemin: Path) -> dict:
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    entete = {}
    for ligne in lignes[1:]:
        if ligne.strip() == "---":
            break
        if ":" in ligne:
            cle, val = ligne.split(":", 1)
            entete[cle.strip()] = val.strip()
    return entete


def premier_commit(chemin: Path) -> datetime | None:
    """Date du commit qui a AJOUTE ce fichier — la preuve d'anteriorite."""
    try:
        sortie = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "--", str(chemin)],
            capture_output=True, text=True, timeout=10).stdout.strip()
        return datetime.fromisoformat(sortie.splitlines()[-1]) if sortie else None
    except Exception:
        return None


def rassembler() -> dict:
    g = json.loads(Path(GEL).read_text(encoding="utf-8"))
    calcule = hashlib.sha256(
        json.dumps(g["spec"], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    veilles = []
    registre = JOURNAL / "veilles.csv"
    if registre.exists():
        for ligne in registre.read_text(encoding="utf-8").splitlines()[1:]:
            if ligne.strip():
                champs = ligne.split(";")
                veilles.append({"quand": champs[0], "statut": champs[2],
                                "signaux": champs[3], "empreinte": champs[4]})

    trades = []
    for plan in sorted(JOURNAL.glob("*.plan.md")):
        e = lire_entete(plan)
        issue_p = plan.with_name(plan.name.replace(".plan.md", ".issue.md"))
        t = {"id": e["id"], "sens": e.get("sens", "?"),
             "entree": float(e["entree"]), "stop": float(e["stop"]),
             "objectif": float(e["objectif"]), "signal": e["bougie_signal"],
             "issue": None, "r": None, "sortie": None, "anteriorite": None}
        if issue_p.exists():
            i = lire_entete(issue_p)
            t.update(issue=i["issue"], r=float(i["r"]), sortie=i["sortie_le"],
                     duree=i.get("duree_h"))
            # Le plan a-t-il ete commite AVANT la sortie du trade ?
            commit = premier_commit(plan)
            if commit:
                sortie = datetime.strptime(i["sortie_le"], "%Y-%m-%d %H:%MZ") \
                    .replace(tzinfo=timezone.utc)
                t["anteriorite"] = commit < sortie
        trades.append(t)

    return {"spec": g, "empreinte_ok": calcule == g["empreinte"],
            "empreinte_calculee": calcule, "veilles": veilles, "trades": trades}


def stats(trades):
    rs = [t["r"] for t in trades if t["r"] is not None]
    n = len(rs)
    if n == 0:
        return {"n": 0}
    moy = sum(rs) / n
    if n < 2:
        return {"n": n, "moyenne": moy, "total": sum(rs), "bas": None, "haut": None,
                "gagnants": sum(1 for r in rs if r > 0)}
    sd = (sum((r - moy) ** 2 for r in rs) / (n - 1)) ** 0.5
    marge = t95(n - 1) * sd / n ** 0.5
    return {"n": n, "moyenne": moy, "total": sum(rs), "ecart_type": sd,
            "bas": moy - marge, "haut": moy + marge,
            "gagnants": sum(1 for r in rs if r > 0)}


PALIERS = [(50, "arret si R moyen <= -0,20"), (100, "arret si R moyen <= 0"),
           (250, "verdict : t > 2 soutient l'hypothese, sinon non concluant")]


def prochain_palier(n):
    for seuil, regle in PALIERS:
        if n < seuil:
            return seuil, regle
    return None, None


def au_terminal(d):
    s = stats(d["trades"])
    spec = d["spec"]
    print(f"\n  JOURNAL PAPIER LIVE — {spec['spec']['nom']}")
    print(f"  {'=' * 62}\n")

    marque = "verifiee" if d["empreinte_ok"] else "!! MODIFIEE !!"
    print(f"  specification  {spec['empreinte']}  ({marque}, gelee le {spec['gele_le']})")
    if not d["empreinte_ok"]:
        print(f"                 calculee : {d['empreinte_calculee']}")
        print("                 LE COMPTAGE EN COURS EST INVALIDE.")

    v = d["veilles"]
    couvrantes = [x for x in v if x["statut"] == "ok"]
    print(f"  veille         {len(v)} passages, dont {len(couvrantes)} couvrants")
    if v:
        print(f"                 dernier : {v[-1]['quand']} ({v[-1]['statut']})")

    print(f"\n  TRADES ({s['n']} denoues, "
          f"{sum(1 for t in d['trades'] if t['r'] is None)} en cours)")
    if not d["trades"]:
        print("    aucun encore. En moyenne un signal tous les six jours ouvres.")
    else:
        print(f"    {'id':18s} {'sens':6s} {'issue':10s} {'R':>7s}  anteriorite")
        for t in d["trades"]:
            if t["r"] is None:
                print(f"    {t['id']:18s} {t['sens']:6s} {'EN COURS':10s} {'':>7s}")
            else:
                a = {True: "ok", False: "NON", None: "?"}[t["anteriorite"]]
                print(f"    {t['id']:18s} {t['sens']:6s} {t['issue']:10s} "
                      f"{t['r']:+7.3f}  {a}")

    if s["n"]:
        print(f"\n  RESULTAT COURANT")
        print(f"    R moyen    {s['moyenne']:+.3f}   total {s['total']:+.1f} R"
              f"   reussite {100 * s['gagnants'] / s['n']:.0f} %")
        if s.get("bas") is not None:
            large = s["haut"] - s["bas"]
            print(f"    intervalle [{s['bas']:+.3f} ; {s['haut']:+.3f}] a 95 %")
            if large > 0.5:
                print(f"    -> large de {large:.2f} R : a ce stade la moyenne ne "
                      f"distingue rien.")
        else:
            print("    intervalle : indefini a n = 1.")

    seuil, regle = prochain_palier(s["n"])
    print(f"\n  PROCHAIN PALIER")
    if seuil is None:
        print("    tous les paliers sont franchis — appliquer la regle de verdict.")
    else:
        reste = seuil - s["n"]
        print(f"    n = {seuil}  ({reste} trades restants, "
              f"environ {reste / 61.6 * 12:.0f} mois au rythme observe)")
        print(f"    regle pre-enregistree : {regle}")
    print("\n    Aucune decision avant un palier. C'est la regle ecrite d'avance,")
    print("    et c'est elle qui protege — pas l'ignorance du chiffre.\n")


def en_html(d, chemin: Path):
    s = stats(d["trades"])
    spec = d["spec"]
    seuil, regle = prochain_palier(s["n"])
    ok = d["empreinte_ok"]

    lignes = []
    for t in d["trades"]:
        if t["r"] is None:
            lignes.append(f"<tr><td>{t['id']}</td><td>{t['sens']}</td>"
                          f"<td colspan=3 class=ouvert>en cours</td></tr>")
        else:
            cl = "gain" if t["r"] > 0 else "perte"
            a = {True: "✓", False: "✗", None: "?"}[t["anteriorite"]]
            lignes.append(
                f"<tr><td>{t['id']}</td><td>{t['sens']}</td><td>{t['issue']}</td>"
                f"<td class={cl}>{t['r']:+.3f} R</td><td>{a}</td></tr>")
    corps = "\n".join(lignes) or "<tr><td colspan=5 class=vide>Aucun trade " \
        "denoue. En moyenne un signal tous les six jours ouvres.</td></tr>"

    if s["n"] and s.get("bas") is not None:
        bloc = f"""<div class=chiffre><span class=gros>{s['moyenne']:+.3f}</span>
        <span class=unite>R moyen sur {s['n']} trades</span></div>
        <p class=ic>Intervalle de confiance a 95 % :
        <strong>[{s['bas']:+.3f} ; {s['haut']:+.3f}]</strong>{
        ' — large de ' + format(s['haut'] - s['bas'], '.2f') +
        ' R, la moyenne ne distingue rien a ce stade.'
        if s['haut'] - s['bas'] > 0.5 else ''}</p>"""
    elif s["n"]:
        bloc = f"<div class=chiffre><span class=gros>{s['moyenne']:+.3f}</span>" \
               f"<span class=unite>R, un seul trade</span></div>"
    else:
        bloc = "<p class=vide>Le comptage n'a pas commence.</p>"

    couvrantes = sum(1 for x in d['veilles'] if x['statut'] == 'ok')
    palier = (f"<strong>n = {seuil}</strong> — {seuil - s['n']} trades restants, "
              f"environ {(seuil - s['n']) / 61.6 * 12:.0f} mois au rythme observe."
              f"<br><span class=regle>Regle pre-enregistree : {regle}</span>"
              if seuil else "Tous les paliers sont franchis.")

    chemin.write_text(f"""<!doctype html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Journal papier live — XAU</title><style>
:root{{--fond:#fbfbf9;--carte:#fff;--texte:#1a1a18;--doux:#6b6b64;--trait:#e4e4de;
--gain:#1a7f5a;--perte:#b4442e;--accent:#2c5f8a}}
@media(prefers-color-scheme:dark){{:root{{--fond:#16161a;--carte:#1e1e23;
--texte:#e8e8e4;--doux:#9a9a92;--trait:#2e2e35;--gain:#4ec49a;--perte:#e0765c;
--accent:#7aa8d0}}}}
*{{box-sizing:border-box}}body{{margin:0;padding:2rem 1rem;background:var(--fond);
color:var(--texte);font:16px/1.6 ui-sans-serif,-apple-system,Segoe UI,sans-serif}}
main{{max-width:52rem;margin:0 auto}}
h1{{font-size:1.5rem;margin:0 0 .25rem}}
.sous{{color:var(--doux);margin:0 0 2rem;font-size:.9rem}}
.carte{{background:var(--carte);border:1px solid var(--trait);border-radius:10px;
padding:1.25rem 1.5rem;margin-bottom:1.25rem}}
h2{{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;
color:var(--doux);margin:0 0 1rem;font-weight:600}}
.chiffre{{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap}}
.gros{{font-size:2.5rem;font-weight:600;font-variant-numeric:tabular-nums}}
.unite{{color:var(--doux)}}
.ic{{margin:.75rem 0 0;color:var(--doux);font-size:.92rem}}
table{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
th,td{{text-align:left;padding:.5rem .4rem;border-bottom:1px solid var(--trait)}}
th{{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--doux)}}
.gain{{color:var(--gain);font-weight:600}}.perte{{color:var(--perte);font-weight:600}}
.ouvert,.vide{{color:var(--doux);font-style:italic}}
.regle{{color:var(--doux);font-size:.9rem}}
.alerte{{border-color:var(--perte);border-width:2px}}
.note{{color:var(--doux);font-size:.88rem;margin:1rem 0 0;
border-left:2px solid var(--trait);padding-left:.9rem}}
code{{font-size:.85em;background:var(--fond);padding:.1em .35em;border-radius:3px}}
</style></head><body><main>
<h1>Journal papier live — XAU/USD</h1>
<p class=sous>{spec['spec']['nom']} · genere le
{datetime.now(timezone.utc):%d/%m/%Y %H:%M} UTC</p>

<div class="carte{'' if ok else ' alerte'}"><h2>Specification</h2>
<p><code>{spec['empreinte']}</code> — {'verifiee' if ok else
'<strong>MODIFIEE — le comptage en cours est invalide</strong>'},
gelee le {spec['gele_le']}.</p>
<p class=regle>{len(d['veilles'])} passages de veille, dont {couvrantes} couvrants.</p></div>

<div class=carte><h2>Resultat courant</h2>{bloc}
<p class=note>L'intervalle est affiche avec la moyenne, toujours. Ce qui protege
d'une lecture prematuree n'est pas de cacher le chiffre — additionner des nombres
visibles ne demande aucun effort — mais de voir a quel point il est encore
indetermine.</p></div>

<div class=carte><h2>Trades</h2><table>
<tr><th>Signal</th><th>Sens</th><th>Issue</th><th>R</th><th>Plan anterieur</th></tr>
{corps}</table>
<p class=note>« Plan anterieur » verifie dans l'historique git que le plan a ete
commite avant la sortie du trade. C'est le verrou anti-biais, et il est
controle, pas suppose.</p></div>

<div class=carte><h2>Prochain palier</h2><p>{palier}</p>
<p class=note>Aucune decision n'est prise entre deux paliers. Un bon resultat
precoce ne valide rien et n'autorise ni a augmenter la taille, ni a passer en
reel : les bornes anticipees ne servent qu'a abandonner tot.</p></div>
</main></body></html>""", encoding="utf-8")
    print(f"page ecrite : {chemin}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", action="store_true",
                    help="ecrit une page a ouvrir dans le navigateur")
    args = ap.parse_args()
    d = rassembler()
    if args.html:
        cible = JOURNAL / "journal.html"
        en_html(d, cible)
        print(f"   ouvrir avec :  open {cible}")
    else:
        au_terminal(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
