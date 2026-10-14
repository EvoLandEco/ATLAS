/* Daily source selections retain their own evidence and weekly processing state. */
const formatter = new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Amsterdam', year:'numeric',month:'2-digit',day:'2-digit'});
function day(value) {
  if (value === null) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    if (!Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0,10) !== value) throw new Error('Invalid date');
    return value;
  }
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error('Timestamp needs an explicit timezone');
  const parts=Object.fromEntries(formatter.formatToParts(new Date(value)).map(p=>[p.type,p.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
export function selectDaily(data, from, until, basis='publication', knowledgeCutoff=null, sourceIds=null, countryCodes=null, asOf=null) {
  if (data.daily_version !== '0.2.1') throw new Error('Unsupported daily contract');
  if (day(from)!==from || day(until)!==until || from>until) throw new Error('Invalid daily date window');
  if (!['publication','capture'].includes(basis)) throw new Error('Invalid daily date basis');
  if (knowledgeCutoff!==null) { day(knowledgeCutoff); if (!knowledgeCutoff.includes('T')) throw new Error('Cutoff needs an explicit timezone'); }
  const cutoff=knowledgeCutoff===null ? Infinity : Date.parse(knowledgeCutoff);
  const assessmentTime=asOf ?? knowledgeCutoff ?? data.knowledge_cutoff;
  day(assessmentTime);
  if (!assessmentTime.includes('T')) throw new Error('Assessment time needs an explicit timezone');
  const at=Date.parse(assessmentTime);
  const sources=sourceIds===null ? null : new Set(sourceIds), countries=countryCodes===null ? null : new Set(countryCodes);
  const reconciled=new Set(data.reconciliations.filter(r=>r.disposition!=='pending' && r.weekly_export_id===data.base_source_export_id && Date.parse(r.reviewed_at)<=cutoff).map(r=>r.review_id));
  const documents=data.documents.filter(d=>{
    const date=day(d[basis]);
    return date!==null && date>=from && date<=until && Date.parse(d.capture)<=cutoff &&
      (sources===null || sources.has(d.source_id) || sources.has(d.channel_id));
  }).map(d=>{
    const reviewed=d.reviewed_at!==null && Date.parse(d.reviewed_at)<=cutoff;
    return {...d, outcome:reviewed?d.outcome:'pending', review_state:reviewed?d.review_state:'not_reviewed',
      processing_status:reconciled.has(d.review_id)?'weekly_reviewed':'weekly_review_pending',
      finding_ids:reviewed?d.finding_ids:[], country_codes:reviewed?d.country_codes:[],
      review_id:reviewed?d.review_id:null, reviewed_at:reviewed?d.reviewed_at:null,
      reviewed_by:reviewed?d.reviewed_by:null, title_translation:reviewed?d.title_translation:null,
      language_tag:reviewed?d.language_tag:'und', limitations:reviewed?d.limitations:['Daily evidence review pending.']};
  }).filter(d=>d.outcome!=='no_relevant_content' && (countries===null || d.country_codes.some(c=>countries.has(c))));
  const ids=new Set(documents.map(d=>d.id));
  const findings=data.findings.filter(f=>ids.has(f.document_id) && Date.parse(f.reviewed_at)<=cutoff);
  const fids=new Set(findings.map(f=>f.id));
  const eids=new Set(findings.flatMap(f=>f.evidence_ids));
  const eligible=w=>w.document_ids.every(d=>ids.has(d)) && w.finding_ids.every(f=>fids.has(f)) && Date.parse(w.reviewed_at)<=Math.min(cutoff,at);
  const supported=data.watch_items.filter(eligible);
  const watch_items=supported;
  return {documents, findings, evidence:data.evidence.filter(e=>eids.has(e.id)), watch_items,
    watch_assessments:data.watch_assessments.filter(eligible),
    overdue_watch_items:supported.filter(w=>at>=Date.parse(w.review_due_at)),
    watch_assessed_at:assessmentTime,
    pending_documents:documents.filter(d=>d.processing_status==='weekly_review_pending'),
    reconciliations:data.reconciliations.filter(r=>documents.some(d=>d.review_id===r.review_id) && Date.parse(r.reviewed_at)<=cutoff)};
}
