import re
from typing import Dict, Optional, List


class JavaParser:
    JAVA_PATTERNS = {
        'class': re.compile(r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)'),
        'interface': re.compile(r'(?:public|private|protected)?\s*interface\s+(\w+)'),
        'method': re.compile(
            r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*'
            r'(?:synchronized)?\s*(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\('
        ),
        'field': re.compile(
            r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*'
            r'(\w+(?:<[^>]+>)?)\s+(\w+)\s*[;=]'
        ),
        'if_stmt': re.compile(r'\bif\s*\('),
        'for_stmt': re.compile(r'\bfor\s*\('),
        'while_stmt': re.compile(r'\bwhile\s*\('),
        'try_stmt': re.compile(r'\btry\s*\{'),
        'catch_stmt': re.compile(r'\bcatch\s*\('),
        'return_stmt': re.compile(r'\breturn\b'),
        'throw_stmt': re.compile(r'\bthrow\b'),
        'import_stmt': re.compile(r'import\s+([\w.]+(?:\.\*)?)\s*;'),
        'assignment': re.compile(r'(\w+)\s*=\s*'),
        'method_call': re.compile(r'(\w+)\s*\('),
        'variable_use': re.compile(r'\b([a-z]\w*)\b'),
    }

    NODE_TYPES = [
        'Module', 'ClassDef', 'InterfaceDef', 'MethodDef', 'FieldDef',
        'If', 'For', 'While', 'Try', 'Catch', 'Return', 'Throw',
        'Import', 'Assignment', 'MethodCall', 'VariableUse', 'Block',
        'Statement', 'Expression', 'Identifier', 'Literal'
    ]

    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        lines = source_code.split('\n')
        nodes = []
        edges = []
        cfg_edges = []
        dfg_edges = []
        functions = []
        node_id = 0

        root = {
            'id': node_id, 'type': 'Module', 'token': file_path.split('/')[-1] if '/' in file_path else file_path,
            'context': '', 'line_start': 1, 'line_end': len(lines),
            'col_offset': 0, 'depth': 0, 'in_degree': 0, 'num_children': 0
        }
        nodes.append(root)
        node_id += 1

        imports = []
        for i, line in enumerate(lines, 1):
            m = self.JAVA_PATTERNS['import_stmt'].search(line)
            if m:
                imp_node = {
                    'id': node_id, 'type': 'Import', 'token': m.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(imp_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                imports.append(node_id)
                root['num_children'] += 1
                node_id += 1

        for i in range(len(imports) - 1):
            cfg_edges.append({'source': imports[i], 'target': imports[i + 1], 'type': 'CFG', 'label': 'sequential'})

        brace_depth = 0
        class_stack = []
        method_start = None
        method_stmts = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            cm = self.JAVA_PATTERNS['class'].search(stripped)
            if cm:
                cls_node = {
                    'id': node_id, 'type': 'ClassDef', 'token': cm.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(cls_node)
                parent = class_stack[-1] if class_stack else 0
                edges.append({'source': parent, 'target': node_id, 'type': 'AST'})
                for n in nodes:
                    if n['id'] == parent:
                        n['num_children'] += 1
                        break
                class_stack.append(node_id)
                node_id += 1

            im = self.JAVA_PATTERNS['interface'].search(stripped)
            if im and not cm:
                int_node = {
                    'id': node_id, 'type': 'InterfaceDef', 'token': im.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(int_node)
                parent = class_stack[-1] if class_stack else 0
                edges.append({'source': parent, 'target': node_id, 'type': 'AST'})
                node_id += 1

            mm = self.JAVA_PATTERNS['method'].search(stripped)
            if mm and not cm and not im and not stripped.startswith('//') and not stripped.startswith('*'):
                meth_name = mm.group(1)
                if meth_name not in ('if', 'for', 'while', 'switch', 'catch', 'return', 'new', 'throw'):
                    meth_node = {
                        'id': node_id, 'type': 'MethodDef', 'token': meth_name,
                        'context': '', 'line_start': i, 'line_end': i,
                        'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
                    }
                    nodes.append(meth_node)
                    parent = class_stack[-1] if class_stack else 0
                    edges.append({'source': parent, 'target': node_id, 'type': 'AST'})
                    for n in nodes:
                        if n['id'] == parent:
                            n['num_children'] += 1
                            break

                    complexity = 1
                    functions.append({
                        'name': meth_name,
                        'node_id': node_id,
                        'line_start': i,
                        'line_end': i,
                        'args': [],
                        'num_statements': 0,
                        'has_return': False,
                        'complexity': complexity,
                    })

                    if method_stmts:
                        for si in range(len(method_stmts) - 1):
                            cfg_edges.append({
                                'source': method_stmts[si], 'target': method_stmts[si + 1],
                                'type': 'CFG', 'label': 'sequential'
                            })
                    method_stmts = []
                    method_start = node_id
                    node_id += 1

            for pattern_name, pattern in [
                ('if_stmt', 'If'), ('for_stmt', 'For'), ('while_stmt', 'While'),
                ('try_stmt', 'Try'), ('catch_stmt', 'Catch'),
                ('return_stmt', 'Return'), ('throw_stmt', 'Throw')
            ]:
                if self.JAVA_PATTERNS[pattern_name].search(stripped):
                    stmt_node = {
                        'id': node_id, 'type': pattern,
                        'token': stripped[:60], 'context': '',
                        'line_start': i, 'line_end': i,
                        'col_offset': 0, 'depth': 3, 'in_degree': 1, 'num_children': 0
                    }
                    nodes.append(stmt_node)
                    if method_start is not None:
                        edges.append({'source': method_start, 'target': node_id, 'type': 'AST'})
                        method_stmts.append(node_id)
                        if functions:
                            functions[-1]['num_statements'] += 1
                            if pattern == 'Return':
                                functions[-1]['has_return'] = True
                            if pattern in ('If', 'For', 'While'):
                                functions[-1]['complexity'] += 1

                    if pattern == 'If' and len(method_stmts) > 1:
                        cfg_edges.append({
                            'source': node_id, 'target': node_id,
                            'type': 'CFG', 'label': 'conditional_branch'
                        })

                    node_id += 1
                    break

            am = self.JAVA_PATTERNS['assignment'].search(stripped)
            if am and not stripped.startswith('//') and '==' not in stripped:
                var_name = am.group(1)
                if var_name not in ('if', 'for', 'while', 'return', 'class', 'public', 'private', 'protected'):
                    assign_node = {
                        'id': node_id, 'type': 'Assignment', 'token': var_name,
                        'context': 'Store', 'line_start': i, 'line_end': i,
                        'col_offset': 0, 'depth': 3, 'in_degree': 1, 'num_children': 0
                    }
                    nodes.append(assign_node)
                    if method_start is not None:
                        edges.append({'source': method_start, 'target': node_id, 'type': 'AST'})
                    node_id += 1

        definitions = {}
        for n in nodes:
            if n['type'] == 'Assignment' or (n['type'] == 'FieldDef'):
                token = n['token']
                if token:
                    definitions.setdefault(token, []).append(n['id'])

        for n in nodes:
            if n['context'] == 'Load' or n['type'] == 'VariableUse':
                token = n['token']
                if token in definitions:
                    for def_id in definitions[token]:
                        if def_id != n['id']:
                            dfg_edges.append({
                                'source': def_id, 'target': n['id'],
                                'type': 'DFG', 'variable': token
                            })

        return {
            'nodes': nodes,
            'edges': edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': functions,
            'language': 'Java',
            'file_path': file_path,
            'num_lines': len(lines)
        }
