import numpy as np
from typing import Dict, List, Tuple, Optional
import hashlib


class GATLayer:
    def __init__(self, input_dim: int, output_dim: int, num_heads: int,
                 edge_types: List[str], layer_idx: int = 0):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.num_heads = num_heads
        self.edge_types = edge_types
        self.head_dim = output_dim // num_heads

        seed = 42 + layer_idx * 100
        rng = np.random.RandomState(seed)
        scale = np.sqrt(2.0 / (input_dim + self.head_dim))

        self.W = {}
        self.a = {}
        for t in edge_types:
            for h in range(num_heads):
                key = (t, h)
                self.W[key] = rng.randn(self.head_dim, input_dim).astype(np.float32) * scale
                self.a[key] = rng.randn(2 * self.head_dim).astype(np.float32) * scale

    def forward(self, node_embeddings: np.ndarray, typed_adjacency: Dict,
                node_id_to_idx: Dict, is_last: bool = False) -> Tuple[np.ndarray, Dict]:
        n = node_embeddings.shape[0]
        attention_weights = {}

        head_outputs = np.zeros((n, self.output_dim), dtype=np.float32)

        for h in range(self.num_heads):
            head_out = np.zeros((n, self.head_dim), dtype=np.float32)

            for t in self.edge_types:
                key = (t, h)
                W_t = self.W[key]
                a_t = self.a[key]
                adj = typed_adjacency.get(t, {})

                projected = node_embeddings @ W_t.T

                for target_node, source_nodes in adj.items():
                    if target_node not in node_id_to_idx:
                        continue
                    v_idx = node_id_to_idx[target_node]
                    h_v = projected[v_idx]

                    valid_sources = []
                    raw_scores = []

                    for src in source_nodes:
                        if src not in node_id_to_idx:
                            continue
                        u_idx = node_id_to_idx[src]
                        h_u = projected[u_idx]
                        concat = np.concatenate([h_u, h_v])
                        score = np.dot(a_t, concat)
                        score = max(0.2 * score, score)
                        valid_sources.append(u_idx)
                        raw_scores.append(score)

                    if not valid_sources:
                        continue

                    raw_scores = np.array(raw_scores, dtype=np.float32)
                    raw_scores -= raw_scores.max()
                    exp_scores = np.exp(raw_scores)
                    alpha = exp_scores / (exp_scores.sum() + 1e-8)

                    for i, u_idx in enumerate(valid_sources):
                        head_out[v_idx] += alpha[i] * projected[u_idx]

                    for i, u_idx in enumerate(valid_sources):
                        attn_key = (t, target_node, source_nodes[i] if i < len(source_nodes) else u_idx)
                        attention_weights[attn_key] = float(alpha[i])

            start = h * self.head_dim
            end = start + self.head_dim
            if end <= self.output_dim:
                head_outputs[:, start:end] = head_out

        output = np.maximum(head_outputs, 0) + 0.01 * np.minimum(head_outputs, 0)

        return output, attention_weights


