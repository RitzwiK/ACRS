import re
from typing import Dict, Optional, List
from html.parser import HTMLParser


class _DOMBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.edges = []
        self.stack = []
        self.node_id = 0
        self.functions = []
        self.cfg_edges = []
        self.dfg_edges = []
        self.script_lines = []
        self.style_lines = []
        self.in_script = False
        self.in_style = False
        self.imports = []

        root = {
            'id': 0, 'type': 'Document', 'token': 'document',
            'context': '', 'line_start': 1, 'line_end': 1,
            'col_offset': 0, 'depth': 0, 'in_degree': 0, 'num_children': 0
        }
        self.nodes.append(root)
        self.node_id = 1
        self.stack.append(0)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        parent = self.stack[-1] if self.stack else 0
        nid = self.node_id
        self.node_id += 1

        attr_str = ' '.join(f'{k}={v}' for k, v in attrs if v) if attrs else ''
        id_attr = ''
        class_attr = ''
        for k, v in attrs:
            if k == 'id':
                id_attr = v or ''
            if k == 'class':
                class_attr = v or ''

        token = tag
        if id_attr:
            token = f'{tag}#{id_attr}'
        elif class_attr:
            first_cls = class_attr.split()[0] if class_attr else ''
            if first_cls:
                token = f'{tag}.{first_cls}'

        node_type = 'Element'
        if tag in ('html', 'head', 'body'):
            node_type = 'RootElement'
        elif tag in ('script',):
            node_type = 'Script'
            self.in_script = True
        elif tag in ('style',):
            node_type = 'Style'
            self.in_style = True
        elif tag in ('link',):
            node_type = 'Link'
            for k, v in attrs:
                if k == 'href' and v:
                    self.imports.append(v)
        elif tag in ('a', 'button', 'input', 'select', 'textarea', 'form'):
            node_type = 'Interactive'
        elif tag in ('div', 'section', 'article', 'main', 'aside', 'header', 'footer', 'nav'):
            node_type = 'Layout'
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'label', 'strong', 'em'):
            node_type = 'Text'
        elif tag in ('img', 'video', 'audio', 'canvas', 'svg', 'iframe'):
            node_type = 'Media'
        elif tag in ('ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody'):
            node_type = 'DataDisplay'
        elif tag in ('meta', 'title', 'base'):
            node_type = 'Meta'

        for k, v in attrs:
            if k == 'src' and v and tag == 'script':
                self.imports.append(v)

        node = {
            'id': nid, 'type': node_type, 'token': token,
            'context': tag, 'line_start': line, 'line_end': line,
            'col_offset': 0, 'depth': len(self.stack), 'in_degree': 1, 'num_children': 0
        }
        self.nodes.append(node)
        self.edges.append({'source': parent, 'target': nid, 'type': 'AST'})
        for n in self.nodes:
            if n['id'] == parent:
                n['num_children'] += 1
                break

        void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
        if tag not in void_tags:
            self.stack.append(nid)

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        if tag == 'style':
            self.in_style = False
        if self.stack and len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data):
        if self.in_script:
            self.script_lines.append(data)
        elif self.in_style:
            self.style_lines.append(data)

    def handle_comment(self, data):
        line = self.getpos()[0]
        parent = self.stack[-1] if self.stack else 0
        nid = self.node_id
        self.node_id += 1
        node = {
            'id': nid, 'type': 'Comment', 'token': data.strip()[:40],
            'context': '', 'line_start': line, 'line_end': line,
            'col_offset': 0, 'depth': len(self.stack), 'in_degree': 1, 'num_children': 0
        }
        self.nodes.append(node)
        self.edges.append({'source': parent, 'target': nid, 'type': 'AST'})


class HTMLParser_:
    def parse(self, source_code: str, file_path: str = '') -> Optional[Dict]:
        builder = _DOMBuilder()
        try:
            builder.feed(source_code)
        except Exception:
            pass

        if len(builder.nodes) <= 1:
            return None

        siblings_by_parent = {}
        for edge in builder.edges:
            parent = edge['source']
            child = edge['target']
            siblings_by_parent.setdefault(parent, []).append(child)

        cfg_edges = []
        for parent, children in siblings_by_parent.items():
            for j in range(len(children) - 1):
                cfg_edges.append({
                    'source': children[j], 'target': children[j + 1],
                    'type': 'CFG', 'label': 'sequential'
                })

        id_map = {}
        class_map = {}
        for n in builder.nodes:
            token = n.get('token', '')
            if '#' in token:
                parts = token.split('#')
                if len(parts) == 2:
                    id_map[parts[1]] = n['id']
            if '.' in token:
                parts = token.split('.')
                if len(parts) == 2:
                    class_map.setdefault(parts[1], []).append(n['id'])

        dfg_edges = []
        for n in builder.nodes:
            token = n.get('token', '')
            context = n.get('context', '')
            if context == 'a':
                href = ''
                if '#' in token:
                    href = token.split('#')[-1]
                    if href in id_map and id_map[href] != n['id']:
                        dfg_edges.append({
                            'source': n['id'], 'target': id_map[href],
                            'type': 'DFG', 'variable': f'link-to-#{href}'
                        })
            if context == 'label':
                pass

        return {
            'nodes': builder.nodes,
            'edges': builder.edges,
            'cfg_edges': cfg_edges,
            'dfg_edges': dfg_edges,
            'functions': builder.functions,
            'language': 'HTML',
            'file_path': file_path,
            'num_lines': source_code.count('\n') + 1
        }
