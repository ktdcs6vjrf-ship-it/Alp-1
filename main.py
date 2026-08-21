"""Point d'entrée ALP-1.

    python main.py            # tables quantitatives du paper
    python main.py --layers   # lexique des sigles et tables des sept couches
    python main.py --quant    # instruments de validation, simulation et stress
    python main.py --paper    # reconstruit docs/alp1-paper.html
    python main.py --tests    # suite de tests du noyau
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

    if "--quant" in sys.argv:
        from alp1.quant import main as quant_main

        quant_main()
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
