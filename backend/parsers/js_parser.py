import re
from typing import Dict, Optional, List


class JSParser:
    PATTERNS = {
        'func_decl': re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'),
        'arrow_const': re.compile(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(?([^)]*?)\)?\s*=>'),
        'class_decl': re.compile(r'(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'),
        'method_decl': re.compile(r'(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*\{'),
        'import_from': re.compile(r'import\s+(?:\{([^}]+)\}|(\w+)(?:\s*,\s*\{([^}]+)\})?)\s+from\s+[\'"]([^\'"]+)[\'"]'),
        'import_side': re.compile(r'import\s+[\'"]([^\'"]+)[\'"]'),
        'require': re.compile(r'(?:const|let|var)\s+(?:\{([^}]+)\}|(\w+))\s*=\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'),
        'export_default': re.compile(r'export\s+default\s+(?:function|class|)\s*(\w*)'),
        'export_named': re.compile(r'export\s+(?:const|let|var|function|class)\s+(\w+)'),
        'if_stmt': re.compile(r'\bif\s*\('),
        'else_if': re.compile(r'\belse\s+if\s*\('),
        'else_stmt': re.compile(r'\belse\s*\{'),
        'for_stmt': re.compile(r'\bfor\s*\('),
        'for_of': re.compile(r'\bfor\s*\(\s*(?:const|let|var)\s+\w+\s+of\b'),
        'for_in': re.compile(r'\bfor\s*\(\s*(?:const|let|var)\s+\w+\s+in\b'),
        'while_stmt': re.compile(r'\bwhile\s*\('),
        'do_stmt': re.compile(r'\bdo\s*\{'),
        'switch_stmt': re.compile(r'\bswitch\s*\('),
        'case_stmt': re.compile(r'\bcase\s+'),
        'try_stmt': re.compile(r'\btry\s*\{'),
        'catch_stmt': re.compile(r'\bcatch\s*\('),
        'finally_stmt': re.compile(r'\bfinally\s*\{'),
        'return_stmt': re.compile(r'\breturn\b'),
        'throw_stmt': re.compile(r'\bthrow\b'),
        'yield_stmt': re.compile(r'\byield\b'),
        'await_expr': re.compile(r'\bawait\b'),
        'new_expr': re.compile(r'\bnew\s+(\w+)'),
        'assignment': re.compile(r'(?:const|let|var)\s+(\w+)\s*='),
        'reassignment': re.compile(r'(\w+)\s*(?:=(?!=)|[+\-*/%&|^]=|\?\?=|&&=|\|\|=)'),
        'call_expr': re.compile(r'(\w+)\s*\('),
        'jsx_element': re.compile(r'<(\w+)[\s/>]'),
        'template_literal': re.compile(r'`[^`]*\$\{'),
        'optional_chain': re.compile(r'(\w+)\?\.\w+'),
        'destructure': re.compile(r'(?:const|let|var)\s+\{([^}]+)\}\s*='),
        'spread': re.compile(r'\.\.\.(\w+)'),
        'ternary': re.compile(r'\?\s*[^:]+\s*:'),
        'promise': re.compile(r'\.then\s*\(|\.catch\s*\(|Promise\.(all|race|resolve|reject)'),
        'type_annotation': re.compile(r':\s*(string|number|boolean|object|any|void|never|unknown|Array|Record|Map|Set)\b'),
        'interface_decl': re.compile(r'(?:export\s+)?interface\s+(\w+)'),
        'type_alias': re.compile(r'(?:export\s+)?type\s+(\w+)\s*='),
        'enum_decl': re.compile(r'(?:export\s+)?enum\s+(\w+)'),
        'generic': re.compile(r'<(\w+)(?:\s+extends\s+\w+)?>'),
    }

    SKIP_CALLS = {'if', 'for', 'while', 'switch', 'catch', 'return', 'throw', 'new', 'typeof', 'instanceof', 'void', 'delete', 'case', 'else', 'import', 'export', 'from', 'const', 'let', 'var', 'function', 'class', 'async', 'await', 'yield'}

    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        lines = source_code.split('\n')
        nodes = []
        edges = []
        cfg_edges = []
        dfg_edges = []
        functions = []
        node_id = 0
        is_ts = file_path.endswith('.ts') or file_path.endswith('.tsx')
        is_jsx = file_path.endswith('.jsx') or file_path.endswith('.tsx')
        lang = 'TypeScript' if is_ts else 'JavaScript'

        root = {
            'id': node_id, 'type': 'Module', 'token': file_path.split('/')[-1] if '/' in file_path else file_path,
            'context': '', 'line_start': 1, 'line_end': len(lines),
            'col_offset': 0, 'depth': 0, 'in_degree': 0, 'num_children': 0
        }
        nodes.append(root)
        node_id += 1

        func_stack = []
        current_func_id = None
        method_stmts = []
        brace_depth = 0
        definitions = {}
        uses = {}

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                continue

            brace_depth += stripped.count('{') - stripped.count('}')

            m = self.PATTERNS['import_from'].search(stripped)
            if m:
                named = m.group(1) or m.group(3) or ''
                default = m.group(2) or ''
                module = m.group(4)
                imp_names = []
                if default:
                    imp_names.append(default)
                if named:
                    imp_names.extend([n.strip().split(' as ')[0].strip() for n in named.split(',')])
                imp_node = {
                    'id': node_id, 'type': 'ImportFrom', 'token': module,
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(imp_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            m = self.PATTERNS['import_side'].search(stripped)
            if m and 'from' not in stripped:
                imp_node = {
                    'id': node_id, 'type': 'Import', 'token': m.group(1),
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(imp_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            m = self.PATTERNS['require'].search(stripped)
            if m:
                module = m.group(3)
                req_node = {
                    'id': node_id, 'type': 'Require', 'token': module,
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(req_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            if is_ts:
                for pat_name, node_type in [('interface_decl', 'InterfaceDef'), ('type_alias', 'TypeAlias'), ('enum_decl', 'EnumDef')]:
                    m = self.PATTERNS[pat_name].search(stripped)
                    if m:
                        ts_node = {
                            'id': node_id, 'type': node_type, 'token': m.group(1),
                            'context': '', 'line_start': i, 'line_end': i,
                            'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                        }
                        nodes.append(ts_node)
                        edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                        root['num_children'] += 1
                        node_id += 1
                        break

            m = self.PATTERNS['class_decl'].search(stripped)
            if m:
                cls_name = m.group(1)
                extends = m.group(2) or ''
                cls_node = {
                    'id': node_id, 'type': 'ClassDef', 'token': cls_name,
                    'context': extends, 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 1, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(cls_node)
                edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1
                node_id += 1
                continue

            is_func = False
            func_name = None
            func_args = []

            m = self.PATTERNS['func_decl'].search(stripped)
            if m:
                func_name = m.group(1)
                func_args = [a.strip().split(':')[0].strip().split('=')[0].strip() for a in m.group(2).split(',') if a.strip()] if m.group(2).strip() else []
                is_func = True

            if not is_func:
                m = self.PATTERNS['arrow_const'].search(stripped)
                if m:
                    func_name = m.group(1)
                    raw_args = m.group(2) or ''
                    func_args = [a.strip().split(':')[0].strip().split('=')[0].strip() for a in raw_args.split(',') if a.strip()] if raw_args.strip() else []
                    is_func = True

            if is_func and func_name:
                func_node = {
                    'id': node_id, 'type': 'FunctionDef', 'token': func_name,
                    'context': '', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 2, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(func_node)
                parent = 0
                edges.append({'source': parent, 'target': node_id, 'type': 'AST'})
                root['num_children'] += 1

                if method_stmts and current_func_id is not None:
                    for si in range(len(method_stmts) - 1):
                        cfg_edges.append({'source': method_stmts[si], 'target': method_stmts[si + 1], 'type': 'CFG', 'label': 'sequential'})

                method_stmts = []
                current_func_id = node_id
                complexity = 1

                functions.append({
                    'name': func_name,
                    'node_id': node_id,
                    'line_start': i,
                    'line_end': i,
                    'args': func_args,
                    'num_statements': 0,
                    'has_return': False,
                    'complexity': complexity,
                })
                node_id += 1
                continue

            for pat_name, node_type in [
                ('if_stmt', 'If'), ('else_if', 'ElseIf'), ('for_stmt', 'For'),
                ('for_of', 'ForOf'), ('for_in', 'ForIn'),
                ('while_stmt', 'While'), ('do_stmt', 'DoWhile'),
                ('switch_stmt', 'Switch'), ('try_stmt', 'Try'),
                ('catch_stmt', 'Catch'), ('finally_stmt', 'Finally'),
                ('return_stmt', 'Return'), ('throw_stmt', 'Throw'),
            ]:
                if self.PATTERNS[pat_name].search(stripped):
                    stmt_node = {
                        'id': node_id, 'type': node_type, 'token': stripped[:60],
                        'context': '', 'line_start': i, 'line_end': i,
                        'col_offset': 0, 'depth': 3, 'in_degree': 1, 'num_children': 0
                    }
                    nodes.append(stmt_node)
                    if current_func_id is not None:
                        edges.append({'source': current_func_id, 'target': node_id, 'type': 'AST'})
                        method_stmts.append(node_id)
                        if functions:
                            functions[-1]['num_statements'] += 1
                            if node_type == 'Return':
                                functions[-1]['has_return'] = True
                            if node_type in ('If', 'ElseIf', 'For', 'ForOf', 'ForIn', 'While', 'DoWhile', 'Switch'):
                                functions[-1]['complexity'] += 1
                    else:
                        edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                        root['num_children'] += 1

                    if node_type == 'If' and current_func_id is not None:
                        cfg_edges.append({'source': node_id, 'target': node_id, 'type': 'CFG', 'label': 'conditional_branch'})
                    if node_type in ('For', 'ForOf', 'ForIn', 'While', 'DoWhile') and current_func_id is not None:
                        cfg_edges.append({'source': node_id, 'target': node_id, 'type': 'CFG', 'label': 'loop_back'})

                    node_id += 1
                    break

            m = self.PATTERNS['assignment'].search(stripped)
            if m and not stripped.startswith('//'):
                var_name = m.group(1)
                definitions.setdefault(var_name, []).append(node_id)
                assign_node = {
                    'id': node_id, 'type': 'Assign', 'token': var_name,
                    'context': 'Store', 'line_start': i, 'line_end': i,
                    'col_offset': 0, 'depth': 3, 'in_degree': 1, 'num_children': 0
                }
                nodes.append(assign_node)
                if current_func_id is not None:
                    edges.append({'source': current_func_id, 'target': node_id, 'type': 'AST'})
                    if functions:
                        functions[-1]['num_statements'] += 1
                else:
                    edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                node_id += 1

            if is_jsx:
                for jsx_m in self.PATTERNS['jsx_element'].finditer(stripped):
                    tag = jsx_m.group(1)
                    if tag[0].isupper() or tag in ('div', 'span', 'p', 'h1', 'h2', 'h3', 'button', 'input', 'form', 'img', 'a', 'ul', 'li', 'section', 'header', 'footer', 'nav', 'main'):
                        jsx_node = {
                            'id': node_id, 'type': 'JSXElement', 'token': tag,
                            'context': '', 'line_start': i, 'line_end': i,
                            'col_offset': 0, 'depth': 3, 'in_degree': 1, 'num_children': 0
                        }
                        nodes.append(jsx_node)
                        if current_func_id is not None:
                            edges.append({'source': current_func_id, 'target': node_id, 'type': 'AST'})
                        else:
                            edges.append({'source': 0, 'target': node_id, 'type': 'AST'})
                        node_id += 1
                        break

        if method_stmts:
            for si in range(len(method_stmts) - 1):
                cfg_edges.append({'source': method_stmts[si], 'target': method_stmts[si + 1], 'type': 'CFG', 'label': 'sequential'})

        for var_name, def_ids in definitions.items():
            for n in nodes:
                if n.get('context') != 'Store' and var_name in n.get('token', ''):
                    for def_id in def_ids:
                        if def_id != n['id']:
                            dfg_edges.append({
                                'source': def_id, 'target': n['id'],
                                'type': 'DFG', 'variable': var_name
                            })

        return {
            'nodes': nodes,
            'edges': edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': functions,
            'language': lang,
            'file_path': file_path,
            'num_lines': len(lines)
        }
