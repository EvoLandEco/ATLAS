"""Prepare explicitly reviewed chains and verify their evidence dependencies."""
from collections import defaultdict, deque
from .util import uid


def prepare_chains(chains, evrefs, evidence, records, assertion_keys, places):
    def support(refs, dependencies=()):
        ids = evrefs(refs)
        rows = [evidence[e] for e in ids]
        rids = {e['record_id'] for e in rows}
        aids = {assertion_keys['claim:'+e['record_id']+':'+str(e['claim_index'])]
                for e in rows if e['claim_index'] is not None}
        for item in dependencies:
            rids.update(item['record_ids']); aids.update(item['assertion_ids'])
        return dict(evidence_ids=ids, assertion_ids=sorted(aids), record_ids=sorted(rids),
                    document_ids=sorted({records[r]['document_id'] for r in rids}),
                    eligibility=dict(record_ids=sorted(rids)))

    output = []
    for chain in chains:
        nodes = []
        for node in chain.nodes:
            row = node.model_dump(mode='json', exclude={'evidence'})
            row.update(support(node.evidence), id=uid('chain_node', chain.key, node.key))
            row['topic_ids'] = sorted({records[r]['track'] for r in row['record_ids']})
            row['coordinate_precision'] = places[node.place_id]['precision'] if node.place_id else None
            nodes.append(row)
        by_key = {n['key']: n for n in nodes}
        if len(by_key) != len(nodes): raise ValueError('Duplicate chain node key')
        edges = []
        for edge in chain.edges:
            start, end = by_key[edge.from_node], by_key[edge.to_node]
            row = edge.model_dump(mode='json', exclude={'evidence', 'from_node', 'to_node'})
            row.update(support(edge.evidence, (start, end)), id=uid('chain_edge', chain.key, edge.key),
                       from_node_id=start['id'], to_node_id=end['id'])
            edges.append(row)
        output.append(dict(chain.model_dump(mode='json', exclude={'nodes', 'edges'}),
                           id=uid('chain', chain.key), nodes=nodes, edges=edges))
    return output


def validate_chains(chains, ix):
    seen = set()
    place_support = {}
    claim_ids = {(a['record_id'], a['claim_index']): a['id']
                 for a in ix['assertions'].values() if a['kind'] == 'finding'}

    def unique(identity):
        if identity in seen: raise ValueError('Duplicate chain identity')
        seen.add(identity)

    def support(item, dependencies=()):
        for name, field in [('records','record_ids'), ('documents','document_ids'),
                            ('assertions','assertion_ids'), ('evidence','evidence_ids')]:
            values = item[field]
            if len(values) != len(set(values)) or not set(values) <= ix[name].keys():
                raise ValueError('Invalid chain '+name+' reference')
        rows = [ix['evidence'][e] for e in item['evidence_ids']]
        rids = {e['record_id'] for e in rows}
        aids = {claim_ids[e['record_id'], e['claim_index']] for e in rows if e['claim_index'] is not None}
        for dependency in dependencies:
            rids.update(dependency['record_ids']); aids.update(dependency['assertion_ids'])
        if (set(item['record_ids']) != rids or set(item['eligibility']['record_ids']) != rids or
                len(item['eligibility']['record_ids']) != len(rids) or
                set(item['document_ids']) != {ix['records'][r]['document_id'] for r in rids} or
                set(item['assertion_ids']) != aids):
            raise ValueError('Chain support must include exact evidence and endpoint dependencies')

    for chain in chains:
        unique(chain['id'])
        if chain['id'] != uid('chain', chain['key']): raise ValueError('Invalid stable chain ID')
        nodes = {n['id']: n for n in chain['nodes']}
        adjacency, directed = defaultdict(set), defaultdict(list)
        indegree = {n: 0 for n in nodes}
        pairs = set()
        for n in chain['nodes']:
            unique(n['id']); support(n)
            if n['id'] != uid('chain_node', chain['key'], n['key']): raise ValueError('Invalid stable chain node ID')
            topics = {ix['records'][r]['topic_id'] for r in n['record_ids']}
            if set(n['topic_ids']) != topics: raise ValueError('Chain topic membership mismatch')
            if n['event_date']['value'] is not None and n['date_basis'] == 'unknown':
                raise ValueError('Chain event date requires its basis')
            p = ix['places'].get(n['place_id']) if n['place_id'] else None
            if n['place_id'] and not p: raise ValueError('Unknown chain place')
            if n['coordinate_precision'] != (p['precision'] if p else None):
                raise ValueError('Chain coordinate precision must match its reference place')
            if p:
                if p['id'] not in place_support:
                    place_records = set(p['record_ids'])
                    for rid in p['relationship_ids']:
                        place_records.update(ix['relationships'][rid]['eligibility']['record_ids'])
                    for mid in p['location_membership_ids']:
                        place_records.update(ix['location_memberships'][mid]['eligibility']['record_ids'])
                    place_support[p['id']] = place_records
                if not place_support[p['id']].intersection(n['record_ids']):
                    raise ValueError('Chain place lacks record-bound geographic support')
            if chain['kind'] == 'contact_exposure' and n['entity_kind'] not in {'person', 'case', 'case_group', 'contact_group'}:
                raise ValueError('Contact nodes describe people or reported groups')
            if chain['kind'] == 'travel_itinerary' and n['entity_kind'] != 'travel_stop':
                raise ValueError('Itinerary nodes describe the reported travel stops')
            if chain['kind'] == 'established_transmission' and n['entity_kind'] not in {'case', 'case_group'}:
                raise ValueError('Transmission nodes describe cases or case groups')
            if chain['kind'] == 'reporting_sequence' and n['entity_kind'] != 'report':
                raise ValueError('Reporting sequence nodes describe reports')
        for edge in chain['edges']:
            unique(edge['id'])
            if edge['id'] != uid('chain_edge', chain['key'], edge['key']): raise ValueError('Invalid stable chain edge ID')
            a, b = edge['from_node_id'], edge['to_node_id']
            if a == b or a not in nodes or b not in nodes: raise ValueError('Invalid chain endpoints')
            if edge['kind'] != chain['kind']: raise ValueError('Chain edge type differs from chain scope')
            support(edge, (nodes[a], nodes[b]))
            pair = (a, b) if edge['directed'] else tuple(sorted((a, b)))
            if pair in pairs: raise ValueError('Duplicate chain connection')
            pairs.add(pair); adjacency[a].add(b); adjacency[b].add(a)
            if edge['directed']:
                directed[a].append(b); indegree[b] += 1
            if chain['kind'] == 'reporting_sequence':
                before = [ix['records'][r]['publication'] for r in nodes[a]['record_ids']]
                after = [ix['records'][r]['publication'] for r in nodes[b]['record_ids']]
                if max(before)[:10] >= min(after)[:10]:
                    raise ValueError('Reporting sequence needs distinct ordered publication dates')
        reached, queue = set(), [next(iter(nodes))]
        while queue:
            n = queue.pop()
            if n not in reached:
                reached.add(n); queue.extend(adjacency[n] - reached)
        if reached != set(nodes): raise ValueError('Reviewed chain must be connected')
        queue = deque(n for n in nodes if indegree[n] == 0)
        visited = 0
        while queue:
            n = queue.popleft(); visited += 1
            for target in directed[n]:
                indegree[target] -= 1
                if indegree[target] == 0: queue.append(target)
        if visited != len(nodes): raise ValueError('Directed chain cannot contain a cycle')
