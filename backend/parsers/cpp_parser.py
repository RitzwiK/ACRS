import re
from typing import Dict, Optional, List


class CppParser:
    PATTERNS = {
        'include': re.compile(r'#include\s*[<"]([^>"]+)[>"]'),
        'define': re.compile(r'#define\s+(\w+)'),
        'function': re.compile(
            r'(?:(?:static|inline|virtual|extern|const)?\s+)*'
            r'(\w+(?:\s*[*&])?)\s+(\w+)\s*\(([^)]*)\)\s*(?:const)?\s*\{'
        ),
        'struct': re.compile(r'(?:typedef\s+)?struct\s+(\w+)'),
        'class': re.compile(r'class\s+(\w+)'),
        'if_stmt': re.compile(r'\bif\s*\('),
        'else_stmt': re.compile(r'\belse\b'),
        'for_stmt': re.compile(r'\bfor\s*\('),
        'while_stmt': re.compile(r'\bwhile\s*\('),
        'switch_stmt': re.compile(r'\bswitch\s*\('),
        'return_stmt': re.compile(r'\breturn\b'),
        'malloc': re.compile(r'\b(?:malloc|calloc|realloc)\s*\('),
        'free': re.compile(r'\bfree\s*\('),
        'new': re.compile(r'\bnew\s+'),
        'delete': re.compile(r'\bdelete\b'),
        'assignment': re.compile(r'(\w+)\s*=\s*(?!=)'),
        'pointer_deref': re.compile(r'\*(\w+)'),
        'null_check': re.compile(r'(\w+)\s*(?:==|!=)\s*(?:NULL|nullptr|0)'),
    }

    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        lines = source_code.split('\n')
        nodes = []
        edges = []
        cfg_edges = []
        dfg_edges = []
        functions = []
        node_id = 0

        root = {
            'id': node_id, 'type': 'TranslationUnit',
            'token': file_path.split('/')[-1] if '/' in file_path else file_path,
            'context': '', 'line_start': 1, 'line_end': len(lines),
            'col_offset': 0, 'depth': 0, 'in_degree': 0, 'num_children': 0
        }
        nodes.append(root)
        node_id += 1

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue

            m = self.PATTERNS['include'].search(stripped)
            if m:
                inc_node = {
                    'id': node_id, 'type': 'Include', 'token': m.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(inc_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            m = self.PATTERNS['define'].search(stripped)
            if m:
                def_node = {
                    'id': node_id, 'type': 'MacroDef', 'token': m.group(1),
                    'context': 'Store', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(def_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            cm = self.PATTERNS['class'].search(stripped)
            if cm:
                cls_node = {
                    'id': node_id, 'type': 'ClassDef', 'token': cm.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(cls_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            sm = self.PATTERNS['struct'].search(stripped)
            if sm:
                st_node = {
                    'id': node_id, 'type': 'StructDef', 'token': sm.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(st_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            fm = self.PATTERNS['function'].search(stripped)
            if fm:
                ret_type = fm.group(1)
                func_name = fm.group(2)
                params = fm.group(3)

                func_node = {
                    'id': node_id, 'type': 'FunctionDef', 'token': func_name,
                    'context': ret_type, 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(func_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1

                func_id = node_id
                node_id += 1

                args = [p.strip() for p in params.split(',') if p.strip()] if params.strip() else []
                complexity = 1

                functions.append({
                    'name': func_name,
                    'node_id': func_id,
                    'line_start': i,
                    'line_end': i,
                    'args': args,
                    'num_statements': 0,
                    'has_return': False,
                    'complexity': complexity,
                })
                continue

            for pat_name, node_type in [
                ('if_stmt', 'If'), ('for_stmt', 'For'), ('while_stmt', 'While'),
                ('switch_stmt', 'Switch'), ('return_stmt', 'Return')
            ]:
                if self.PATTERNS[pat_name].search(stripped):
                    stmt_node = {
                        'id': node_id, 'type': node_type, 'token': stripped[:60],
                        'context': '', 'line_start': i, 'line_end': i,
                        'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
                    }
                    nodes.append(stmt_node)
                    if functions:
                        edges.append({'source': functions[-1]['node_id'], 'target': node_id, 'type': 'AST'})
                        functions[-1]['num_statements'] += 1
                        if node_type == 'Return':
                            functions[-1]['has_return'] = True
                        if node_type in ('If', 'For', 'While', 'Switch'):
                            functions[-1]['complexity'] += 1
                    node_id += 1
                    break

            if self.PATTERNS['malloc'].search(stripped):
                alloc_node = {
                    'id': node_id, 'type': 'MemAlloc', 'token': stripped[:60],
                    'context': 'Store', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(alloc_node)
                if functions:
                    edges.append({'source': functions[-1]['node_id'], 'target': node_id, 'type': 'AST'})
                node_id += 1

            if self.PATTERNS['free'].search(stripped):
                free_node = {
                    'id': node_id, 'type': 'MemFree', 'token': stripped[:60],
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(free_node)
                if functions:
                    edges.append({'source': functions[-1]['node_id'], 'target': node_id, 'type': 'AST'})
                node_id += 1

        definitions = {}
        for n in nodes:
            if n['context'] == 'Store':
                definitions.setdefault(n['token'], []).append(n['id'])

        return {
            'nodes': nodes,
            'edges': edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': functions,
            'language': 'C/C++',
            'file_path': file_path,
            'num_lines': len(lines)
        }
