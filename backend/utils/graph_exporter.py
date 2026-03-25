import ast
import re
import math
from typing import Dict, List, Set


FRAMEWORK_DB = {
    'flask': 'Flask', 'django': 'Django', 'fastapi': 'FastAPI', 'tornado': 'Tornado',
    'bottle': 'Bottle', 'sanic': 'Sanic', 'starlette': 'Starlette', 'aiohttp': 'aiohttp',
    'numpy': 'NumPy', 'pandas': 'Pandas', 'scipy': 'SciPy', 'matplotlib': 'Matplotlib',
    'seaborn': 'Seaborn', 'plotly': 'Plotly', 'bokeh': 'Bokeh',
    'sklearn': 'scikit-learn', 'tensorflow': 'TensorFlow', 'torch': 'PyTorch',
    'keras': 'Keras', 'xgboost': 'XGBoost', 'lightgbm': 'LightGBM',
    'transformers': 'HuggingFace', 'langchain': 'LangChain',
    'requests': 'Requests', 'httpx': 'HTTPX', 'urllib3': 'urllib3',
    'sqlalchemy': 'SQLAlchemy', 'pymongo': 'PyMongo', 'redis': 'Redis',
    'celery': 'Celery', 'pytest': 'pytest', 'unittest': 'unittest',
    'asyncio': 'asyncio', 'threading': 'threading', 'multiprocessing': 'multiprocessing',
    'os': 'os', 'sys': 'sys', 'json': 'json', 'csv': 'csv', 're': 're',
    'pathlib': 'pathlib', 'collections': 'collections', 'itertools': 'itertools',
    'functools': 'functools', 'typing': 'typing', 'dataclasses': 'dataclasses',
    'pydantic': 'Pydantic', 'marshmallow': 'Marshmallow',
    'click': 'Click', 'typer': 'Typer', 'argparse': 'argparse',
    'logging': 'logging', 'datetime': 'datetime', 'time': 'time',
    'socket': 'socket', 'subprocess': 'subprocess', 'shutil': 'shutil',
    'hashlib': 'hashlib', 'secrets': 'secrets', 'cryptography': 'cryptography',
    'PIL': 'Pillow', 'cv2': 'OpenCV', 'networkx': 'NetworkX',
    'beautifulsoup4': 'BeautifulSoup', 'bs4': 'BeautifulSoup',
    'scrapy': 'Scrapy', 'selenium': 'Selenium',
    'pyyaml': 'PyYAML', 'yaml': 'PyYAML', 'toml': 'TOML',
    'docker': 'Docker SDK', 'boto3': 'AWS SDK', 'google': 'Google Cloud',
    'azure': 'Azure SDK', 'jwt': 'PyJWT', 'bcrypt': 'bcrypt',
    'spring': 'Spring', 'javax': 'Java EE', 'junit': 'JUnit',
    'lombok': 'Lombok', 'hibernate': 'Hibernate', 'jackson': 'Jackson',
    'apache': 'Apache Commons', 'guava': 'Guava', 'slf4j': 'SLF4J',
    'mockito': 'Mockito', 'assertj': 'AssertJ',
    'stdio': 'C Standard I/O', 'stdlib': 'C Standard Lib', 'string': 'string',
    'math': 'math', 'pthread': 'POSIX Threads', 'unistd': 'POSIX',
    'iostream': 'C++ I/O', 'vector': 'STL Vector', 'map': 'STL Map',
    'algorithm': 'STL Algorithm', 'memory': 'Smart Pointers',
    'thread': 'C++ Threading', 'mutex': 'C++ Mutex',
    'boost': 'Boost', 'eigen': 'Eigen', 'opencv2': 'OpenCV',
    'qt': 'Qt', 'gtk': 'GTK',
    'react': 'React', 'react-dom': 'React DOM', 'next': 'Next.js',
    'vue': 'Vue.js', 'svelte': 'Svelte', 'angular': 'Angular',
    'express': 'Express', 'koa': 'Koa', 'fastify': 'Fastify', 'hono': 'Hono',
    'axios': 'Axios', 'node-fetch': 'node-fetch',
    'tailwindcss': 'Tailwind CSS', 'styled-components': 'styled-components',
    'emotion': 'Emotion', 'sass': 'Sass',
    'prisma': 'Prisma', 'mongoose': 'Mongoose', 'sequelize': 'Sequelize', 'typeorm': 'TypeORM',
    'jest': 'Jest', 'vitest': 'Vitest', 'mocha': 'Mocha', 'cypress': 'Cypress',
    'webpack': 'Webpack', 'vite': 'Vite', 'esbuild': 'esbuild', 'rollup': 'Rollup',
    'lodash': 'Lodash', 'underscore': 'Underscore', 'ramda': 'Ramda',
    'moment': 'Moment.js', 'dayjs': 'Day.js', 'date-fns': 'date-fns',
    'zod': 'Zod', 'yup': 'Yup', 'joi': 'Joi',
    'redux': 'Redux', 'zustand': 'Zustand', 'mobx': 'MobX', 'jotai': 'Jotai',
    'trpc': 'tRPC', 'graphql': 'GraphQL', 'apollo': 'Apollo',
    'socket': 'Socket.IO', 'ws': 'WebSocket',
    'd3': 'D3.js', 'three': 'Three.js', 'chart': 'Chart.js', 'recharts': 'Recharts',
    'framer-motion': 'Framer Motion', 'gsap': 'GSAP',
    'lucide-react': 'Lucide', 'heroicons': 'Heroicons',
}

