import {readFileSync,writeFileSync} from 'node:fs';

const required=['CLOUDFLARE_ACCOUNT_ID','ATLAS_INBOX_DATABASE_ID','INBOX_ORIGIN','ACCESS_ISSUER','ACCESS_AUD','SYNC_SERVICE_TOKEN_ID'];
for(const key of required)if(!process.env[key]?.trim())throw new Error(`${key} is required.`);
if(!/^[a-f0-9]{32}$/.test(process.env.CLOUDFLARE_ACCOUNT_ID))throw new Error('Invalid Cloudflare account ID.');
if(!/^[a-f0-9-]{36}$/.test(process.env.ATLAS_INBOX_DATABASE_ID)||process.env.ATLAS_INBOX_DATABASE_ID==='00000000-0000-0000-0000-000000000000')throw new Error('Invalid D1 database ID.');
if(!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(process.env.ACCESS_ISSUER))throw new Error('ACCESS_ISSUER must identify the Cloudflare Access team.');
const origin=new URL(process.env.INBOX_ORIGIN);
if(origin.protocol!=='https:'||origin.origin!==process.env.INBOX_ORIGIN)throw new Error('INBOX_ORIGIN must be an HTTPS origin without credentials, path, query or fragment.');
const config=JSON.parse(readFileSync(new URL('wrangler.jsonc',import.meta.url)));
config.account_id=process.env.CLOUDFLARE_ACCOUNT_ID;
config.d1_databases[0].database_id=process.env.ATLAS_INBOX_DATABASE_ID;
for(const key of ['INBOX_ORIGIN','ACCESS_ISSUER','ACCESS_AUD','SYNC_SERVICE_TOKEN_ID'])config.vars[key]=process.env[key];
writeFileSync(new URL('wrangler.local.json',import.meta.url),JSON.stringify(config,null,2)+'\n');
console.log('Deployment configuration saved. Authentication secrets remain in the environment.');
