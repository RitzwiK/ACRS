import os
import sys
import json
import shutil
import tempfile
import traceback
import hashlib
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from parsers.python_parser import PythonASTParser
from parsers.java_parser import JavaParser
from parsers.cpp_parser import CppParser
from graph.program_graph import ProgramGraphBuilder
from graph.feature_encoder import FeatureEncoder
from models.gat_model import GATDefectDetector
from models.benchmark import BenchmarkEvaluator
from utils.repo_handler import RepoHandler
from utils.report_generator import ReportGenerator
from utils.graph_exporter import detect_imports, export_graph_for_viz

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

UPLOAD_DIR = tempfile.mkdtemp(prefix='acrs_')
RESULTS_CACHE = {}

PARSERS = {
    '.py': PythonASTParser(),
    '.java': JavaParser(),
    '.c': CppParser(),
    '.cpp': CppParser(),
    '.h': CppParser(),
    '.hpp': CppParser(),
}

SUPPORTED_EXTENSIONS = set(PARSERS.keys())

gat_model = GATDefectDetector(
    input_dim=64,
    hidden_dim=128,
    output_dim=4,
    num_heads=4,
    num_layers=3,
    edge_types=['AST', 'CFG', 'DFG']
)

feature_encoder = FeatureEncoder(embedding_dim=64)
report_generator = ReportGenerator()


