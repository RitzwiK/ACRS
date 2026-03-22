import ast
import sys
from typing import Dict, List, Optional, Any, Tuple


class PythonASTParser:
    NODE_TYPE_MAP = {
        ast.Module: 'Module',
        ast.FunctionDef: 'FunctionDef',
        ast.AsyncFunctionDef: 'AsyncFunctionDef',
        ast.ClassDef: 'ClassDef',
        ast.Return: 'Return',
        ast.Delete: 'Delete',
        ast.Assign: 'Assign',
        ast.AugAssign: 'AugAssign',
        ast.AnnAssign: 'AnnAssign',
        ast.For: 'For',
        ast.AsyncFor: 'AsyncFor',
        ast.While: 'While',
        ast.If: 'If',
        ast.With: 'With',
        ast.AsyncWith: 'AsyncWith',
        ast.Raise: 'Raise',
        ast.Try: 'Try',
        ast.Assert: 'Assert',
        ast.Import: 'Import',
        ast.ImportFrom: 'ImportFrom',
        ast.Global: 'Global',
        ast.Nonlocal: 'Nonlocal',
        ast.Expr: 'Expr',
        ast.Pass: 'Pass',
        ast.Break: 'Break',
        ast.Continue: 'Continue',
        ast.BoolOp: 'BoolOp',
        ast.NamedExpr: 'NamedExpr',
        ast.BinOp: 'BinOp',
        ast.UnaryOp: 'UnaryOp',
        ast.Lambda: 'Lambda',
        ast.IfExp: 'IfExp',
        ast.Dict: 'Dict',
        ast.Set: 'Set',
        ast.ListComp: 'ListComp',
        ast.SetComp: 'SetComp',
        ast.DictComp: 'DictComp',
        ast.GeneratorExp: 'GeneratorExp',
        ast.Await: 'Await',
        ast.Yield: 'Yield',
        ast.YieldFrom: 'YieldFrom',
        ast.Compare: 'Compare',
        ast.Call: 'Call',
        ast.FormattedValue: 'FormattedValue',
        ast.JoinedStr: 'JoinedStr',
        ast.Constant: 'Constant',
        ast.Attribute: 'Attribute',
        ast.Subscript: 'Subscript',
        ast.Starred: 'Starred',
        ast.Name: 'Name',
        ast.List: 'List',
        ast.Tuple: 'Tuple',
        ast.Slice: 'Slice',
    }

    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            return None

        nodes = []
        edges = []
        node_counter = [0]
        node_map = {}

        def get_node_id():
            nid = node_counter[0]
            node_counter[0] += 1
            return nid

        def get_token(node):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Constant):
                return str(node.value)[:50]
            if isinstance(node, ast.Attribute):
                return node.attr
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                return node.name
            if isinstance(node, ast.ClassDef):
                return node.name
            if isinstance(node, ast.Import):
                return ','.join(a.name for a in node.names)
            if isinstance(node, ast.ImportFrom):
                return node.module or ''
            return ''

        def get_context(node):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    return 'Store'
                elif isinstance(node.ctx, ast.Load):
                    return 'Load'
                elif isinstance(node.ctx, ast.Del):
                    return 'Del'
            return ''

        def visit(node, parent_id=None, depth=0):
            node_type = self.NODE_TYPE_MAP.get(type(node), type(node).__name__)
            nid = get_node_id()
            node_map[id(node)] = nid

            node_info = {
                'id': nid,
                'type': node_type,
                'token': get_token(node),
                'context': get_context(node),
                'line_start': getattr(node, 'lineno', 0),
                'line_end': getattr(node, 'end_lineno', getattr(node, 'lineno', 0)),
                'col_offset': getattr(node, 'col_offset', 0),
                'depth': depth,
                'in_degree': 0,
                'num_children': 0,
            }
            nodes.append(node_info)

            if parent_id is not None:
                edges.append({
                    'source': parent_id,
                    'target': nid,
                    'type': 'AST'
                })
                for n in nodes:
                    if n['id'] == parent_id:
                        n['num_children'] += 1
                        break
                node_info['in_degree'] += 1

            for child in ast.iter_child_nodes(node):
                visit(child, nid, depth + 1)

        visit(tree)

        functions = self._extract_functions(tree, nodes, node_map)
        cfg_edges = self._build_cfg(tree, node_map)
        dfg_edges = self._build_dfg(tree, node_map)

        return {
            'nodes': nodes,
            'edges': edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': functions,
            'language': 'Python',
            'file_path': file_path,
            'num_lines': source_code.count('\n') + 1
        }

    def _extract_functions(self, tree, nodes, node_map):
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = []
                for arg in node.args.args:
                    args.append(arg.arg)
                functions.append({
                    'name': node.name,
                    'node_id': node_map.get(id(node), -1),
                    'line_start': node.lineno,
                    'line_end': getattr(node, 'end_lineno', node.lineno),
                    'args': args,
                    'num_statements': len(node.body),
                    'has_return': any(isinstance(n, ast.Return) for n in ast.walk(node)),
                    'complexity': self._compute_complexity(node),
                })
        return functions

    def _compute_complexity(self, node):
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ExceptHandler,)):
                complexity += 1
            elif isinstance(child, (ast.Assert,)):
                complexity += 1
        return complexity

    def _build_cfg(self, tree, node_map):
        cfg_edges = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._build_function_cfg(node, node_map, cfg_edges)
        return cfg_edges

    def _build_function_cfg(self, func_node, node_map, cfg_edges):
        stmts = func_node.body
        for i in range(len(stmts) - 1):
            src_id = node_map.get(id(stmts[i]))
            tgt_id = node_map.get(id(stmts[i + 1]))
            if src_id is not None and tgt_id is not None:
                cfg_edges.append({
                    'source': src_id,
                    'target': tgt_id,
                    'type': 'CFG',
                    'label': 'sequential'
                })

        for stmt in stmts:
            self._build_stmt_cfg(stmt, node_map, cfg_edges)

    def _build_stmt_cfg(self, stmt, node_map, cfg_edges):
        stmt_id = node_map.get(id(stmt))
        if stmt_id is None:
            return

        if isinstance(stmt, ast.If):
            if stmt.body:
                body_id = node_map.get(id(stmt.body[0]))
                if body_id is not None:
                    cfg_edges.append({
                        'source': stmt_id, 'target': body_id,
                        'type': 'CFG', 'label': 'true_branch'
                    })
                for i in range(len(stmt.body) - 1):
                    s = node_map.get(id(stmt.body[i]))
                    t = node_map.get(id(stmt.body[i + 1]))
                    if s is not None and t is not None:
                        cfg_edges.append({'source': s, 'target': t, 'type': 'CFG', 'label': 'sequential'})

            if stmt.orelse:
                else_id = node_map.get(id(stmt.orelse[0]))
                if else_id is not None:
                    cfg_edges.append({
                        'source': stmt_id, 'target': else_id,
                        'type': 'CFG', 'label': 'false_branch'
                    })
                for i in range(len(stmt.orelse) - 1):
                    s = node_map.get(id(stmt.orelse[i]))
                    t = node_map.get(id(stmt.orelse[i + 1]))
                    if s is not None and t is not None:
                        cfg_edges.append({'source': s, 'target': t, 'type': 'CFG', 'label': 'sequential'})

        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            if stmt.body:
                body_id = node_map.get(id(stmt.body[0]))
                if body_id is not None:
                    cfg_edges.append({
                        'source': stmt_id, 'target': body_id,
                        'type': 'CFG', 'label': 'loop_body'
                    })
                last_body = node_map.get(id(stmt.body[-1]))
                if last_body is not None:
                    cfg_edges.append({
                        'source': last_body, 'target': stmt_id,
                        'type': 'CFG', 'label': 'back_edge'
                    })

        elif isinstance(stmt, ast.While):
            if stmt.body:
                body_id = node_map.get(id(stmt.body[0]))
                if body_id is not None:
                    cfg_edges.append({
                        'source': stmt_id, 'target': body_id,
                        'type': 'CFG', 'label': 'loop_body'
                    })
                last_body = node_map.get(id(stmt.body[-1]))
                if last_body is not None:
                    cfg_edges.append({
                        'source': last_body, 'target': stmt_id,
                        'type': 'CFG', 'label': 'back_edge'
                    })

        elif isinstance(stmt, ast.Try):
            if stmt.body:
                body_id = node_map.get(id(stmt.body[0]))
                if body_id is not None:
                    cfg_edges.append({
                        'source': stmt_id, 'target': body_id,
                        'type': 'CFG', 'label': 'try_body'
                    })
            for handler in stmt.handlers:
                handler_id = node_map.get(id(handler))
                if handler_id is not None:
                    cfg_edges.append({
                        'source': stmt_id, 'target': handler_id,
                        'type': 'CFG', 'label': 'exception_handler'
                    })

        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.stmt):
                self._build_stmt_cfg(child, node_map, cfg_edges)

    def _build_dfg(self, tree, node_map):
        dfg_edges = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._build_function_dfg(node, node_map, dfg_edges)
        return dfg_edges

    def _build_function_dfg(self, func_node, node_map, dfg_edges):
        definitions = {}

        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                nid = node_map.get(id(node))
                if nid is not None:
                    definitions[node.id] = definitions.get(node.id, [])
                    definitions[node.id].append(nid)

            if isinstance(node, ast.arg):
                nid = node_map.get(id(node))
                if nid is not None:
                    definitions[node.arg] = definitions.get(node.arg, [])
                    definitions[node.arg].append(nid)

        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                use_id = node_map.get(id(node))
                if use_id is not None and node.id in definitions:
                    for def_id in definitions[node.id]:
                        if def_id != use_id:
                            dfg_edges.append({
                                'source': def_id,
                                'target': use_id,
                                'type': 'DFG',
                                'variable': node.id
                            })

        return dfg_edges
