#!/usr/bin/env python3
"""SessionStart : active Ponytail (niveau full) à chaque session, sans attendre /ponytail."""
import os
import pathlib

root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
skill = root / ".claude/skills/ponytail/SKILL.md"
text = skill.read_text(encoding="utf-8")
# Retire l'en-tête YAML, garde les règles.
if text.startswith("---"):
    text = text.split("---", 2)[2]
print("Ponytail est actif pour toute cette session (niveau full), sans que "
      "l'utilisateur ait à taper /ponytail. Règles :\n" + text.strip())
