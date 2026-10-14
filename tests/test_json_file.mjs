import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseJsonBytes} from '../scripts/json-file.mjs';

test('Chunked parsing preserves UTF-8, escapes and JSON values', () => {
  const text = '{"__proto__":{"test":true},"rows":' + JSON.stringify(Array.from({length:50000},(_,i)=>({i,text:'鳥 🐦 '+String.fromCharCode(34,92),value:i%2 ? null : -1.25e-7}))) + '}';
  const actual = parseJsonBytes(Buffer.from(text));
  assert.deepEqual(actual,JSON.parse(text));
  assert.equal(Object.getPrototypeOf(actual),Object.prototype);
  for (const invalid of ['',text.slice(0,-1),text+' null','{"x":01}']) assert.throws(()=>parseJsonBytes(Buffer.from(invalid)));
});
