#!/usr/bin/env python3
"""UserPromptSubmit : au N-ième message d'une session, demande à Claude de proposer Graphify.

Une seule proposition par session. Seuil réglable par GRAPHIFY_NUDGE_AFTER (défaut 15).
"""
import json
import os
import pathlib
import sys
import tempfile

try:
    session = json.load(sys.stdin).get("session_id") or "sans-id"
except ValueError:
    session = "sans-id"

after = int(os.environ.get("GRAPHIFY_NUDGE_AFTER", "15"))
state = pathlib.Path(tempfile.gettempdir()) / "claude-graphify-nudge"
state.mkdir(exist_ok=True)
counter = state / f"{''.join(c for c in session if c.isalnum() or c in '-_')}.count"

try:
    count = int(counter.read_text()) + 1
except (OSError, ValueError):
    count = 1
counter.write_text(str(count))

if count != after:
    sys.exit(0)

print(
    f"[graphify] Cette session est longue ({count} messages). Avant de répondre au "
    "message ci-dessus, propose à l'utilisateur, avec AskUserQuestion (options « Oui » "
    "et « Non », sans autre question), de construire le graphe de connaissances du "
    "dépôt avec Graphify. S'il répond Oui : invoque le skill graphify sur le dépôt "
    "(/graphify .), puis envoie graphify-out/graph.html dans la conversation avec "
    "SendUserFile (display « render ») et résume GRAPH_REPORT.md en quelques lignes. "
    "S'il répond Non : n'en reparle plus de la session. Traite ensuite son message."
)