@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'model': 'GAT-v1',
        'supported_languages': ['Python', 'Java', 'C', 'C++'],
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/analyze', methods=['POST'])
def analyze_repository():
    data = request.get_json()
    if not data or 'repo_url' not in data:
        return jsonify({'error': 'Repository URL is required'}), 400

    repo_url = data['repo_url']
    branch = data.get('branch', 'main')
    scan_id = hashlib.md5(f"{repo_url}:{branch}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]

    try:
        repo_handler = RepoHandler(UPLOAD_DIR)
        repo_path, repo_info = repo_handler.clone_repository(repo_url, branch)

        source_files = repo_handler.discover_source_files(repo_path, SUPPORTED_EXTENSIONS)

        if not source_files:
            return jsonify({
                'error': 'No supported source files found in repository',
                'supported': list(SUPPORTED_EXTENSIONS)
            }), 400

        analysis_results = {
            'scan_id': scan_id,
            'repository': repo_info,
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': 0,
            'total_nodes': 0,
            'total_edges': 0,
            'files': [],
            'summary': {
                'total_issues': 0,
                'bugs': 0,
                'code_smells': 0,
                'design_issues': 0,
                'clean': 0,
                'severity_distribution': {'critical': 0, 'warning': 0, 'info': 0},
                'language_breakdown': {},
                'confidence_avg': 0.0
            },
            'graph_stats': {
                'total_ast_edges': 0,
                'total_cfg_edges': 0,
                'total_dfg_edges': 0,
                'avg_graph_density': 0.0
            }
        }

        all_confidences = []

        for file_path in source_files:
            try:
                result = analyze_single_file(file_path, repo_path)
                if result:
                    analysis_results['files'].append(result)
                    analysis_results['files_analyzed'] += 1
                    analysis_results['total_nodes'] += result['graph_info']['num_nodes']
                    analysis_results['total_edges'] += result['graph_info']['num_edges']

                    lang = result['language']
                    if lang not in analysis_results['summary']['language_breakdown']:
                        analysis_results['summary']['language_breakdown'][lang] = {
                            'files': 0, 'issues': 0, 'bugs': 0, 'smells': 0, 'design': 0
                        }
                    analysis_results['summary']['language_breakdown'][lang]['files'] += 1

                    for issue in result['issues']:
                        analysis_results['summary']['total_issues'] += 1
                        cat = issue['category'].lower()
                        if 'bug' in cat:
                            analysis_results['summary']['bugs'] += 1
                            analysis_results['summary']['language_breakdown'][lang]['bugs'] += 1
                        elif 'smell' in cat:
                            analysis_results['summary']['code_smells'] += 1
                            analysis_results['summary']['language_breakdown'][lang]['smells'] += 1
                        elif 'design' in cat:
                            analysis_results['summary']['design_issues'] += 1
                            analysis_results['summary']['language_breakdown'][lang]['design'] += 1

                        sev = issue.get('severity', 'info')
                        if sev in analysis_results['summary']['severity_distribution']:
                            analysis_results['summary']['severity_distribution'][sev] += 1

                        all_confidences.append(issue.get('confidence', 0.0))

                    analysis_results['summary']['language_breakdown'][lang]['issues'] += len(result['issues'])

                    gi = result['graph_info']
                    analysis_results['graph_stats']['total_ast_edges'] += gi.get('ast_edges', 0)
                    analysis_results['graph_stats']['total_cfg_edges'] += gi.get('cfg_edges', 0)
                    analysis_results['graph_stats']['total_dfg_edges'] += gi.get('dfg_edges', 0)

            except Exception as e:
                analysis_results['files'].append({
                    'path': str(Path(file_path).relative_to(repo_path)),
                    'error': str(e),
                    'issues': []
                })

        analysis_results['summary']['clean'] = analysis_results['files_analyzed'] - len(
            [f for f in analysis_results['files'] if f.get('issues')]
        )

        if all_confidences:
            analysis_results['summary']['confidence_avg'] = round(
                sum(all_confidences) / len(all_confidences), 3
            )

        if analysis_results['total_edges'] > 0:
            total_e = (analysis_results['graph_stats']['total_ast_edges'] +
                       analysis_results['graph_stats']['total_cfg_edges'] +
                       analysis_results['graph_stats']['total_dfg_edges'])
            analysis_results['graph_stats']['avg_graph_density'] = round(
                total_e / max(analysis_results['total_nodes'], 1), 3
            )

        analysis_results['report'] = report_generator.generate(analysis_results)

        RESULTS_CACHE[scan_id] = analysis_results

        try:
            shutil.rmtree(repo_path, ignore_errors=True)
        except:
            pass

        return jsonify(analysis_results)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def analyze_single_file(file_path, repo_root):
    ext = Path(file_path).suffix.lower()
    parser = PARSERS.get(ext)
    if not parser:
        return None

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        source_code = f.read()

    if len(source_code.strip()) < 10:
        return None

    ast_data = parser.parse(source_code, str(file_path))
    if not ast_data or not ast_data.get('nodes'):
        return None

    graph_builder = ProgramGraphBuilder()
    program_graph = graph_builder.build(ast_data, source_code)

    encoded_features = feature_encoder.encode(program_graph)

    predictions = gat_model.predict(encoded_features, program_graph)

    issues = []
    for pred in predictions:
        if pred['category'] != 'Clean':
            issues.append({
                'category': pred['category'],
                'confidence': round(pred['confidence'], 3),
                'severity': pred['severity'],
                'line_start': pred.get('line_start', 0),
                'line_end': pred.get('line_end', 0),
                'node_type': pred.get('node_type', ''),
                'description': pred.get('description', ''),
                'suggestion': pred.get('suggestion', ''),
                'attention_weights': pred.get('attention_weights', {}),
                'structural_context': pred.get('structural_context', '')
            })

    rel_path = str(Path(file_path).relative_to(repo_root))
    lang_map = {'.py': 'Python', '.java': 'Java', '.c': 'C', '.cpp': 'C++', '.h': 'C', '.hpp': 'C++'}
    language = lang_map.get(ext, 'Unknown')

    import_info = detect_imports(source_code, language)
    graph_viz = export_graph_for_viz(program_graph, max_nodes=200)

    return {
        'path': rel_path,
        'language': language,
        'lines': source_code.count('\n') + 1,
        'size_bytes': len(source_code.encode('utf-8')),
        'issues': issues,
        'issue_count': len(issues),
        'imports': import_info,
        'graph_info': {
            'num_nodes': program_graph['num_nodes'],
            'num_edges': program_graph['num_edges'],
            'ast_edges': program_graph.get('ast_edge_count', 0),
            'cfg_edges': program_graph.get('cfg_edge_count', 0),
            'dfg_edges': program_graph.get('dfg_edge_count', 0),
            'node_types': program_graph.get('node_type_counts', {}),
        },
        'graph_viz': graph_viz,
        'source_preview': source_code[:2000] if len(source_code) > 2000 else source_code
    }


@app.route('/api/results/<scan_id>', methods=['GET'])
def get_results(scan_id):
    if scan_id in RESULTS_CACHE:
        return jsonify(RESULTS_CACHE[scan_id])
    return jsonify({'error': 'Scan not found'}), 404


@app.route('/api/file/<scan_id>/<path:file_path>', methods=['GET'])
def get_file_detail(scan_id, file_path):
    if scan_id not in RESULTS_CACHE:
        return jsonify({'error': 'Scan not found'}), 404

    results = RESULTS_CACHE[scan_id]
    for f in results['files']:
        if f['path'] == file_path:
            return jsonify(f)
    return jsonify({'error': 'File not found in scan'}), 404


@app.route('/api/benchmark', methods=['POST'])
def run_benchmark():
    try:
        python_parser = PARSERS['.py']
        graph_builder = ProgramGraphBuilder()
        evaluator = BenchmarkEvaluator(python_parser, graph_builder, feature_encoder, gat_model)
        results = evaluator.run_full_evaluation()
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("  ACRS - Automated Code Review System")
    print("  Graph Neural Network-Based Defect Detection")
    print("=" * 60)
    print(f"  Model: GAT with type-aware message passing")
    print(f"  Languages: Python, Java, C, C++")
    print(f"  Edge types: AST, CFG, DFG")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
