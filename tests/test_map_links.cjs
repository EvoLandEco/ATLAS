const assert = require('node:assert/strict');
const { validateMapLinks, mapLinks, windowRecords } = require('../scripts/map_links.js');
const records = [
 {id:'a',publication:'2026-07-01',capture:'2026-09-25T12:00:00Z',claims:[{claim_index:0,quotes:['Source statement.']}]},
 {id:'b',publication:'2026-07-31T23:59:59Z',capture:'2026-09-26',claims:[{claim_index:1,quotes:['Follow-up.']}]},
 {id:'c',publication:'2026-08-01',capture:'2026-09-26',claims:[]}
];
const point={label:'Country',lon:10,lat:20,precision:'Country reference'};
const link={id:'travel',type:'movement',label:'Reported travel',basis:'Source describes travel.',limit:'Country scale.',directed:true,from:point,to:point,support:[['a',0],['b',1]]};
validateMapLinks([link],records);
assert.deepEqual(windowRecords(records,'2026-07-01','2026-07-31','publication').map(r=>r.id),['a','b']);
assert.deepEqual(windowRecords(records,'2026-09-26','2026-09-26','capture').map(r=>r.id),['b','c']);
assert.equal(mapLinks([link],records.slice(1)).length,0);
assert.equal(mapLinks([link],records).length,1);
assert.throws(()=>validateMapLinks([{...link,type:'disease'}],records));
assert.throws(()=>validateMapLinks([{...link,type:'hypothesis'}],records));
assert.throws(()=>validateMapLinks([{...link,support:[['a',99]]}],records));
assert.throws(()=>validateMapLinks([{...link,to:{...point,lat:100}}],records));
assert.throws(()=>validateMapLinks([link,link],records));
assert.throws(()=>windowRecords(records,'2026-08-01','2026-07-01','publication'));
console.log('Map rules: typed source links, quoted support, inclusive windows, capture dates and missing evidence pass.');
