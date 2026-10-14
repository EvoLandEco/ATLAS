import {test} from 'node:test';
import assert from 'node:assert/strict';
import {connectParent} from '../public/embedded.js';

test('embedded theme messages require the ATLAS parent and an exact theme', () => {
  const originalWindow = globalThis.window, originalDocument = globalThis.document;
  const listeners = new Map(), announcements = [], themes = [];
  const parent = {postMessage: (...args) => announcements.push(args)};
  globalThis.window = {parent, addEventListener: (type, handler) => listeners.set(type, handler)};
  globalThis.document = {documentElement: {dataset: {}}};
  try {
    connectParent(theme => themes.push(theme));
    assert.equal(document.documentElement.dataset.embedded, 'true');
    const message = {source: parent, origin: 'https://qtj.me', data: {type: 'atlas-review-theme', theme: 'dark'}};
    listeners.get('message')({...message, origin: 'https://another.example'});
    listeners.get('message')({...message, source: {}});
    listeners.get('message')({...message, data: {...message.data, theme: 'unknown'}});
    assert.deepEqual(themes, []);
    listeners.get('message')(message);
    listeners.get('message')({...message, data: {...message.data, theme: 'light'}});
    assert.deepEqual(themes, [true, false]);
    listeners.get('pagehide')();
    listeners.get('pageshow')();
    assert.deepEqual(announcements, [true, false, true].map(ready => [{type: 'atlas-review-ready', ready}, 'https://qtj.me']));
  } finally {
    globalThis.window = originalWindow;
    globalThis.document = originalDocument;
  }
});
