const $ = id => document.getElementById(id);
function setTheme(dark) {
  document.documentElement.dataset.theme=dark?'dark':'light';
  $('theme').setAttribute('aria-checked',String(dark));
  $('theme').title=dark?'Switch to light mode':'Switch to dark mode';
}
setTheme(matchMedia('(prefers-color-scheme: dark)').matches);
$('theme').onclick=()=>setTheme($('theme').getAttribute('aria-checked')!=='true');
const labels = {pending:'Needs a decision',submitted:'Submitted',recorded:'Awaiting application',applied:'Awaiting validation',deferred:'Deferred',stale:'Evidence changed',invalid:'Needs attention',completed:'Completed'};
const kinds = {registry:'Event registry',geography:'Geography',longitudinal:'Numerical comparisons',chain:'Chains',one_health:'One Health',extraction:'Extraction',source:'Sources',research:'Research'};
const state = {issues:[],snapshot:null,selected:null,historyCursor:null,tab:'inbox'};
function el(tag, text, className) { const node=document.createElement(tag); if(text!==undefined)node.textContent=text; if(className)node.className=className; return node; }
function message(text, error=false) { $('message').textContent=text; $('message').className=text?`notice${error?' error':''}`:''; }
async function api(path, data) {
  const response=await fetch(`./api/${path}`, data ? {method:'POST',headers:{'Content-Type':'application/json','X-Atlas-Review':'1'},body:JSON.stringify(data)} : {});
  if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('Your access session needs renewal. Reload this page to sign in.');
  const result=await response.json();if(!response.ok)throw new Error(result.error||'Request failed.');return result;
}
function status(issue){return issue.last?.receipt?.status||(issue.last?'submitted':'pending');}
function badge(value){return el('span',labels[value]||value,`badge${['stale','invalid','applied'].includes(value)?' attention':''}`);}
function time(value){return new Date(value).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});}
function metadata(text){return el('p',text,'meta');}
function showList(){
  const search=$('search').value.toLowerCase(),kind=$('kind').value,filter=$('status').value;
  const items=state.issues.filter(i=>(!kind||i.kind===kind)&&(!filter||status(i)===filter)&&`${i.title} ${i.question} ${i.issue_id}`.toLowerCase().includes(search));
  $('issues').replaceChildren();$('count').textContent=state.issues.length;
  if(!items.length)$('issues').append(el('p','No issues match this view.','meta'));
  const rank={high:0,normal:1,low:2};items.sort((a,b)=>rank[a.priority]-rank[b.priority]||b.changed_at.localeCompare(a.changed_at));
  for(const issue of items){const button=el('button',undefined,`issue${state.selected===issue.issue_id?' active':''}`);button.type='button';button.setAttribute('aria-pressed',String(state.selected===issue.issue_id));button.append(badge(status(issue)),el('strong',issue.title),el('span',`${kinds[issue.kind]} · ${issue.evidence[0].published_at}`,'meta'));button.onclick=()=>{state.selected=issue.issue_id;showList();showIssue(issue);};$('issues').append(button);}
}
function contextSection(issue){
  const section=el('div');section.append(el('h3','Captured evidence'));
  for(const evidence of issue.evidence){
    const source=el('section',undefined,'source'),link=el('a',evidence.title);link.href=evidence.url;link.target='_blank';link.rel='noopener noreferrer';
    source.append(link,metadata(`Published ${evidence.published_at} · Captured ${time(evidence.captured_at)}`));
    for(const quote of evidence.quotes)source.append(el('blockquote',quote));
    const button=el('button','Read captured source','secondary');button.type='button';
    button.onclick=async()=>{button.disabled=true;try{const response=await fetch(`./api/evidence/${evidence.sha256}`);if(!response.ok||!response.headers.get('content-type')?.startsWith('text/plain'))throw new Error('Captured source could not be loaded.');const text=await response.text();source.append(el('pre',text));button.remove();}catch(error){message(error.message,true);button.disabled=false;}};
    source.append(button,metadata(`Evidence SHA-256: ${evidence.sha256}`));section.append(source);
  }
  const details=el('details'),summary=el('summary','Scientific context and dependency references');details.append(summary,el('pre',JSON.stringify({affected_ids:issue.affected_ids,dependencies:issue.dependencies,...issue.context},null,2)));section.append(details);return section;
}
function field(form,labelText,input){const label=el('label',labelText);label.append(input);form.append(label);return input;}
function showIssue(issue){
  const detail=$('detail');detail.replaceChildren();detail.append(badge(status(issue)),metadata(`${kinds[issue.kind]} · ${issue.issue_id}`),el('h2',issue.title),el('p',issue.question,'question'),el('p',issue.impact,'impact'),metadata(`First seen ${time(issue.first_seen)} · Issue changed ${time(issue.changed_at)}`),contextSection(issue));
  if(issue.last){const note=el('div',undefined,'notice');note.append(el('strong',labels[status(issue)]),el('p',issue.last.receipt?.detail||'The decision is saved. ATLAS has not acknowledged application.'),metadata(`${issue.last.decision.reviewer} · ${time(issue.last.decision.submitted_at)}`));detail.append(note);}
  const history=el('button','View decision history','secondary');history.type='button';history.onclick=()=>showHistory(issue.issue_id);detail.append(history);
  if(['submitted','recorded','applied'].includes(status(issue))){detail.append(metadata('A decision is awaiting application or validation. Its receipt will appear here.'));return;}
  const form=el('form',undefined,'decision-form');form.append(el('h3','Record your decision'));
  const action=el('select');for(const [value,label] of issue.kind==='registry'?[['defer','Defer for further review'],['accept','Accept into an event'],['reject','Reject this candidate']]:[['instruct','Give a scientific review instruction'],['defer','Defer for further review']]){const option=el('option',label);option.value=value;action.append(option);}field(form,'Action',action);
  const rationale=field(form,'Rationale or exact instruction',el('textarea'));rationale.required=true;rationale.minLength=3;rationale.maxLength=800;
  const acceptance=el('div');acceptance.hidden=true;
  const event=field(acceptance,'Stable event key',el('input'));event.maxLength=200;
  const publicNote=field(acceptance,'Public rationale',el('textarea'));publicNote.maxLength=300;publicNote.value='Editorial review';
  const supersedes=field(acceptance,'Candidate IDs explicitly superseded (comma separated)',el('input'));
  const reclass=el('input');reclass.type='checkbox';const reclassLabel=el('label','The evidence supports a disease reclassification.','check');reclassLabel.prepend(reclass);acceptance.append(reclassLabel);
  const numeric={};for(const flag of issue.context.validation_errors||[]){if(flag.startsWith('Numeric evidence needs review:')){const input=field(acceptance,flag,el('textarea'));input.maxLength=500;numeric[flag]=input;}}
  form.append(acceptance);action.onchange=()=>{acceptance.hidden=action.value!=='accept';event.required=action.value==='accept';publicNote.required=action.value==='accept';};
  form.append(el('small','Submission records your instruction. ATLAS reports application and output validation separately.'));
  const submit=el('button','Submit decision');submit.type='submit';form.append(submit);let retry=null;
  form.onsubmit=async e=>{e.preventDefault();submit.disabled=true;message('Saving decision…');
    const input={snapshot_id:state.snapshot.snapshot_id,issue_id:issue.issue_id,revision:issue.revision,previous_decision_id:issue.last?.decision.decision_id||null,action:action.value,rationale:rationale.value.trim()};
    if(action.value==='accept')Object.assign(input,{event_key:event.value.trim(),public_rationale:publicNote.value.trim(),supersedes_candidate_ids:supersedes.value.split(',').map(x=>x.trim()).filter(Boolean),allow_disease_reclassification:reclass.checked,numeric_evidence_reviews:Object.fromEntries(Object.entries(numeric).filter(([,v])=>v.value.trim()).map(([k,v])=>[k,v.value.trim()]))});
    const signature=JSON.stringify(input);if(!retry||retry.signature!==signature)retry={signature,id:crypto.randomUUID()};
    try{await api('decisions',{...input,decision_id:retry.id});message('Decision saved. Application and validation receipts will appear here.');await refresh();}catch(error){message(error.message,true);submit.disabled=false;}
  };detail.append(form);
}
function selectTab(tab){state.tab=tab;for(const name of ['inbox','history']){$(`${name}-view`).hidden=name!==tab;$(`${name}-tab`).classList.toggle('selected',name===tab);$(`${name}-tab`).setAttribute('aria-pressed',String(name===tab));}}
let historyIssue=null;
async function showHistory(issueId=null,append=false){
  selectTab('history');if(!append){$('history').replaceChildren();state.historyCursor=null;historyIssue=issueId;}
  const params=new URLSearchParams();if(historyIssue)params.set('issue',historyIssue);if(append&&state.historyCursor)params.set('before',state.historyCursor);
  try{const result=await api(`history?${params}`);for(const item of result.entries){const card=el('article',undefined,'history-card');card.append(badge(item.receipts.at(-1)?.status||'submitted'),el('h2',item.issue.title),metadata(`${item.decision.reviewer} · ${time(item.decision.submitted_at)} · ${item.decision.action}`),el('p',item.decision.rationale),metadata(`Decision ${item.decision.decision_id} · Revision ${item.decision.revision}`));for(const receipt of item.receipts){const block=el('div',undefined,'receipt');block.append(el('strong',labels[receipt.status]),el('p',receipt.detail),metadata(`${time(receipt.recorded_at)} · Validation: ${receipt.validation}`));if(receipt.export_id)block.append(metadata(`Validated export: ${receipt.export_id}`));card.append(block);}const evidence=el('details');evidence.append(el('summary','Evidence reviewed for this decision'),contextSection(item.issue));card.append(evidence);$('history').append(card);}if(!append&&!result.entries.length)$('history').append(el('p','No decisions have been submitted.','empty'));state.historyCursor=result.next;$('older').hidden=!result.next;}catch(error){message(error.message,true);}
}
async function refresh(){
  $('refresh').disabled=true;
  try{const result=await api('issues');state.issues=result.issues;state.snapshot=result.snapshot;$('packet-info').textContent=result.snapshot?`Prepared by ATLAS · ${time(result.snapshot.generated_at)}`:'Awaiting the first ATLAS review packet.';showList();const issue=state.issues.find(i=>i.issue_id===state.selected);if(issue)showIssue(issue);else if(state.selected){state.selected=null;$('detail').replaceChildren(el('p','This issue is absent from the active packet. Its decisions remain in history.','empty'));}if(state.tab==='history')await showHistory(historyIssue);}catch(error){message(error.message,true);}finally{$('refresh').disabled=false;}
}
$('refresh').onclick=refresh;for(const id of ['search','kind','status'])$(id).addEventListener('input',showList);
$('inbox-tab').onclick=()=>selectTab('inbox');$('history-tab').onclick=()=>showHistory();$('older').onclick=()=>showHistory(historyIssue,true);
try{const me=await api('me');$('identity').textContent=me.email;await refresh();}catch(error){$('identity').textContent='Access unavailable';message(error.message,true);}
