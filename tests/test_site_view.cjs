const assert = require('node:assert/strict');
(async () => {
  const { selectView } = await import('../src/atlas/assets/site_view.js');
  const old = {id:'old',document_id:'d1',publication:'2026-07-01',capture:'2026-09-25T12:00:00Z'};
  const newer = {id:'new',document_id:'d2',publication:'2026-08-01',capture:'2026-09-26T12:00:00Z'};
  const data = {contract_version:'1.0.0', records:[old,newer],
    assertions:[{id:'a',measure_id:'m1',eligibility:{record_ids:['old']}},{id:'b',measure_id:'m2',eligibility:{record_ids:['new']}}],
    comparisons:[{id:'c',eligibility:{record_ids:['old','new']},lineage:[{from_assertion_id:'a',to_assertion_id:'b'}]}],
    metrics:{measures:[{measure_id:'m1',context_id:'series',observation_date:'2026-06-30',priority:1,value:0},{measure_id:'m2',context_id:'series',observation_date:'2026-06-30',priority:1,value:1}],
      panels:[{kind:'topic',id:'topic',measure_ids:['m1','m2']}]},
    relationships:[],places:[],location_memberships:[],source_coverage:[{id:'coverage',record_ids:['old','new']}]};
  let view=selectView(data,'2026-07-01','2026-07-31');
  assert.deepEqual(view.comparison_ids,[]);assert.deepEqual(view.superseded_assertion_ids,[]);
  assert.deepEqual(view.panels[0].card_groups[0].measure_ids,['m1']);
  view=selectView(data,'2026-07-01','2026-08-01');
  assert.deepEqual(view.comparison_ids,['c']);assert.deepEqual(view.superseded_assertion_ids,['a']);
  assert.deepEqual(view.panels[0].card_groups[0].measure_ids,['m2']);
  assert.deepEqual(selectView(data,'2026-07-01','2026-08-01','publication','2026-09-25T23:59:59Z').comparison_ids,[]);
  assert.deepEqual(selectView(data,'2026-09-26','2026-09-26','capture').record_ids,['new']);
  assert.deepEqual(selectView(data,'2026-07-01','2026-08-01','publication',null,['old']).panels[0].card_groups[0].measure_ids,['m1']);
  assert.throws(()=>selectView(data,'2026-02-30','2026-09-26'));
  assert.throws(()=>selectView(data,'2026-07-01','2026-09-26','publication','2026-09-25T23:59:59'));
  data.comparisons[0].lineage=[];
  assert.deepEqual(selectView(data,'2026-07-01','2026-08-01').panels[0].card_groups[0].measure_ids,['m1','m2']);
  data.metrics.measures[0].observation_date=null;data.metrics.measures[1].observation_date=null;
  assert.equal(selectView(data,'2026-07-01','2026-08-01').panels[0].card_groups[0].observation_date,null);
  const tv = value => ({value,status:value === null ? 'not_reported' : 'reported'});
  const figure = {label:'Confirmed cases',metric:'cases',value:7890,value_status:'reported',unit:'people',
    count_kind:'cumulative',case_class:'confirmed',date_basis:'report',period_start:tv(null),period_end:tv(null),
    case_definition:tv(null),population:tv('Country outbreak'),stratum:tv(null),denominator:null,
    denominator_status:'not_reported',qualifier:'exact',origin_authority:tv(null),disease:tv('Example disease'),
    pathogen:tv(null),host:tv('Humans'),geography:tv('Country A'),acquisition:'unknown',transmission_role:'unknown',
    as_of:tv('2026-06-30'),period_label:'Through 30 June',denominator_population:tv(null),ratio_basis:'not_applicable',
    cumulative_baseline:tv('Current outbreak'),track_id:'topic',review_status:'source_checked_draft',
    observation_date:'2026-06-30',observation_date_status:'reported',source_date_warning:false,priority:1,conflict_set:null};
  const compact = structuredClone(data);compact.comparisons=[];
  compact.metrics.measures=[{...figure,measure_id:'m1',context_id:'a',source_id:'ECDC'},
    {...structuredClone(figure),measure_id:'m2',context_id:'b',source_id:'WHO'},
    {...structuredClone(figure),measure_id:'m3',context_id:'c',source_id:'WHO',label:'Deaths',metric:'deaths',value:3799},
    {...structuredClone(figure),measure_id:'m4',context_id:'d',source_id:'WHO',label:'Hospitalizations',metric:'hospitalizations',value:893}];
  compact.assertions.push({id:'deaths',measure_id:'m3',eligibility:{record_ids:['new']}},
    {id:'hospitalizations',measure_id:'m4',eligibility:{record_ids:['new']}});
  compact.metrics.panels[0].measure_ids=['m1','m2','m3','m4'];
  const selected = (d=compact) => selectView(d,'2026-07-01','2026-08-01');
  const groups = d => selected(d).panels[0].compact_groups;
  let cards=groups();
  assert.deepEqual(cards.map(g=>g.value),[7890,3799,893]);
  assert.deepEqual(cards[0].measure_ids,['m1','m2']);
  assert.deepEqual(cards[0].source_ids,['ECDC','WHO']);
  assert.deepEqual(cards[0].context_ids,['a','b']);
  assert.equal(cards[0].comparability_status,'not_established');
  assert.equal(selected().compact_grouping_version,'1.0.0');
  assert.deepEqual(selected().panels[0].card_groups.map(g=>g.measure_ids),[['m1'],['m2'],['m3']]);
  assert.deepEqual(selectView(compact,'2026-07-01','2026-07-31').panels[0].compact_groups[0].measure_ids,['m1']);
  assert.deepEqual(selectView(compact,'2026-07-01','2026-08-01','publication',null,['new']).panels[0].compact_groups[0].source_ids,['WHO']);
  assert.deepEqual(selectView(compact,'2026-07-01','2026-08-01','publication','2026-09-25T23:59:59Z').panels[0].compact_groups[0].measure_ids,['m1']);
  const differences={value:7891,disease:tv('Other disease'),population:tv('Other population'),case_definition:tv('Other definition'),
    geography:tv('Country B'),observation_date:'2026-06-29',period_start:tv('2026-06-01'),denominator:100,
    denominator_status:'reported',qualifier:'approximately',unit:'animals',count_kind:'interval',case_class:'suspected',
    origin_authority:tv('Other authority'),track_id:'other',stratum:tv('Children'),pathogen:tv('Other pathogen'),
    host:tv('Animals'),acquisition:'imported',transmission_role:'secondary',date_basis:'onset',ratio_basis:'source_reported',
    cumulative_baseline:tv('Other baseline'),denominator_population:tv('Residents'),period_label:'Other period'};
  for (const [field,value] of Object.entries(differences)) {
    const changed=structuredClone(compact);changed.metrics.measures[1][field]=value;
    assert(!groups(changed).some(g=>g.measure_ids.includes('m1') && g.measure_ids.includes('m2')),field);
  }
  for (const kind of ['contradiction','different_scope','unresolved_association']) {
    const changed=structuredClone(compact);
    changed.comparisons=[{id:'separate',kind,participant_ids:['a','b'],eligibility:{record_ids:['old','new']},lineage:[]}];
    assert(!groups(changed).some(g=>g.measure_ids.length>1),kind);
  }
  for (const change of [{value:null,value_status:'unknown'},{observation_date:null,observation_date_status:'not_reported'},
    {conflict_set:'disputed'}]) {
    const changed=structuredClone(compact);changed.metrics.measures.slice(0,2).forEach(m=>Object.assign(m,change));
    assert(!groups(changed).some(g=>g.measure_ids.length>1));
  }
  const zero=structuredClone(compact);zero.metrics.measures.slice(0,2).forEach(m=>m.value=0);
  assert.equal(groups(zero)[0].value,0);assert.equal(groups(zero)[0].measure_ids.length,2);
  const corrected=structuredClone(compact);corrected.comparisons=[{id:'corrected',kind:'correction',participant_ids:['a','b'],
    eligibility:{record_ids:['old','new']},lineage:[{from_assertion_id:'a',to_assertion_id:'b'}]}];
  assert.deepEqual(groups(corrected)[0].measure_ids,['m2']);
  const unchanged=JSON.stringify(compact);selected();assert.equal(JSON.stringify(compact),unchanged);
  const ratio=structuredClone(compact);
  ratio.metrics.measures.push({...structuredClone(figure),measure_id:'ratio',context_id:'aa',source_id:'WHO',
    label:'Source-reported ratio',metric:'other',unit:'percent',value:48.1,ratio_basis:'source_reported'});
  ratio.assertions.push({id:'ratio-a',measure_id:'ratio',eligibility:{record_ids:['new']}});
  ratio.metrics.panels[0].measure_ids.push('ratio');
  assert.deepEqual(groups(ratio).map(g=>g.metric),['cases','deaths','hospitalizations']);
  assert.equal(selected(ratio).panels[0].compact_group_count,4);
  const geography=structuredClone(compact);
  geography.location_memberships=[{id:'older-place',record_id:'old',eligibility:{record_ids:['old']}},{id:'later-place',record_id:'new',eligibility:{record_ids:['new']}}];
  geography.places=[{id:'older',record_ids:['old','new'],relationship_ids:[],location_membership_ids:['older-place']},
    {id:'later',record_ids:['old','new'],relationship_ids:[],location_membership_ids:['later-place']}];
  assert.deepEqual(selectView(geography,'2026-07-01','2026-08-02','publication',null,['old']).place_ids,['older']);
  const longitudinal=structuredClone(compact);longitudinal.contract_version='1.1.0';
  longitudinal.metrics.reviewed_series=[{series_id:'reviewed',members:[
    {measure_id:'m1',evidence_ids:['method'],eligibility:{record_ids:['old']}},
    {measure_id:'m2',evidence_ids:['method'],eligibility:{record_ids:['new']}}],
    connections:[{id:'approved-pair',from_measure_id:'m1',to_measure_id:'m2',evidence_ids:['method'],eligibility:{record_ids:['old','new']}}],
    evidence:[{id:'method'}]}];
  const full=selectView(longitudinal,'2026-07-01','2026-08-01');
  assert.equal(full.reviewed_series[0].connections.length,1);
  assert.equal(full.numeric_coverage.reviewed_connection_count,1);
  for (const v of [selectView(longitudinal,'2026-07-01','2026-07-31'),
    selectView(longitudinal,'2026-07-01','2026-08-01','publication',null,['new']),
    selectView(longitudinal,'2026-07-01','2026-08-01','publication','2026-09-25T23:59:59Z')]) {
    assert.equal(v.reviewed_series[0].connections.length,0);
  }
  longitudinal.comparisons=[{id:'disputed',kind:'contradiction',participant_ids:['a','b'],eligibility:{record_ids:['old','new']},lineage:[]}];
  assert.equal(selectView(longitudinal,'2026-07-01','2026-08-01').reviewed_series[0].connections.length,0);
  longitudinal.comparisons=[{id:'other-scope',kind:'different_scope',participant_ids:['a','deaths'],eligibility:{record_ids:['old','new']},lineage:[]}];
  assert.equal(selectView(longitudinal,'2026-07-01','2026-08-01').reviewed_series[0].connections.length,1);
  longitudinal.comparisons[0].participant_ids=['a','b'];
  assert.equal(selectView(longitudinal,'2026-07-01','2026-08-01').reviewed_series[0].connections.length,0);
  longitudinal.comparisons=[];
  longitudinal.metrics.reviewed_series[0].members[1].eligibility.record_ids=['old','new'];
  assert.deepEqual(selectView(longitudinal,'2026-08-01','2026-08-01').reviewed_series,[]);
  const membershipOrder=structuredClone(compact);
  membershipOrder.source_coverage=[{id:'reversed',record_ids:['new','old']}];
  assert.deepEqual(selectView(membershipOrder,'2026-07-01','2026-08-01').source_coverage,
    [{id:'reversed',record_ids:['new','old'],document_ids:['d1','d2']}]);
  assert.throws(()=>selectView(membershipOrder,'2026-07-01','2026-08-01','publication',null,['missing']),/Unknown selected record/);
  assert.deepEqual(selectView(membershipOrder,'2026-07-01','2026-08-01','publication',null,[]).source_coverage,[]);
  const chains=structuredClone(data);chains.contract_version='1.2.0';chains.comparisons=[];
  chains.records.push({id:'middle',document_id:'dm',publication:'2026-07-15',capture:'2026-09-26T12:00:00Z'});
  const cn=(id,rid,place_id)=>({id,place_id,eligibility:{record_ids:[rid]}});
  const ce=(id,a,b,record_ids)=>({id,from_node_id:a,to_node_id:b,eligibility:{record_ids}});
  chains.reviewed_chains=[{id:'episode',nodes:[cn('a','old','p1'),cn('b','middle',null),cn('c','new','p2'),cn('branch','old','p3')],
    edges:[ce('ab','a','b',['old','middle']),ce('bc','b','c',['middle','new']),ce('branch','a','branch',['old'])]}];
  const all=selectView(chains,'2026-07-01','2026-08-01').reviewed_chains[0];
  assert.equal(all.selection_complete,true);assert.equal(all.edges.length,3);
  assert.deepEqual(all.drawable_edge_ids,['branch']);
  for(const v of [selectView(chains,'2026-07-01','2026-08-01','publication',null,['old','new']),
    selectView(chains,'2026-07-01','2026-07-01'),
    selectView(chains,'2026-07-01','2026-08-01','publication','2026-09-25T23:59:59Z')]) {
    assert.deepEqual(v.reviewed_chains[0].edges.map(e=>e.id),['branch']);
    assert.equal(v.reviewed_chains[0].selection_complete,false);
  }
  const late=selectView(chains,'2026-09-26','2026-09-26','capture').reviewed_chains[0];
  assert.deepEqual(late.edges.map(e=>e.id),['bc']);assert.deepEqual(late.drawable_edge_ids,[]);
  chains.reviewed_chains[0].edges[2].eligibility.record_ids.push('new');
  assert.deepEqual(selectView(chains,'2026-07-01','2026-07-01').reviewed_chains[0].edges,[]);
  assert.deepEqual(selectView(chains,'2026-01-01','2026-01-02').reviewed_chains,[]);
  const mix=structuredClone(data);mix.contract_version='1.3.0';
  mix.records=Array.from({length:6},(_,i)=>({id:'r'+i,document_id:'d'+i,publication:'2026-07-0'+(i+1),capture:'2026-09-25T12:00:00Z'}));
  mix.assertions=[];mix.comparisons=[];mix.metrics={measures:[],panels:[]};mix.source_coverage=[];
  mix.diseases=[{id:'disease:a',label:'Disease A'},{id:'disease:b',label:'Disease B'}];
  mix.disease_reviews=[
    {record_id:'r0',kind:'single_disease',disease_ids:['disease:a'],eligibility:{record_ids:['r0','r5']}},
    {record_id:'r1',kind:'multiple_diseases',disease_ids:['disease:a','disease:b'],eligibility:{record_ids:['r1']}},
    {record_id:'r2',kind:'not_disease_specific',disease_ids:[],eligibility:{record_ids:['r2']}},
    {record_id:'r3',kind:'unresolved',disease_ids:[],eligibility:{record_ids:['r3']}},
    {record_id:'r5',kind:'single_disease',disease_ids:['disease:b'],eligibility:{record_ids:['r5']}},
  ];
  const composition=(...args)=>selectView(mix,...args).disease_composition;
  const allMix=composition('2026-07-01','2026-07-06');
  assert.equal(allMix.denominator,6);assert.equal(allMix.reviewed_record_count,5);
  assert.equal(allMix.categories.reduce((n,c)=>n+c.count,0),6);
  assert.equal(new Set(allMix.categories.flatMap(c=>c.record_ids)).size,6);
  assert.equal(allMix.unclassified_record_count,2);
  assert.equal(allMix.overlapping_diseases.partition,false);
  assert.equal(allMix.overlapping_diseases.categories.reduce((n,c)=>n+c.count,0),4);
  assert.deepEqual(composition('2026-07-01','2026-07-01').unknown_reasons.support_outside_selection,['r0']);
  assert.equal(composition('2026-07-01','2026-07-06','publication',null,['r1']).categories[0].id,'multiple_diseases');
  assert.equal(composition('2026-07-01','2026-07-06','publication','2026-09-24T00:00:00Z').denominator,0);
  assert.equal(composition('2026-07-01','2026-07-06','publication','2026-09-24T00:00:00Z').chart,'empty');
  assert.equal(composition('2026-09-25','2026-09-25','capture').denominator,6);
  const legacy=structuredClone(mix);legacy.contract_version='1.2.0';delete legacy.disease_reviews;delete legacy.diseases;
  assert.equal(selectView(legacy,'2026-07-01','2026-07-06').disease_composition.unclassified_record_count,6);
  console.log('ATLAS view rules pass: inclusive windows, capture cutoff, revision visibility, conflicts, zero, missing dates and geographic evidence.');
})();
