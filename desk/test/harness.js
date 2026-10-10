// Charge le socle et un desk dans node, sans navigateur, pour tester les fonctions pures.
// const { T, lib } = require('./harness')('risk');   puis lib.maFonction(...)
const fs = require('fs'), path = require('path'), vm = require('vm');
module.exports = function (deskId) {
  const root = path.join(__dirname, '..');
  const ctx = { console, Intl, Math, Date, JSON, Promise, setTimeout, clearTimeout, Array, Object, String, Number, Boolean, RegExp, Error, isFinite, isNaN, parseFloat, parseInt };
  ctx.window = ctx; ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(root, 'src', 'core.js'), 'utf8'), ctx, { filename: 'core.js' });
  const T = ctx.T;
  T.lib = T.lib || {};
  if (deskId) vm.runInContext('(function(){\n' + fs.readFileSync(path.join(root, 'src', 'desks', deskId + '.js'), 'utf8') + '\n})();', ctx, { filename: deskId + '.js' });
  return { T, lib: T.lib[deskId] || {} };
};
// Texte brut d'ALP nº 3 (une partie par fichier) : desk/ref/alp3txt dans le dépôt, ../alp3txt dans le scratchpad.
module.exports.ALP3 = [path.join(__dirname, '..', 'ref', 'alp3txt'), path.join(__dirname, '..', '..', 'alp3txt')].filter(d => fs.existsSync(d))[0] || path.join(__dirname, '..', 'ref', 'alp3txt');
