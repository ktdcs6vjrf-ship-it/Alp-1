#!/usr/bin/env node
/* Labo de stratégie — vérification d’une stratégie JSON avant que Claude l’écrive (LABO.md §2.9, §8).

   node tools/labo-check.js strategie.json [--dataset jeu.json] [--commission 1.24] [--values '{"k": -2}'] [--json]

   Le fichier contient une stratégie (§3), ou une liste de stratégies. L’outil charge les fichiers du desk par
   test/harness.js (une seule implémentation : T.lib.laboStats et T.lib.laboEngine) et imprime, pour chacune :
   les erreurs et les avertissements de normalize, la lecture en français (describe, côté vendeur reflété compris),
   le hachage scellé et le configHash. Code de sortie : 0 sans erreur, 1 si une stratégie porte une erreur,
   2 pour un appel mal formé (fichier illisible, option inconnue).

   --dataset    méta d’un jeu (document datasets/items) ou { meta, adj, levels } : vérifie les niveaux nommés
                (raccord des contrats, échelle NDX sans base).
   --commission commission aller-retour du réglage de l’utilisateur, figée dans le hachage au scellement quand la
                stratégie n’en déclare aucune.
   --values     valeurs imposées aux paramètres (comme un balayage) pour la lecture et les hachages.
   --json       sortie JSON (un objet par stratégie) au lieu du texte. */
'use strict';
const fs = require('fs'), path = require('path');
const HARNESS = path.resolve(__dirname, '..', 'test', 'harness.js');

let LIB = null;
function load() {
  if (!LIB) {
    const { T } = require(HARNESS)(['quant', 'labo-engine', 'labo-stats']);
    LIB = { T, LS: T.lib.laboStats };
  }
  return LIB;
}

/* check(raw, o) → { ok, errors, warnings, reading: [{id, title, text}], hash, configHash, hashNote, spec }.
   raw : objet ou texte JSON ; o = { dataset, commission, values }. */
function check(raw, o) {
  o = o || {};
  const { LS } = load();
  const ctx = {};
  if (o.dataset) ctx.dataset = o.dataset;
  const n = LS.normalize(raw, ctx);
  const res = { ok: n.errors.length === 0, errors: n.errors.slice(), warnings: n.warnings.slice(), reading: [], hash: null, configHash: null, hashNote: null, spec: n.spec };
  if (!n.spec) return res;
  try { res.reading = LS.describe(n.spec, { values: o.values }).map(x => ({ id: x.id, title: x.title, text: x.text })); }
  catch (e) { res.errors.push('lecture : ' + e.message); res.ok = false; }
  if (!res.ok) return res;
  try {
    const declared = n.spec.costs && typeof n.spec.costs.commissionRT === 'number';
    const com = typeof o.commission === 'number' && isFinite(o.commission) ? o.commission : undefined;
    res.hash = LS.hash(n.spec, com, o.values);
    res.configHash = LS.configHash(n.spec, o.values);
    res.hashNote = declared ? 'commission déclarée par la stratégie' : com !== undefined ? 'commission du réglage figée à ' + com + ' $' : 'commission non figée : la page la fige au scellement (--commission X pour la simuler)';
  } catch (e) { res.errors.push('hachage : ' + e.message); res.ok = false; }
  return res;
}

function parseArgs(argv) {
  const o = { files: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') o.json = true;
    else if (a === '--dataset' || a === '--commission' || a === '--values') {
      const v = argv[++i];
      if (v === undefined) throw new Error('valeur manquante après ' + a);
      if (a === '--dataset') o.dataset = JSON.parse(fs.readFileSync(v, 'utf8'));
      else if (a === '--commission') { o.commission = Number(String(v).replace(',', '.')); if (!isFinite(o.commission) || o.commission < 0) throw new Error('commission invalide : ' + v); }
      else { o.values = JSON.parse(v); if (!o.values || typeof o.values !== 'object' || Array.isArray(o.values)) throw new Error('--values attend un objet JSON'); }
    } else if (a === '-h' || a === '--help') o.help = true;
    else if (a.charAt(0) === '-' && a !== '-') throw new Error('option inconnue : ' + a);
    else o.files.push(a);
  }
  return o;
}

const USAGE = 'Usage : node tools/labo-check.js strategie.json [--dataset jeu.json] [--commission 1.24] [--values \'{"nom": 1}\'] [--json]';

function main(argv, out) {
  out = out || (s => process.stdout.write(s + '\n'));
  let o;
  try { o = parseArgs(argv); } catch (e) { out('Erreur : ' + e.message); out(USAGE); return 2; }
  if (o.help || !o.files.length) { out(USAGE); return o.help ? 0 : 2; }
  let docs = [];
  for (const f of o.files) {
    let raw;
    try { raw = JSON.parse(f === '-' ? fs.readFileSync(0, 'utf8') : fs.readFileSync(f, 'utf8')); }
    catch (e) { out('Erreur : ' + f + ' illisible (' + e.message + ').'); return 2; }
    (Array.isArray(raw) ? raw : [raw]).forEach((d, k) => docs.push({ file: f, k: Array.isArray(raw) ? k : null, raw: d }));
  }
  let bad = 0;
  const all = [];
  docs.forEach(d => {
    const r = check(d.raw, o);
    if (!r.ok) bad++;
    const name = (d.raw && d.raw.name) || (d.raw && d.raw.id) || 'stratégie sans nom';
    if (o.json) { all.push({ file: d.file, index: d.k, name, ok: r.ok, errors: r.errors, warnings: r.warnings, reading: r.reading, hash: r.hash, configHash: r.configHash, hashNote: r.hashNote }); return; }
    out('== ' + name + (d.k !== null ? ' (n° ' + (d.k + 1) + ')' : '') + ' — ' + d.file);
    out('Erreurs (' + r.errors.length + ')' + (r.errors.length ? ' :' : ''));
    r.errors.forEach(x => out('  ✗ ' + x));
    out('Avertissements (' + r.warnings.length + ')' + (r.warnings.length ? ' :' : ''));
    r.warnings.forEach(x => out('  ! ' + x));
    if (r.reading.length) {
      out('Lecture :');
      r.reading.forEach(x => out('  ' + x.title + ' — ' + x.text.replace(/ /g, ' ')));
    }
    if (r.hash) {
      out('Hachage scellé : ' + r.hash + ' (' + r.hashNote + ')');
      out('configHash     : ' + r.configHash);
    } else out('Hachage : impossible tant qu’une erreur reste.');
    out(r.ok ? 'Résultat : valide.' : 'Résultat : ' + r.errors.length + ' erreur' + (r.errors.length > 1 ? 's' : '') + ', à corriger avant d’écrire.');
    out('');
  });
  if (o.json) out(JSON.stringify(all.length === 1 ? all[0] : all, null, 2));
  return bad ? 1 : 0;
}

module.exports = { check, main, parseArgs };
if (require.main === module) process.exitCode = main(process.argv.slice(2));
