import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(process.argv[2]);
const data = JSON.parse(fs.readFileSync(path.join(root, 'atlas-site.json'), 'utf8'));
const { selectView } = await import(pathToFileURL(path.join(root, 'view.mjs')));
const view = selectView(data, data.snapshot.publication_from, data.snapshot.publication_until);
process.stdout.write(JSON.stringify({
  record_ids: view.record_ids,
  assertion_ids: view.assertion_ids,
  comparison_ids: view.comparison_ids,
  superseded_assertion_ids: view.superseded_assertion_ids,
  relationship_ids: view.relationship_ids,
  reviewed_series: view.reviewed_series,
  one_health: view.one_health,
}));
