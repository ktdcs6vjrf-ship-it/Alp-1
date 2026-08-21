"""Point d'entrée ALP-1.

    python main.py                    # tables quantitatives du paper
    python main.py --layers           # lexique des sigles et tables des couches
    python main.py --quant            # instruments de validation et de stress
    python main.py --alp2             # tables d'ALP-2, grille de notation comprise
    python main.py --prereg           # protocole scellé et son empreinte SHA-256
    python main.py --measure [f.csv]  # exécute le protocole sur un historique
    python main.py --paper            # reconstruit docs/alp1-paper.html
    python main.py --paper2           # reconstruit docs/alp2-paper.html
    python main.py --wp               # reconstruit le document de travail complet
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
