import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

test('sign-in returns only a completion signal to ATLAS', () => {
  const script = readFileSync(new URL('../public/sign-in.js', import.meta.url), 'utf8');
  const messages = [];
  let closed = false;
  runInNewContext(script, {window: {
    opener: {postMessage: (...args) => messages.push(args)},
    close: () => { closed = true; },
  }});
  assert.equal(JSON.stringify(messages), JSON.stringify([[{type: 'atlas-review-signed-in'}, 'https://qtj.me']]));
  assert.equal(closed, true);
  closed = false;
  runInNewContext(script, {window: {opener: null, close: () => { closed = true; }}});
  assert.equal(closed, false);
});
