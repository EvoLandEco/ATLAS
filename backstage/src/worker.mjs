import { createRemoteJWKSet, jwtVerify } from 'jose';
import validators from '../.generated/validate.cjs';
const { validatePacket, validateDecision, validateReceipts } = validators;

const MAX_JSON = 8_000_000;
const MAX_EVIDENCE = 16_000_000;
const SHA = /^[a-f0-9]{64}$/;
let keyIssuer, keys;

export class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}
export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
export async function sha256(value) {
  const bytes = typeof value === 'string' ? new TextEncoder().encode(value) : value;
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
}
export async function boundedBody(request, limit) {
  if (Number(request.headers.get('content-length')) > limit) throw new HttpError(413, 'Request exceeds the byte limit.');
  if (!request.body) throw new HttpError(400, 'Request body is required.');
  const reader = request.body.getReader(), chunks = [];
  let size = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) { await reader.cancel(); throw new HttpError(413, 'Request exceeds the byte limit.'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}
async function jsonBody(request) {
  if (!request.headers.get('content-type')?.startsWith('application/json')) throw new HttpError(415, 'Send application/json.');
  try { return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(await boundedBody(request, MAX_JSON))); }
  catch (error) { if (error instanceof HttpError) throw error; throw new HttpError(400, 'Invalid JSON.'); }
}
function schema(validate, value) {
  if (!validate(value)) throw new HttpError(400, 'Payload does not match the inbox 1.0.0 contract.');
}
export function identityFromClaims(claims, env) {
  if (claims.common_name && claims.common_name === env.SYNC_SERVICE_TOKEN_ID) return {service: true};
  const allowed = env.REVIEWER_EMAILS.split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
  if (typeof claims.email === 'string' && claims.sub && allowed.includes(claims.email.toLowerCase())) {
    return {service: false, email: claims.email.toLowerCase()};
  }
  throw new HttpError(403, 'This account does not have reviewer access.');
}
export async function authenticate(request, env) {
  if (!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.ACCESS_ISSUER || '') || !env.ACCESS_AUD || !env.REVIEWER_EMAILS) {
    throw new HttpError(503, 'Reviewer access is awaiting configuration.');
  }
  const token = request.headers.get('Cf-Access-Jwt-Assertion');
  if (!token || token.length > 16384) throw new HttpError(401, 'Sign in through Cloudflare Access.');
  if (keyIssuer !== env.ACCESS_ISSUER) {
    keyIssuer = env.ACCESS_ISSUER;
    keys = createRemoteJWKSet(new URL(`${keyIssuer}/cdn-cgi/access/certs`), {timeoutDuration: 5000});
  }
  let claims;
  try { claims = (await jwtVerify(token, keys, {issuer: env.ACCESS_ISSUER, audience: env.ACCESS_AUD, algorithms: ['RS256'], requiredClaims: ['exp','iat']})).payload; }
  catch { throw new HttpError(401, 'The Access session is invalid or expired.'); }
  return identityFromClaims(claims, env);
}
function json(value, status = 200) {
  const body = JSON.stringify(value);
  if (new TextEncoder().encode(body).byteLength > 16_000_000) throw new HttpError(413, 'Response exceeds 16000000 bytes.');
  return new Response(body, {status, headers: {'Content-Type': 'application/json; charset=utf-8'}});
}
function safeResponse(response) {
  const headers = new Headers(response.headers);
  headers.set('Cache-Control', 'private, no-store');
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('Referrer-Policy', 'no-referrer');
  headers.set('X-Frame-Options', 'DENY');
  headers.set('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");
  return new Response(response.body, {status: response.status, headers});
}
async function active(db) { return db.prepare('SELECT s.* FROM active_snapshot a JOIN snapshots s USING(snapshot_id)').first(); }
async function issueFor(db, issueId) {
  return db.prepare(`SELECT v.payload FROM issue_versions v JOIN snapshot_items i USING(issue_id, revision)
    JOIN active_snapshot a USING(snapshot_id) WHERE i.issue_id=?`).bind(issueId).first();
}
async function lastDecision(db, issueId) {
  const row = await db.prepare('SELECT * FROM decisions WHERE issue_id=? ORDER BY seq DESC LIMIT 1').bind(issueId).first();
  if (!row) return null;
  const receipt = await db.prepare('SELECT payload FROM receipts WHERE decision_id=? ORDER BY seq DESC LIMIT 1').bind(row.decision_id).first();
  return {decision: JSON.parse(row.payload), receipt: receipt ? JSON.parse(receipt.payload) : null};
}

export function makeDecision(input, identity, env, now = new Date().toISOString()) {
  const allowed = ['decision_id','snapshot_id','issue_id','revision','previous_decision_id','action','rationale','event_key','public_rationale','supersedes_candidate_ids','allow_disease_reclassification','numeric_evidence_reviews'];
  if (!input || Array.isArray(input) || typeof input !== 'object' || Object.keys(input).some(k => !allowed.includes(k))) throw new HttpError(400, 'Unknown decision fields.');
  const value = {inbox_version: '1.0.0', archive_id: env.ATLAS_ARCHIVE_ID,
    previous_decision_id: null, event_key: null, public_rationale: 'Editorial review', supersedes_candidate_ids: [],
    allow_disease_reclassification: false, numeric_evidence_reviews: {}, ...input,
    reviewer: identity.email, submitted_at: now};
  schema(validateDecision, value);
  if ((value.action === 'accept') !== Boolean(value.event_key?.trim())) throw new HttpError(400, 'Acceptance requires an event key.');
  if (value.action !== 'accept' && (value.supersedes_candidate_ids.length || value.allow_disease_reclassification || Object.keys(value.numeric_evidence_reviews).length)) throw new HttpError(400, 'These fields require acceptance.');
  if (Object.values(value.numeric_evidence_reviews).some(x => typeof x !== 'string' || x.trim().length < 10 || x.length > 500)) throw new HttpError(400, 'Numeric verification needs a source explanation of 10 to 500 characters.');
  return value;
}
async function submitDecision(request, env, identity, db) {
  const input = await jsonBody(request);
  const value = makeDecision(input, identity, env);
  const old = await db.prepare('SELECT payload FROM decisions WHERE decision_id=?').bind(value.decision_id).first();
  if (old) {
    const previous = JSON.parse(old.payload);
    value.submitted_at = previous.submitted_at;
    if (canonical(value) !== canonical(previous)) throw new HttpError(409, 'Decision ID already identifies another submission.');
    return json(previous);
  }
  const row = await issueFor(db, value.issue_id);
  if (!row) throw new HttpError(409, 'This issue is absent from the current review packet.');
  const issue = JSON.parse(row.payload);
  if (issue.kind === 'registry' ? value.action === 'instruct' : !['instruct','defer'].includes(value.action)) throw new HttpError(400, 'Action does not match this review type.');
  try {
    await db.prepare(`INSERT INTO decisions(decision_id,issue_id,revision,previous_decision_id,snapshot_id,sha256,payload)
      VALUES(?,?,?,?,?,?,?)`).bind(value.decision_id, value.issue_id, value.revision, value.previous_decision_id,
      value.snapshot_id, await sha256(canonical(value)), canonical(value)).run();
  } catch { throw new HttpError(409, 'The issue or decision changed. Reload its history before submitting.'); }
  return json(value, 201);
}
async function publishSnapshot(request, env, db) {
  const packet = await jsonBody(request);
  schema(validatePacket, packet);
  if (packet.archive_id !== env.ATLAS_ARCHIVE_ID) throw new HttpError(400, 'Archive identity differs.');
  if (new Set(packet.issues.map(i => i.issue_id)).size !== packet.issues.length) throw new HttpError(400, 'Duplicate issue identity.');
  const payload = canonical(packet), wireHash = await sha256(payload);
  const old = await db.prepare('SELECT * FROM snapshots WHERE snapshot_id=?').bind(packet.snapshot_id).first();
  if (old) {
    if (old.wire_sha256 !== wireHash) throw new HttpError(409, 'Snapshot identity has different content.');
    return json({snapshot_id: old.snapshot_id, current: (await active(db))?.snapshot_id === old.snapshot_id});
  }
  const current = await active(db);
  if (current && packet.sequence <= current.sequence) throw new HttpError(409, 'A later archive snapshot is active.');
  const versions = await db.prepare(`SELECT v.issue_id,v.payload FROM issue_versions v JOIN json_each(?) i
    ON v.issue_id=json_extract(i.value,'$.issue_id') AND v.revision=json_extract(i.value,'$.revision')`)
    .bind(JSON.stringify(packet.issues.map(({issue_id,revision})=>({issue_id,revision})))).all();
  const previous = new Map(versions.results.map(row=>[row.issue_id,row.payload]));
  const checked = new Set();
  for (const issue of packet.issues) {
    if (new TextEncoder().encode(canonical(issue)).byteLength > 500_000) throw new HttpError(413, 'Issue exceeds 500000 bytes.');
    if (previous.has(issue.issue_id) && previous.get(issue.issue_id) !== canonical(issue)) throw new HttpError(409, 'Issue revision has different content.');
    for (const evidence of issue.evidence) {
      if (checked.has(evidence.sha256)) continue;
      const object = await env.EVIDENCE.head(`evidence/${evidence.sha256}.txt`);
      if (!object || object.size !== evidence.bytes || object.customMetadata?.sha256 !== evidence.sha256) throw new HttpError(409, 'Captured evidence must be uploaded before the review packet.');
      checked.add(evidence.sha256);
    }
  }
  await env.EVIDENCE.put(`snapshots/${packet.snapshot_id}.json`, payload, {httpMetadata: {contentType: 'application/json'}});
  const statements = [db.prepare('INSERT INTO snapshots VALUES(?,?,?,?,?)').bind(packet.snapshot_id, packet.archive_id, packet.sequence, packet.generated_at, wireHash)];
  for (const issue of packet.issues) {
    statements.push(db.prepare('INSERT OR IGNORE INTO issue_versions VALUES(?,?,?)').bind(issue.issue_id, issue.revision, canonical(issue)));
    statements.push(db.prepare('INSERT INTO snapshot_items VALUES(?,?,?)').bind(packet.snapshot_id, issue.issue_id, issue.revision));
  }
  statements.push(db.prepare(`INSERT INTO active_snapshot VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE
    SET snapshot_id=excluded.snapshot_id,sequence=excluded.sequence WHERE excluded.sequence>active_snapshot.sequence`).bind(packet.snapshot_id, packet.sequence));
  try { await db.batch(statements); }
  catch { throw new HttpError(409, 'Snapshot publication conflicted with another upload.'); }
  return json({snapshot_id: packet.snapshot_id, current: (await active(db))?.snapshot_id === packet.snapshot_id});
}
async function acceptReceipts(request, db, env) {
  const batch = await jsonBody(request);
  schema(validateReceipts, batch);
  const statements = [];
  for (const receipt of batch.receipts) {
    const decision = await db.prepare('SELECT * FROM decisions WHERE decision_id=?').bind(receipt.decision_id).first();
    if (!decision || decision.sha256 !== receipt.decision_sha256 || decision.issue_id !== receipt.issue_id || decision.revision !== receipt.revision || receipt.archive_id !== env.ATLAS_ARCHIVE_ID) throw new HttpError(409, 'Receipt does not identify the submitted decision.');
    const expected = receipt.status === 'completed' ? 'passed' : ['applied','recorded'].includes(receipt.status) ? 'pending' : 'not_required';
    if (receipt.validation !== expected || (receipt.status === 'completed') !== Boolean(receipt.export_id)) throw new HttpError(400, 'Receipt validation must match its application status.');
    const payload = canonical(receipt), hash = await sha256(payload);
    statements.push(db.prepare(`INSERT INTO receipts(sha256,decision_id,status,payload)
      SELECT ?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM receipts WHERE sha256=?)`).bind(hash, receipt.decision_id, receipt.status, payload, hash));
  }
  if (statements.length) {
    try { await db.batch(statements); } catch { throw new HttpError(409, 'Receipt history does not permit this transition.'); }
  }
  return json({received: batch.receipts.length});
}
async function syncRoute(request, path, env, db) {
  if (path.startsWith('evidence/') && request.method === 'PUT') {
    const hash = path.slice(9);
    if (!SHA.test(hash)) throw new HttpError(400, 'Invalid evidence identity.');
    const bytes = await boundedBody(request, MAX_EVIDENCE);
    if (await sha256(bytes) !== hash) throw new HttpError(400, 'Evidence checksum differs.');
    try { new TextDecoder('utf-8', {fatal: true}).decode(bytes); } catch { throw new HttpError(400, 'Evidence must be UTF-8 text.'); }
    await env.EVIDENCE.put(`evidence/${hash}.txt`, bytes, {httpMetadata: {contentType: 'text/plain; charset=utf-8'}, customMetadata: {sha256: hash}});
    return json({sha256: hash});
  }
  if (path === 'snapshot' && request.method === 'POST') return publishSnapshot(request, env, db);
  if (path === 'decisions' && request.method === 'GET') {
    const rows = await db.prepare(`SELECT payload FROM decisions d WHERE NOT EXISTS
      (SELECT 1 FROM receipts r WHERE r.decision_id=d.decision_id) ORDER BY seq LIMIT 200`).all();
    return json({inbox_version: '1.0.0', decisions: rows.results.map(r => JSON.parse(r.payload))});
  }
  if (path === 'receipts' && request.method === 'POST') return acceptReceipts(request, db, env);
  throw new HttpError(404, 'Unknown synchronization route.');
}
export async function route(request, env, identity) {
  const url = new URL(request.url), base = env.INBOX_PATH;
  if (url.origin !== env.INBOX_ORIGIN || !base?.startsWith('/') || !base.endsWith('/')) throw new HttpError(404, 'Unknown inbox address.');
  if (url.pathname === base.slice(0, -1)) return Response.redirect(url.origin + base, 308);
  if (!url.pathname.startsWith(base)) throw new HttpError(404, 'Unknown inbox address.');
  const path = url.pathname.slice(base.length);
  const db = env.DB.withSession('first-primary');
  if (path.startsWith('api/sync/')) {
    if (!identity.service) throw new HttpError(403, 'Synchronization requires the ATLAS service identity.');
    return syncRoute(request, path.slice(9), env, db);
  }
  if (identity.service) throw new HttpError(403, 'Use the synchronization API.');
  if (!['GET','HEAD'].includes(request.method)) {
    if (request.headers.get('Origin') !== env.INBOX_ORIGIN || request.headers.get('X-Atlas-Review') !== '1') throw new HttpError(403, 'Submit decisions from the reviewer interface.');
  }
  if (path === 'api/me' && request.method === 'GET') return json({email: identity.email, archive_id: env.ATLAS_ARCHIVE_ID});
  if (path === 'api/issues' && request.method === 'GET') {
    const snapshot = await active(db);
    const rows = await db.prepare(`SELECT v.payload FROM issue_versions v JOIN snapshot_items i USING(issue_id,revision)
      JOIN active_snapshot a USING(snapshot_id) ORDER BY i.issue_id`).all();
    const issues = [];
    for (const row of rows.results) {
      const issue = JSON.parse(row.payload), last = await lastDecision(db, issue.issue_id);
      issues.push({...issue, last});
    }
    return json({snapshot, issues});
  }
  if (path === 'api/history' && request.method === 'GET') {
    const before = Number(url.searchParams.get('before') || Number.MAX_SAFE_INTEGER);
    if (!Number.isSafeInteger(before) || before < 1) throw new HttpError(400, 'Invalid history cursor.');
    const issueId = url.searchParams.get('issue');
    const rows = await db.prepare(`SELECT d.seq,d.payload,v.payload AS issue FROM decisions d
      JOIN issue_versions v USING(issue_id,revision) WHERE d.seq<? AND (? IS NULL OR d.issue_id=?) ORDER BY d.seq DESC LIMIT 10`).bind(before, issueId, issueId).all();
    const entries = [];
    for (const row of rows.results) {
      const decision = JSON.parse(row.payload);
      const receipts = await db.prepare('SELECT payload FROM receipts WHERE decision_id=? ORDER BY seq').bind(decision.decision_id).all();
      entries.push({seq: row.seq, decision, issue: JSON.parse(row.issue), receipts: receipts.results.map(r => JSON.parse(r.payload))});
    }
    return json({entries, next: entries.length === 10 ? entries.at(-1).seq : null});
  }
  if (path === 'api/decisions' && request.method === 'POST') return submitDecision(request, env, identity, db);
  if (path.startsWith('api/evidence/') && request.method === 'GET') {
    const hash = path.slice(13);
    if (!SHA.test(hash)) throw new HttpError(400, 'Invalid evidence identity.');
    const object = await env.EVIDENCE.get(`evidence/${hash}.txt`);
    if (!object) throw new HttpError(404, 'Captured evidence is unavailable.');
    return new Response(object.body, {headers: {'Content-Type': 'text/plain; charset=utf-8'}});
  }
  if (path.startsWith('api/')) throw new HttpError(404, 'Unknown API route.');
  if (!['GET','HEAD'].includes(request.method)) throw new HttpError(405, 'Method not allowed.');
  url.pathname = '/' + path;
  return env.ASSETS.fetch(new Request(url, request));
}
export default {
  async fetch(request, env) {
    try { return safeResponse(await route(request, env, await authenticate(request, env))); }
    catch (error) { return safeResponse(json({error: error instanceof HttpError ? error.message : 'The reviewer service could not complete this request.'}, error instanceof HttpError ? error.status : 500)); }
  },
};
