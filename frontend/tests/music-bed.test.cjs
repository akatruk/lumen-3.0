const {test} = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('vm');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');

const src = path.resolve(__dirname, '../src');
const cache = {};
function load(name) {
  if (cache[name]) return cache[name];
  const filename = fs.existsSync(path.join(src, name + '.tsx')) ? name + '.tsx' : name + '.ts';
  const code = ts.transpileModule(fs.readFileSync(path.join(src, filename), 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX},
    fileName: filename,
  }).outputText;
  const exports = {};
  vm.runInNewContext(code, {
    exports,
    require: id => id === 'react' || id === 'react/jsx-runtime' ? require(id) : load(id.replace('./', '')),
  }, {filename});
  return cache[name] = exports;
}

const bed = load('musicBed');
const {MusicBedList, MusicCandidateList} = load('MusicBedList');
const tracks = [
  {key: 'curated:cipher', title: 'Cipher', artist: 'Kevin MacLeod', mood: 'energetic', duration: 231.26, origin: 'curated', available: true, license: 'CC BY 4.0'},
  {key: 'curated:carefree', title: 'Carefree', artist: 'Kevin MacLeod', mood: 'uplifting', duration: 205.1, origin: 'curated', available: true, license: 'CC BY 4.0'},
  {key: 'curated:missing', title: 'Missing', artist: 'Kevin MacLeod', mood: 'calm', duration: 10, origin: 'curated', available: false},
];

function tag(html, value) {
  const found = html.match(new RegExp('<input\\b[^>]*\\bvalue="' + value + '"[^>]*>'));
  assert.ok(found, value);
  return found[0];
}

test('catalogue bed selection is visible and not blocked by a render or unsaved edit', () => {
  assert.equal(bed.bedKeyForAsset({id: 'a'.repeat(32), metadata: {catalogue_id: 'cipher', reused_from: 'curated:cipher'}}), 'curated:cipher');
  assert.equal(bed.projectAssetForTrack('curated:cipher', [{id: 'asset1', metadata: {catalogue_id: 'cipher'}}]), 'asset1');
  assert.equal(bed.bedControlDisabled(true), false);
  assert.equal(bed.formatClock(231.26), '3:51');
  const html = renderToStaticMarkup(React.createElement(MusicBedList, {lang: 'ru', tracks, selectedKey: 'curated:cipher', group: 'music-bed', onSelect() {}}));
  const cipher = tag(html, 'curated:cipher');
  assert.match(cipher, /\bchecked(?:=|"|\s|>)/);
  assert.equal(cipher.includes('disabled'), false);
  assert.equal(tag(html, 'curated:carefree').includes('checked'), false);
  assert.equal(tag(html, 'curated:carefree').includes('disabled'), false);
  assert.match(tag(html, 'curated:missing'), /\bdisabled(?:=|"|\s|>)/);
  assert.match(html, /Выбрано/);
  assert.match(html, /Энергичное · 3:51 · Kevin MacLeod · CC BY 4\.0/);
  assert.match(html, /Carefree/);
});

test('AI candidate checkboxes check without a paid call and stop at three', () => {
  const listed = value => Array.from(value).join(',');
  assert.equal(listed(bed.toggleCandidate([], 'asset1', true)), 'asset1');
  assert.equal(listed(bed.toggleCandidate(['asset1'], 'asset1', false)), '');
  assert.equal(listed(bed.toggleCandidate(['a', 'b', 'c'], 'd', true)), 'a,b,c');
  assert.equal(bed.candidateControlDisabled({busy: false, checked: false, chosen: 0, available: true}), false);
  assert.equal(bed.candidateControlDisabled({busy: false, checked: true, chosen: 3, available: true}), false);
  assert.equal(bed.candidateControlDisabled({busy: false, checked: false, chosen: 3, available: true}), true);
  const html = renderToStaticMarkup(React.createElement(MusicCandidateList, {
    lang: 'ru',
    tracks,
    chosenIds: ['asset1'],
    busyKey: '',
    assetIdFor: key => key === 'curated:cipher' ? 'asset1' : null,
    onToggle() {},
  }));
  const cipher = tag(html, 'curated:cipher');
  assert.match(cipher, /\bchecked(?:=|"|\s|>)/);
  assert.equal(cipher.includes('disabled'), false);
  assert.equal(tag(html, 'curated:carefree').includes('disabled'), false);
  assert.match(html, /1\/3/);
  assert.match(html, /Cipher/);
  assert.match(html, /Carefree/);
});
