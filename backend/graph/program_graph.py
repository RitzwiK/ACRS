import networkx as nx
from typing import Dict, List, Any


class ProgramGraphBuilder:
    def build(self, ast_data: Dict, source_code: str) -> Dict:
        G = nx.DiGraph()

        nodes = ast_data.get('nodes', [])
        ast_edges = ast_data.get('edges', [])
        cfg_edges = ast_data.get('cfg_edges', [])
        dfg_edges = ast_data.get('dfg_edges', [])

        node_type_counts = {}
        for node in nodes:
            G.add_node(node['id'], **node)
            nt = node['type']
            node_type_counts[nt] = node_type_counts.get(nt, 0) + 1

        ast_edge_count = 0
        for edge in ast_edges:
            if G.has_node(edge['source']) and G.has_node(edge['target']):
                G.add_edge(edge['source'], edge['target'], type='AST')
                ast_edge_count += 1

        cfg_edge_count = 0
        for edge in cfg_edges:
            if G.has_node(edge['source']) and G.has_node(edge['target']):
                G.add_edge(
                    edge['source'], edge['target'],
                    type='CFG',
                    label=edge.get('label', 'sequential')
                )
                cfg_edge_count += 1

        dfg_edge_count = 0
        seen_dfg = set()
        for edge in dfg_edges:
            key = (edge['source'], edge['target'])
            if key not in seen_dfg and G.has_node(edge['source']) and G.has_node(edge['target']):
                G.add_edge(
                    edge['source'], edge['target'],
                    type='DFG',
                    variable=edge.get('variable', '')
                )
                dfg_edge_count += 1
                seen_dfg.add(key)

        adjacency = {}
        typed_adjacency = {'AST': {}, 'CFG': {}, 'DFG': {}}

        for u, v, data in G.edges(data=True):
            edge_type = data.get('type', 'AST')
            adjacency.setdefault(v, []).append((u, edge_type))
            typed_adjacency[edge_type].setdefault(v, []).append(u)

        node_features_raw = []
        node_ids = []
        for node in nodes:
            if G.has_node(node['id']):
                node_ids.append(node['id'])
                node_features_raw.append({
                    'type': node['type'],
                    'token': node.get('token', ''),
                    'depth': node.get('depth', 0),
                    'in_degree': G.in_degree(node['id']),
                    'out_degree': G.out_degree(node['id']),
                    'line_start': node.get('line_start', 0),
                    'line_end': node.get('line_end', 0),
                    'context': node.get('context', ''),
                    'num_children': node.get('num_children', 0),
                })

        return {
            'graph': G,
            'num_nodes': G.number_of_nodes(),
            'num_edges': G.number_of_edges(),
            'ast_edge_count': ast_edge_count,
            'cfg_edge_count': cfg_edge_count,
            'dfg_edge_count': dfg_edge_count,
            'node_ids': node_ids,
            'node_features_raw': node_features_raw,
            'adjacency': adjacency,
            'typed_adjacency': typed_adjacency,
            'node_type_counts': node_type_counts,
            'functions': ast_data.get('functions', []),
            'source_lines': source_code.split('\n'),
            'language': ast_data.get('language', 'Unknown'),
        }
