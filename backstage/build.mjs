import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import Ajv from 'ajv';
import standalone from 'ajv/dist/standalone/index.js';

const ajv = new Ajv({code: {source: true, lines: true}, strict: false, allErrors: true});
for (const name of ['inbox', 'inbox-decision', 'inbox-receipts']) {
  const schema = JSON.parse(readFileSync(new URL(`../schemas/${name}.schema.json`, import.meta.url)));
  ajv.addSchema(schema, name);
}
mkdirSync(new URL('.generated', import.meta.url), {recursive: true});
writeFileSync(new URL('.generated/validate.cjs', import.meta.url), standalone(ajv, {
  validatePacket: 'inbox', validateDecision: 'inbox-decision', validateReceipts: 'inbox-receipts',
}));