CATEGORY_MAP = {
    'web': {'flask', 'django', 'fastapi', 'tornado', 'bottle', 'sanic', 'starlette', 'aiohttp', 'spring', 'javax'},
    'data': {'numpy', 'pandas', 'scipy', 'polars'},
    'ml': {'sklearn', 'tensorflow', 'torch', 'keras', 'xgboost', 'lightgbm', 'transformers', 'langchain'},
    'viz': {'matplotlib', 'seaborn', 'plotly', 'bokeh'},
    'db': {'sqlalchemy', 'pymongo', 'redis', 'hibernate'},
    'test': {'pytest', 'unittest', 'junit', 'mockito', 'assertj'},
    'http': {'requests', 'httpx', 'urllib3', 'aiohttp'},
}


def detect_imports(source_code: str, language: str) -> Dict:
    imports = []
    frameworks = []
    categories = set()

    if language == 'Python':
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split('.')[0]
                        imports.append({
                            'module': alias.name,
                            'alias': alias.asname,
                            'line': node.lineno,
                            'type': 'import'
                        })
                        _classify(root, frameworks, categories)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        root = node.module.split('.')[0]
                        names = [a.name for a in (node.names or [])]
                        imports.append({
                            'module': node.module,
                            'names': names,
                            'line': node.lineno,
                            'type': 'from_import'
                        })
                        _classify(root, frameworks, categories)
        except SyntaxError:
            pass

    elif language == 'Java':
        for m in re.finditer(r'import\s+([\w.]+(?:\.\*)?)\s*;', source_code):
            mod = m.group(1)
            parts = mod.split('.')
            root = parts[0] if parts else mod
            imports.append({'module': mod, 'line': source_code[:m.start()].count('\n') + 1, 'type': 'import'})
            _classify(root, frameworks, categories)

    elif language in ('C', 'C++'):
        for m in re.finditer(r'#include\s*[<"]([^>"]+)[>"]', source_code):
            header = m.group(1)
            root = header.replace('.h', '').split('/')[0]
            imports.append({'module': header, 'line': source_code[:m.start()].count('\n') + 1, 'type': 'include'})
            _classify(root, frameworks, categories)

    elif language in ('JavaScript', 'TypeScript'):
        for m in re.finditer(r'import\s+(?:\{[^}]+\}|[\w*]+(?:\s*,\s*\{[^}]+\})?)\s+from\s+[\'"]([^\'"]+)[\'"]', source_code):
            mod = m.group(1)
            root = mod.split('/')[0].replace('@', '')
            imports.append({'module': mod, 'line': source_code[:m.start()].count('\n') + 1, 'type': 'import'})
            _classify(root, frameworks, categories)
        for m in re.finditer(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', source_code):
            mod = m.group(1)
            root = mod.split('/')[0].replace('@', '')
            imports.append({'module': mod, 'line': source_code[:m.start()].count('\n') + 1, 'type': 'require'})
            _classify(root, frameworks, categories)

    elif language == 'HTML':
        for m in re.finditer(r'<(?:script|link)[^>]*(?:src|href)\s*=\s*[\'"]([^\'"]+)[\'"]', source_code):
            ref = m.group(1)
            imports.append({'module': ref, 'line': source_code[:m.start()].count('\n') + 1, 'type': 'reference'})

    elif language == 'CSS':
        for m in re.finditer(r'@import\s+(?:url\s*\(\s*)?[\'"]([^\'"]+)[\'"]', source_code):
            ref = m.group(1)
            imports.append({'module': ref, 'line': source_code[:m.start()].count('\n') + 1, 'type': 'import'})

    seen = set()
    unique_fw = []
    for fw in frameworks:
        if fw['name'] not in seen:
            seen.add(fw['name'])
            unique_fw.append(fw)

    return {
        'imports': imports,
        'frameworks': unique_fw,
        'categories': list(categories),
        'import_count': len(imports),
    }


def _classify(root: str, frameworks: list, categories: set):
    root_lower = root.lower()
    if root_lower in FRAMEWORK_DB:
        frameworks.append({
            'name': FRAMEWORK_DB[root_lower],
            'module': root,
        })
    for cat, modules in CATEGORY_MAP.items():
        if root_lower in modules:
            categories.add(cat)


def export_graph_for_viz(program_graph: Dict, max_nodes: int = 200) -> Dict:
    graph = program_graph.get('graph')
    if not graph:
        return {'nodes': [], 'edges': []}

    raw_features = program_graph.get('node_features_raw', [])
    node_ids = program_graph.get('node_ids', [])

    if len(node_ids) > max_nodes:
        important = set()
        for i, feat in enumerate(raw_features):
            if i >= len(node_ids):
                break
            nt = feat.get('type', '')
            if nt in ('Module', 'FunctionDef', 'AsyncFunctionDef', 'ClassDef',
                       'If', 'For', 'While', 'Return', 'Import', 'ImportFrom',
                       'Assign', 'Try', 'Raise', 'Call', 'BinOp', 'Compare',
                       'MethodDef', 'StructDef', 'Include', 'MacroDef',
                       'TranslationUnit', 'InterfaceDef', 'MemAlloc', 'MemFree'):
                important.add(node_ids[i])
        if len(important) > max_nodes:
            important = set(list(important)[:max_nodes])
        selected = important
    else:
        selected = set(node_ids)

    id_to_feat = {}
    for i, nid in enumerate(node_ids):
        if i < len(raw_features):
            id_to_feat[nid] = raw_features[i]

    NODE_COLORS = {
        'Module': '#6366F1', 'TranslationUnit': '#6366F1',
        'FunctionDef': '#2563EB', 'AsyncFunctionDef': '#2563EB', 'MethodDef': '#2563EB',
        'ClassDef': '#7C3AED', 'InterfaceDef': '#7C3AED', 'StructDef': '#7C3AED',
        'If': '#F59E0B', 'For': '#F59E0B', 'While': '#F59E0B', 'Switch': '#F59E0B',
        'Return': '#10B981', 'Yield': '#10B981', 'YieldFrom': '#10B981',
        'Import': '#8B5CF6', 'ImportFrom': '#8B5CF6', 'Include': '#8B5CF6',
        'Assign': '#64748B', 'AugAssign': '#64748B', 'AnnAssign': '#64748B', 'Assignment': '#64748B',
        'Call': '#EC4899', 'MethodCall': '#EC4899',
        'Try': '#EF4444', 'Raise': '#EF4444', 'Catch': '#EF4444', 'Throw': '#EF4444',
        'BinOp': '#94A3B8', 'Compare': '#94A3B8', 'BoolOp': '#94A3B8', 'UnaryOp': '#94A3B8',
        'Name': '#CBD5E1', 'Identifier': '#CBD5E1', 'Constant': '#CBD5E1', 'Literal': '#CBD5E1',
        'MemAlloc': '#DC2626', 'MemFree': '#DC2626',
    }

    SIZE_MAP = {
        'Module': 14, 'TranslationUnit': 14,
        'FunctionDef': 12, 'AsyncFunctionDef': 12, 'MethodDef': 12,
        'ClassDef': 13, 'InterfaceDef': 13, 'StructDef': 13,
        'If': 8, 'For': 8, 'While': 8,
        'Return': 7, 'Import': 7, 'ImportFrom': 7,
        'Try': 8, 'Raise': 7,
        'Call': 7, 'Assign': 6,
    }

    viz_nodes = []
    node_set = set()
    for nid in selected:
        feat = id_to_feat.get(nid)
        if not feat:
            continue
        node_set.add(nid)
        nt = feat.get('type', 'Unknown')
        token = feat.get('token', '')
        label = token if token and len(token) < 30 else nt
        viz_nodes.append({
            'id': str(nid),
            'type': nt,
            'label': label,
            'token': token[:30] if token else '',
            'line': feat.get('line_start', 0),
            'depth': feat.get('depth', 0),
            'color': NODE_COLORS.get(nt, '#94A3B8'),
            'size': SIZE_MAP.get(nt, 5),
        })

    EDGE_STYLES = {
        'AST': {'color': '#6366F1', 'dash': None, 'label': 'AST', 'width': 1.5},
        'CFG': {'color': '#22C55E', 'dash': '5,3', 'label': 'CFG', 'width': 1.2},
        'DFG': {'color': '#EF4444', 'dash': '2,3', 'label': 'DFG', 'width': 1.0},
    }

    viz_edges = []
    seen_edges = set()
    for u, v, data in graph.edges(data=True):
        if u in node_set and v in node_set:
            edge_type = data.get('type', 'AST')
            key = (str(u), str(v), edge_type)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            style = EDGE_STYLES.get(edge_type, EDGE_STYLES['AST'])
            viz_edges.append({
                'source': str(u),
                'target': str(v),
                'type': edge_type,
                'color': style['color'],
                'dash': style['dash'],
                'width': style['width'],
                'label': data.get('label', ''),
                'variable': data.get('variable', ''),
            })

    return {
        'nodes': viz_nodes,
        'edges': viz_edges,
        'stats': {
            'total_nodes': len(viz_nodes),
            'total_edges': len(viz_edges),
            'ast_edges': sum(1 for e in viz_edges if e['type'] == 'AST'),
            'cfg_edges': sum(1 for e in viz_edges if e['type'] == 'CFG'),
            'dfg_edges': sum(1 for e in viz_edges if e['type'] == 'DFG'),
            'node_types': {},
        },
        'edge_styles': EDGE_STYLES,
    }

    nt_counts = {}
    for n in viz_nodes:
        nt_counts[n['type']] = nt_counts.get(n['type'], 0) + 1
    return {
        'nodes': viz_nodes,
        'edges': viz_edges,
        'stats': {
            'total_nodes': len(viz_nodes),
            'total_edges': len(viz_edges),
            'ast_edges': sum(1 for e in viz_edges if e['type'] == 'AST'),
            'cfg_edges': sum(1 for e in viz_edges if e['type'] == 'CFG'),
            'dfg_edges': sum(1 for e in viz_edges if e['type'] == 'DFG'),
            'node_types': nt_counts,
        },
        'edge_styles': EDGE_STYLES,
    }