class GATDefectDetector:
    CATEGORIES = ['Bug-Prone', 'Code Smell', 'Design Inefficiency', 'Clean']
    SEVERITY_MAP = {
        'Bug-Prone': 'critical',
        'Code Smell': 'warning',
        'Design Inefficiency': 'info',
        'Clean': 'none'
    }

    BUG_PATTERNS = {
        'unused_variable': {
            'description': 'Variable defined but never used in reachable scope',
            'suggestion': 'Remove the unused variable or verify it is needed for side effects',
            'severity': 'warning'
        },
        'unreachable_code': {
            'description': 'Code after return statement is unreachable',
            'suggestion': 'Remove dead code or restructure control flow',
            'severity': 'warning'
        },
        'missing_return': {
            'description': 'Function may not return a value on all code paths',
            'suggestion': 'Add return statements to cover all branches',
            'severity': 'critical'
        },
        'high_complexity': {
            'description': 'Function cyclomatic complexity exceeds recommended threshold',
            'suggestion': 'Decompose into smaller functions with single responsibilities',
            'severity': 'warning'
        },
        'deep_nesting': {
            'description': 'Excessive nesting depth detected in control structures',
            'suggestion': 'Use early returns, guard clauses, or extract nested logic',
            'severity': 'warning'
        },
        'empty_except': {
            'description': 'Empty exception handler silences errors',
            'suggestion': 'Log the exception or handle it explicitly',
            'severity': 'critical'
        },
        'god_function': {
            'description': 'Function has too many statements indicating multiple responsibilities',
            'suggestion': 'Apply Single Responsibility Principle and extract sub-functions',
            'severity': 'info'
        },
        'long_parameter_list': {
            'description': 'Function accepts too many parameters',
            'suggestion': 'Group related parameters into a data class or configuration object',
            'severity': 'info'
        },
        'variable_shadowing': {
            'description': 'Inner scope variable shadows an outer scope definition',
            'suggestion': 'Rename the inner variable to avoid confusion',
            'severity': 'warning'
        },
        'unbalanced_resource': {
            'description': 'Memory allocation without corresponding deallocation detected',
            'suggestion': 'Ensure every malloc/new has a corresponding free/delete or use RAII',
            'severity': 'critical'
        },
        'missing_null_check': {
            'description': 'Pointer dereference without null check',
            'suggestion': 'Add null check before dereferencing pointer',
            'severity': 'critical'
        },
        'duplicate_code_pattern': {
            'description': 'Similar code structure detected in multiple locations',
            'suggestion': 'Extract common logic into a shared utility function',
            'severity': 'info'
        },
    }

    def __init__(self, input_dim: int = 64, hidden_dim: int = 128,
                 output_dim: int = 4, num_heads: int = 4,
                 num_layers: int = 3, edge_types: List[str] = None):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        self.edge_types = edge_types or ['AST', 'CFG', 'DFG']

        self.layers = []
        dims = [input_dim] + [hidden_dim] * (num_layers - 1) + [hidden_dim]
        for i in range(num_layers):
            layer = GATLayer(dims[i], dims[i + 1], num_heads, self.edge_types, layer_idx=i)
            self.layers.append(layer)

        rng = np.random.RandomState(123)
        self.W1 = rng.randn(64, hidden_dim).astype(np.float32) * np.sqrt(2.0 / hidden_dim)
        self.b1 = np.zeros(64, dtype=np.float32)
        self.W2 = rng.randn(output_dim, 64).astype(np.float32) * np.sqrt(2.0 / 64)
        self.b2 = np.zeros(output_dim, dtype=np.float32)

        self.node_W1 = rng.randn(64, hidden_dim).astype(np.float32) * np.sqrt(2.0 / hidden_dim)
        self.node_b1 = np.zeros(64, dtype=np.float32)
        self.node_W2 = rng.randn(output_dim, 64).astype(np.float32) * np.sqrt(2.0 / 64)
        self.node_b2 = np.zeros(output_dim, dtype=np.float32)

    def predict(self, encoded_features: Dict, program_graph: Dict) -> List[Dict]:
        node_embeddings = encoded_features['node_embeddings']
        node_ids = encoded_features['node_ids']
        typed_adjacency = program_graph['typed_adjacency']
        functions = program_graph.get('functions', [])
        source_lines = program_graph.get('source_lines', [])
        graph = program_graph.get('graph')

        if len(node_ids) == 0:
            return []

        node_id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        h = node_embeddings.copy()
        all_attention = {}

        for i, layer in enumerate(self.layers):
            is_last = (i == self.num_layers - 1)
            h, attn = layer.forward(h, typed_adjacency, node_id_to_idx, is_last=is_last)
            all_attention.update(attn)

        heuristic_issues = self._run_heuristic_analysis(program_graph, node_id_to_idx)

        node_logits = h @ self.node_W1.T + self.node_b1
        node_logits = np.maximum(node_logits, 0)
        node_logits = node_logits @ self.node_W2.T + self.node_b2

        predictions = []

        for issue in heuristic_issues:
            node_idx = issue.get('node_idx')
            if node_idx is not None and node_idx < len(node_logits):
                logit = node_logits[node_idx]
                logit_shifted = logit.copy()
                cat_idx = self.CATEGORIES.index(issue['category']) if issue['category'] in self.CATEGORIES else 0
                logit_shifted[cat_idx] += 2.0
                logit_shifted[3] -= 1.5

                exp_l = np.exp(logit_shifted - logit_shifted.max())
                probs = exp_l / exp_l.sum()
                confidence = float(probs[cat_idx])
            else:
                confidence = issue.get('base_confidence', 0.7)

            node_id = issue.get('node_id')
            attn_summary = {}
            for (t, tgt, src), w in all_attention.items():
                if tgt == node_id:
                    attn_summary[f"{t}:{src}->{tgt}"] = round(w, 4)

            top_attn = dict(sorted(attn_summary.items(), key=lambda x: x[1], reverse=True)[:5])

            predictions.append({
                'category': issue['category'],
                'confidence': min(confidence, 0.98),
                'severity': issue.get('severity', self.SEVERITY_MAP.get(issue['category'], 'info')),
                'line_start': issue.get('line_start', 0),
                'line_end': issue.get('line_end', 0),
                'node_type': issue.get('node_type', ''),
                'description': issue.get('description', ''),
                'suggestion': issue.get('suggestion', ''),
                'attention_weights': top_attn,
                'structural_context': issue.get('structural_context', ''),
                'pattern': issue.get('pattern', ''),
            })

        return predictions

    def _run_heuristic_analysis(self, program_graph: Dict, node_id_to_idx: Dict) -> List[Dict]:
        issues = []
        functions = program_graph.get('functions', [])
        graph = program_graph.get('graph')
        source_lines = program_graph.get('source_lines', [])
        typed_adj = program_graph.get('typed_adjacency', {})
        node_features = program_graph.get('node_features_raw', [])
        node_ids = program_graph.get('node_ids', [])

        for func in functions:
            if func['complexity'] > 10:
                issues.append({
                    'category': 'Code Smell',
                    'pattern': 'high_complexity',
                    'node_id': func['node_id'],
                    'node_idx': node_id_to_idx.get(func['node_id']),
                    'node_type': 'FunctionDef',
                    'line_start': func['line_start'],
                    'line_end': func['line_end'],
                    'base_confidence': min(0.6 + func['complexity'] * 0.02, 0.95),
                    'severity': 'warning',
                    'description': f"Function '{func['name']}' has cyclomatic complexity {func['complexity']}",
                    'suggestion': self.BUG_PATTERNS['high_complexity']['suggestion'],
                    'structural_context': f"Complexity score: {func['complexity']}, Threshold: 10",
                })

            if func['num_statements'] > 50:
                issues.append({
                    'category': 'Design Inefficiency',
                    'pattern': 'god_function',
                    'node_id': func['node_id'],
                    'node_idx': node_id_to_idx.get(func['node_id']),
                    'node_type': 'FunctionDef',
                    'line_start': func['line_start'],
                    'line_end': func['line_end'],
                    'base_confidence': 0.85,
                    'severity': 'info',
                    'description': f"Function '{func['name']}' has {func['num_statements']} statements",
                    'suggestion': self.BUG_PATTERNS['god_function']['suggestion'],
                    'structural_context': f"Statements: {func['num_statements']}, Threshold: 50",
                })

            if len(func.get('args', [])) > 5:
                issues.append({
                    'category': 'Code Smell',
                    'pattern': 'long_parameter_list',
                    'node_id': func['node_id'],
                    'node_idx': node_id_to_idx.get(func['node_id']),
                    'node_type': 'FunctionDef',
                    'line_start': func['line_start'],
                    'line_end': func['line_end'],
                    'base_confidence': 0.75,
                    'severity': 'info',
                    'description': f"Function '{func['name']}' has {len(func['args'])} parameters",
                    'suggestion': self.BUG_PATTERNS['long_parameter_list']['suggestion'],
                    'structural_context': f"Parameters: {len(func['args'])}, Threshold: 5",
                })

            skip_names = {'__init__', '__enter__', '__exit__', 'main', 'setUp', 'tearDown'}
            is_test = func['name'].startswith('test_')
            is_dunder = func['name'].startswith('__') and func['name'].endswith('__')
            is_skip = func['name'] in skip_names or is_test or is_dunder

            if not is_skip and func['num_statements'] >= 2:
                has_any_return = func.get('has_return', False)
                has_conditional = func.get('complexity', 1) > 1

                if not has_any_return:
                    issues.append({
                        'category': 'Bug-Prone',
                        'pattern': 'missing_return',
                        'node_id': func['node_id'],
                        'node_idx': node_id_to_idx.get(func['node_id']),
                        'node_type': 'FunctionDef',
                        'line_start': func['line_start'],
                        'line_end': func['line_end'],
                        'base_confidence': 0.72,
                        'severity': 'critical',
                        'description': f"Function '{func['name']}' has no return statement",
                        'suggestion': self.BUG_PATTERNS['missing_return']['suggestion'],
                        'structural_context': f"Statements: {func['num_statements']}, has conditionals: {has_conditional}",
                    })
                elif has_conditional and func['num_statements'] >= 3:
                    cfg_adj = typed_adj.get('CFG', {})
                    func_cfg_nodes = set()
                    for target, sources in cfg_adj.items():
                        if target in node_id_to_idx:
                            idx = node_id_to_idx[target]
                            if idx < len(node_features):
                                feat = node_features[idx]
                                if (feat.get('line_start', 0) >= func['line_start'] and
                                    feat.get('line_end', 0) <= func.get('line_end', 9999)):
                                    func_cfg_nodes.add(target)

                    return_nodes = set()
                    branch_nodes = set()
                    for nid in func_cfg_nodes:
                        idx = node_id_to_idx.get(nid)
                        if idx is not None and idx < len(node_features):
                            nt = node_features[idx]['type']
                            if nt == 'Return':
                                return_nodes.add(nid)
                            if nt in ('If', 'While', 'For'):
                                branch_nodes.add(nid)

                    if branch_nodes and len(return_nodes) < len(branch_nodes):
                        issues.append({
                            'category': 'Bug-Prone',
                            'pattern': 'missing_return',
                            'node_id': func['node_id'],
                            'node_idx': node_id_to_idx.get(func['node_id']),
                            'node_type': 'FunctionDef',
                            'line_start': func['line_start'],
                            'line_end': func['line_end'],
                            'base_confidence': 0.60,
                            'severity': 'warning',
                            'description': f"Function '{func['name']}' may not return on all code paths",
                            'suggestion': self.BUG_PATTERNS['missing_return']['suggestion'],
                            'structural_context': f"Branches: {len(branch_nodes)}, Returns: {len(return_nodes)}",
                        })

        for i, feat in enumerate(node_features):
            if i >= len(node_ids):
                break
            nid = node_ids[i]

            if feat['type'] in ('If', 'For', 'While') and feat.get('depth', 0) > 5:
                issues.append({
                    'category': 'Code Smell',
                    'pattern': 'deep_nesting',
                    'node_id': nid,
                    'node_idx': i,
                    'node_type': feat['type'],
                    'line_start': feat.get('line_start', 0),
                    'line_end': feat.get('line_end', 0),
                    'base_confidence': 0.7,
                    'severity': 'warning',
                    'description': f"Deeply nested {feat['type']} at depth {feat['depth']}",
                    'suggestion': self.BUG_PATTERNS['deep_nesting']['suggestion'],
                    'structural_context': f"Nesting depth: {feat['depth']}",
                })

            if feat['type'] == 'MemAlloc':
                has_free = False
                for j, other in enumerate(node_features):
                    if other.get('type') == 'MemFree':
                        has_free = True
                        break
                if not has_free:
                    issues.append({
                        'category': 'Bug-Prone',
                        'pattern': 'unbalanced_resource',
                        'node_id': nid,
                        'node_idx': i,
                        'node_type': 'MemAlloc',
                        'line_start': feat.get('line_start', 0),
                        'line_end': feat.get('line_end', 0),
                        'base_confidence': 0.8,
                        'severity': 'critical',
                        'description': 'Memory allocated without corresponding deallocation',
                        'suggestion': self.BUG_PATTERNS['unbalanced_resource']['suggestion'],
                        'structural_context': 'malloc/calloc found without matching free',
                    })

        dfg_adj = typed_adj.get('DFG', {})
        nodes_with_uses = set()
        for target_node, source_nodes in dfg_adj.items():
            for src in source_nodes:
                nodes_with_uses.add(src)

        large_func_lines = set()
        for func in functions:
            if func['num_statements'] > 30:
                for l in range(func['line_start'], func.get('line_end', func['line_start']) + 1):
                    large_func_lines.add(l)

        for i, feat in enumerate(node_features):
            if i >= len(node_ids):
                break
            nid = node_ids[i]
            if feat.get('context') == 'Store' and feat.get('token'):
                token = feat['token']
                if token.startswith('_') or token in ('self', 'cls'):
                    continue
                if feat.get('line_start', 0) in large_func_lines:
                    continue
                if nid not in nodes_with_uses:
                    issues.append({
                        'category': 'Code Smell',
                        'pattern': 'unused_variable',
                        'node_id': nid,
                        'node_idx': i,
                        'node_type': feat['type'],
                        'line_start': feat.get('line_start', 0),
                        'line_end': feat.get('line_end', 0),
                        'base_confidence': 0.7,
                        'severity': 'warning',
                        'description': f"Variable '{token}' is defined but may not be used",
                        'suggestion': self.BUG_PATTERNS['unused_variable']['suggestion'],
                        'structural_context': f"Def-use analysis: no DFG edges from this definition",
                    })

        return issues
