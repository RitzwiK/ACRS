import re
from typing import Dict, Optional, List


class CSSParser:
    IMPORT_PATTERN = re.compile(r'@import\s+(?:url\s*\(\s*)?[\'"]([^\'"]+)[\'"]')
    RULE_PATTERN = re.compile(r'([^{]+)\{([^}]*)\}', re.DOTALL)
    MEDIA_PATTERN = re.compile(r'@media\s+([^{]+)\{')
    KEYFRAME_PATTERN = re.compile(r'@keyframes\s+(\w+)')
    VAR_DEF_PATTERN = re.compile(r'(--[\w-]+)\s*:\s*([^;]+)')
    VAR_USE_PATTERN = re.compile(r'var\(\s*(--[\w-]+)')
    FONT_FACE_PATTERN = re.compile(r'@font-face')
    PROPERTY_PATTERN = re.compile(r'([\w-]+)\s*:\s*([^;]+)')

    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        lines = source_code.split('\n')
        nodes = []
        edges = []
        cfg_edges = []
        dfg_edges = []
        node_id = 0

        root = {
            'id': node_id, 'type': 'Stylesheet', 'token': file_path.split('/')[-1] if '/' in file_path else file_path,
            'context': '', 'line_start': 1, 'line_end': len(lines),
            'col_offset': 0, 'depth': 0, 'in_degree': 0, 'num_children': 0
        }
        nodes.append(root)
        node_id += 1

        for m in self.IMPORT_PATTERN.finditer(source_code):
            pos = source_code[:m.start()].count('\n') + 1
            imp_node = {
                'id': node_id, 'type': 'Import', 'token': m.group(1),
                'context': '', 'line_start': pos, 'line_end': pos,
                'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
            }
            nodes.append(imp_node)
            edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
            root['num_children'] += 1
            node_id += 1

        var_defs = {}
        for m in self.VAR_DEF_PATTERN.finditer(source_code):
            var_name = m.group(1)
            pos = source_code[:m.start()].count('\n') + 1
            var_node = {
                'id': node_id, 'type': 'VarDef', 'token': var_name,
                'context': 'Store', 'line_start': pos, 'line_end': pos,
                'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
            }
            nodes.append(var_node)
            edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
            root['num_children'] += 1
            var_defs[var_name] = node_id
            node_id += 1

        for m in self.VAR_USE_PATTERN.finditer(source_code):
            var_name = m.group(1)
            if var_name in var_defs:
                pos = source_code[:m.start()].count('\n') + 1
                use_node = {
                    'id': node_id, 'type': 'VarUse', 'token': var_name,
                    'context': 'Load', 'line_start': pos, 'line_end': pos,
                    'col_offset': 0, 'depth': 3, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(use_node)
                dfg_edges.append({
                    'source': var_defs[var_name], 'target': node_id,
                    'type': 'DFG', 'variable': var_name
                })
                node_id += 1

        for km in self.KEYFRAME_PATTERN.finditer(source_code):
            pos = source_code[:km.start()].count('\n') + 1
            kf_node = {
                'id': node_id, 'type': 'Keyframes', 'token': km.group(1),
                'context': '', 'line_start': pos, 'line_end': pos,
                'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
            }
            nodes.append(kf_node)
            edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
            root['num_children'] += 1
            node_id += 1

        cleaned = re.sub(r'@media[^{]+\{', '', source_code)
        cleaned = re.sub(r'@keyframes\s+\w+\s*\{[^}]*\}', '', cleaned, flags=re.DOTALL)

        prev_rule_id = None
        for m in self.RULE_PATTERN.finditer(cleaned):
            selector = m.group(1).strip()
            body = m.group(2).strip()

            if not selector or selector.startswith('@') or selector.startswith('//'):
                continue

            pos = source_code.find(selector)
            line = source_code[:pos].count('\n') + 1 if pos >= 0 else 0
            props = self.PROPERTY_PATTERN.findall(body)
            prop_count = len(props)

            rule_type = 'Rule'
            if selector.startswith(':root'):
                rule_type = 'RootRule'
            elif '::' in selector:
                rule_type = 'PseudoElement'
            elif ':' in selector:
                rule_type = 'PseudoClass'
            elif '@' in selector:
                rule_type = 'AtRule'

            specificity = 0
            specificity += selector.count('#') * 100
            specificity += selector.count('.') * 10
            specificity += len(re.findall(r'(?:^|[\s>+~])(\w)', selector))

            rule_node = {
                'id': node_id, 'type': rule_type, 'token': selector[:50],
                'context': f'{prop_count} props', 'line_start': line, 'line_end': line,
                'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': prop_count
            }
            nodes.append(rule_node)
            edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
            root['num_children'] += 1

            if prev_rule_id is not None:
                cfg_edges.append({
                    'source': prev_rule_id, 'target': node_id,
                    'type': 'CFG', 'label': 'cascade_order'
                })
            prev_rule_id = node_id

            rule_id = node_id
            node_id += 1

            for prop_name, prop_val in props[:10]:
                prop_node = {
                    'id': node_id, 'type': 'Property', 'token': prop_name.strip(),
                    'context': prop_val.strip()[:30], 'line_start': line, 'line_end': line,
                    'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(prop_node)
                edges.append({'source': rule_id, 'target': node_id, 'type': 'AST'})
                node_id += 1

        for mm in self.MEDIA_PATTERN.finditer(source_code):
            pos = source_code[:mm.start()].count('\n') + 1
            media_node = {
                'id': node_id, 'type': 'MediaQuery', 'token': mm.group(1).strip()[:40],
                'context': '', 'line_start': pos, 'line_end': pos,
                'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
            }
            nodes.append(media_node)
            edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
            root['num_children'] += 1
            node_id += 1

        return {
            'nodes': nodes,
            'edges': edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': [],
            'language': 'CSS',
            'file_path': file_path,
            'num_lines': len(lines)
        }
