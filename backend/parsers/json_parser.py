import json
from typing import Dict, Optional


class JSONParser:
    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        try:
            data = json.loads(source_code)
        except json.JSONDecodeError:
            return None

        nodes = []
        edges = []
        node_id_counter = [0]

        def get_id():
            nid = node_id_counter[0]
            node_id_counter[0] += 1
            return nid

        def visit(obj, parent_id=None, key=None, depth=0):
            nid = get_id()

            if isinstance(obj, dict):
                token = key or 'object'
                node = {
                    'id': nid, 'type': 'Object', 'token': str(token)[:40],
                    'context': f'{len(obj)} keys', 'line_start': 0, 'line_end': 0,
                    'col_offset': 0, 'depth': depth, 'in_degree': 1 if parent_id is not None else 0,
                    'num_children': len(obj)
                }
                nodes.append(node)
                if parent_id is not None:
                    edges.append({'source': parent_id, 'target': nid, 'type': 'AST'})
                for k, v in obj.items():
                    visit(v, nid, k, depth + 1)

            elif isinstance(obj, list):
                token = key or 'array'
                node = {
                    'id': nid, 'type': 'Array', 'token': str(token)[:40],
                    'context': f'{len(obj)} items', 'line_start': 0, 'line_end': 0,
                    'col_offset': 0, 'depth': depth, 'in_degree': 1 if parent_id is not None else 0,
                    'num_children': len(obj)
                }
                nodes.append(node)
                if parent_id is not None:
                    edges.append({'source': parent_id, 'target': nid, 'type': 'AST'})
                for i, item in enumerate(obj[:50]):
                    visit(item, nid, f'[{i}]', depth + 1)

            else:
                val_type = type(obj).__name__
                token = key or val_type
                val_str = str(obj)[:30] if obj is not None else 'null'
                node = {
                    'id': nid, 'type': 'Value', 'token': str(token)[:40],
                    'context': val_str, 'line_start': 0, 'line_end': 0,
                    'col_offset': 0, 'depth': depth, 'in_degree': 1 if parent_id is not None else 0,
                    'num_children': 0
                }
                nodes.append(node)
                if parent_id is not None:
                    edges.append({'source': parent_id, 'target': nid, 'type': 'AST'})

        visit(data)

        if not nodes:
            return None

        cfg_edges = []
        if isinstance(data, dict):
            top_level = [e['target'] for e in edges if e['source'] == 0]
            for i in range(len(top_level) - 1):
                cfg_edges.append({
                    'source': top_level[i], 'target': top_level[i + 1],
                    'type': 'CFG', 'label': 'sequential'
                })

        dfg_edges = []
        ref_keys = {'$ref', '$id', '$schema', 'extends', 'allOf', 'oneOf', 'anyOf'}
        ref_nodes = {}
        for n in nodes:
            if n['type'] == 'Value' and n.get('token') in ref_keys:
                ref_nodes[n.get('context', '')] = n['id']

        lines = source_code.split('\n')
        line_map = {}
        for i, line in enumerate(lines, 1):
            stripped = line.strip().strip(',').strip('"').strip("'")
            for n in nodes:
                if n.get('line_start', 0) == 0 and n['token'] in stripped:
                    n['line_start'] = i
                    n['line_end'] = i
                    break

        return {
            'nodes': nodes,
            'edges': edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': [],
            'language': 'JSON',
            'file_path': file_path,
            'num_lines': len(lines)
        }
