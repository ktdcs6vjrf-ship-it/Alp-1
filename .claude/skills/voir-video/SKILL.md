---
name: voir-video
description: >
  Regarder une vidéo en ligne (TikTok, Instagram, YouTube, X…) : la télécharger, en tirer 12 images régulières
  assemblées en une planche, plus le titre, l'auteur, la durée, la description et les sous-titres. À utiliser dès
  que l'utilisateur envoie un lien de vidéo ou demande de « regarder », « voir » ou « analyser » une vidéo.
---

# Voir une vidéo

Claude ne lit pas une vidéo en continu : il regarde des **images extraites** et lit le texte qui l'accompagne.

## Étapes

1. `bash "$CLAUDE_PROJECT_DIR/.claude/skills/voir-video/voir-video.sh" "<lien>" "<dossier du scratchpad>/video-<nom>"`
   (installe `yt-dlp` et un `ffmpeg` autonome au premier appel, dans un environnement Python à part).
2. Lire `planche.jpg` (12 images, de gauche à droite puis de haut en bas). Pour un détail, lire
   `image-01.jpg` … `image-12.jpg`, ou relancer `ffmpeg` sur `video.*` autour du moment voulu.
3. Lire le titre, la description et les sous-titres affichés (fichiers `.vtt` s'il y en a).
4. Décrire à l'utilisateur ce que montre la vidéo, moment par moment, en français.

## Si le téléchargement est bloqué

`Tunnel connection failed: 403` veut dire que le réseau de l'environnement refuse le serveur qui héberge le
fichier. Les métadonnées passent souvent quand même : lire les hôtes exacts dans `video.info.json`
(`formats[].url`), puis demander leur ajout avec `update_environment` (`add_allowed_hosts`, hôtes exacts, une phrase
d'explication avant). Les serveurs changent d'une plateforme et d'une vidéo à l'autre : si l'utilisateur veut
regarder beaucoup de vidéos, lui expliquer que l'accès réseau « illimité » de l'environnement évite ces demandes,
et le laisser choisir.

- **Instagram** demande souvent d'être connecté. Ne jamais demander de mot de passe dans la conversation ; proposer
  plutôt une capture d'écran ou un enregistrement envoyé directement.
- Aucune vidéo n'est publiée ni partagée : tout reste dans le scratchpad de la session.
