"""Point d'entrée ALP-1.

    python main.py                    # tables quantitatives du paper
    python main.py --layers           # lexique des sigles et tables des couches
    python main.py --quant            # instruments de validation et de stress
    python main.py --alp2             # tables d'ALP-2, grille de notation comprise
    python main.py --prereg           # protocole scellé et son empreinte SHA-256
    python main.py --power            # protocole à horizon borné et son Monte-Carlo
    python main.py --measure [f.csv]  # exécute le protocole sur un historique
    python main.py --strategy [f.csv] # rejoue la stratégie scellée et sa batterie
    python main.py --hurst [f.csv]    # loi d'échelle mesurée, ratio de variance
    python main.py --bounds [f.csv]   # la mesure encadrée par les deux remplissages
    python main.py --edge             # témoin, catalogue de dérives, opérateur
    python main.py --risque           # géométrie serrée, spread, forçage, capital
    python main.py --tape <pseudo>    # enregistre un direct, une frappe par appel
    python main.py --diffuseur f.csv  # évalue un registre de diffuseur déjà collecté
    python main.py --paper            # reconstruit docs/alp1-paper.html
    python main.py --paper2           # reconstruit docs/alp2-paper.html
    python main.py --wp               # reconstruit le document de travail complet
    python main.py --disc             # journal de décision, lois nulles, attribution
    python main.py --discpaper        # reconstruit docs/prouver-un-jugement.html
    python main.py --tests            # suite de tests du noyau

Sans fichier, `--measure` fait tourner la chaîne de mesure sur une série
synthétique de vérité connue : c'est un test de la chaîne, pas une mesure du
marché. Le format attendu du fichier est décrit dans docs/donnees-requises.md.
"""

from __future__ import annotations

import sys


def main() -> int:
    if "--tests" in sys.argv:
        import unittest

        loader = unittest.TestLoader()
        suite = loader.discover("tests", top_level_dir=".")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

    if "--risque" in sys.argv:
        from alp1.report8 import main as report8_main

        report8_main()
        return 0

    if "--edge" in sys.argv:
        from alp1.report7 import main as report7_main

        report7_main()
        return 0

    if "--diffuseur" in sys.argv:
        from alp1.report7 import main as report7_main

        rest = sys.argv[sys.argv.index("--diffuseur") + 1:]
        files = [a for a in rest if not a.startswith("--")]
        report7_main(files[0] if files else "registre-inexistant")
        return 0

    if "--tape" in sys.argv:
        from alp1.broadcast import TAPE_HELP, record, to_csv

        rest = [a for a in sys.argv[sys.argv.index("--tape") + 1:]
                if not a.startswith("--")]
        if not rest:
            print("usage : python main.py --tape <pseudo> [instrument]")
            return 2
        pseudo = rest[0]
        instrument = rest[1] if len(rest) > 1 else "ES"
        print(TAPE_HELP)
        print(f"\nDiffuseur : {pseudo} — instrument : {instrument}\n")
        registre = record(pseudo, instrument, sys.stdin)
        sortie = to_csv(registre)
        chemin = f"data/{pseudo}.csv"
        try:
            with open(chemin, "w", encoding="utf-8") as f:
                f.write(sortie)
            print(f"\n{len(registre.calls)} appels écrits dans {chemin}")
        except OSError:
            print("\n" + sortie)
        for defaut in registre.audit():
            print(f"  défaut : {defaut}")
        return 0

    if "--layers" in sys.argv:
        from alp1.lexicon import main as lexicon_main

        lexicon_main()
        return 0

    if "--alp2" in sys.argv:
        from alp1.report2 import main as report2_main

        report2_main()
        return 0

    if "--prereg" in sys.argv:
        from alp1.prereg import main as prereg_main

        prereg_main()
        return 0

    if "--power" in sys.argv:
        from alp1.report4 import main as power_main

        power_main()
        return 0

    if "--hurst" in sys.argv:
        from alp1.varratio import main as varratio_main

        rest = sys.argv[sys.argv.index("--hurst") + 1:]
        files = [a for a in rest if not a.startswith("--")]
        varratio_main(files[0] if files else None)
        return 0

    if "--bounds" in sys.argv:
        from alp1.dataset import load_csv, synthetic_sessions
        from alp1.measure import bounds

        rest = sys.argv[sys.argv.index("--bounds") + 1:]
        files = [a for a in rest if not a.startswith("--")]
        if files:
            sessions, origine = load_csv(files[0]), files[0]
        else:
            sessions = synthetic_sessions(250, seed=20260821)
            origine = "série synthétique sans dérive"
        b = bounds(sessions)
        print(f"Encadrement par remplissage du stop — {origine}")
        print(f"{len(sessions)} séances, {b.optimistic.n_trades} trades, "
              f"{b.optimistic.stop_rate:.1%} d'arrêts\n")
        print(f"  remplissage au stop      net {b.optimistic.mean_net:+.4f} pt   "
              f"SR/trade {b.optimistic.sharpe_trade:+.4f}")
        print(f"  remplissage à l'extrême  net {b.worst.mean_net:+.4f} pt   "
              f"SR/trade {b.worst.sharpe_trade:+.4f}")
        print(f"\n  écart {b.spread_points:.4f} pt "
              f"({b.spread_fraction:.0%} de la borne optimiste)")
        print(f"  seuil {b.threshold:.4f} pt sur l'espérance nette "
              f"(la friction est déjà retranchée)")
        print(f"\n  {b.verdict}")
        return 0

    if "--strategy" in sys.argv:
        from alp1.strategy import main as strategy_main

        rest = sys.argv[sys.argv.index("--strategy") + 1:]
        files = [a for a in rest if not a.startswith("--")]
        strategy_main(files[0] if files else None)
        return 0

    if "--measure" in sys.argv:
        from alp1.measure import main as measure_main

        rest = sys.argv[sys.argv.index("--measure") + 1:]
        files = [a for a in rest if not a.startswith("--")]
        measure_main(files[0] if files else None,
                     files[1] if len(files) > 1 else None)
        return 0

    if "--quant" in sys.argv:
        from alp1.quant import main as quant_main

        quant_main()
        return 0

    if "--discpaper" in sys.argv:
        from alp1.discpaper import main as discpaper_main

        discpaper_main()
        return 0

    if "--disc" in sys.argv:
        from alp1.report10 import main as report10_main

        report10_main()
        return 0

    if "--wp" in sys.argv:
        from alp1.workingpaper import main as wp_main

        wp_main()
        return 0

    if "--paper2" in sys.argv:
        from alp1.paper2 import main as paper2_main

        paper2_main()
        return 0

    if "--paper" in sys.argv:
        from alp1.paper import main as paper_main

        paper_main()
        return 0

    from alp1.report import main as report_main

    report_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
