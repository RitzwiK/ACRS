import numpy as np
import time
import hashlib
from typing import Dict, List, Tuple
from collections import defaultdict


BENCHMARK_SUITE = [
    {
        "id": "bug_missing_return_01",
        "code": """
def divide(a, b):
    if b != 0:
        result = a / b
    print("done")
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Bug-Prone", "pattern": "missing_return", "line_start": 2, "line_end": 5}
        ],
        "description": "Function with conditional assignment but no return statement"
    },
    {
        "id": "bug_missing_return_02",
        "code": """
def get_status(code):
    if code == 200:
        msg = "OK"
    elif code == 404:
        msg = "Not Found"
    elif code == 500:
        msg = "Server Error"
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Bug-Prone", "pattern": "missing_return", "line_start": 2, "line_end": 8}
        ],
        "description": "Multi-branch function without return or default assignment"
    },
    {
        "id": "smell_high_complexity_01",
        "code": """
def process(data, mode, flag, check):
    result = []
    for item in data:
        if mode == 'a':
            if flag:
                if item > 0:
                    if check:
                        result.append(item * 2)
                    else:
                        result.append(item)
                else:
                    if check:
                        result.append(0)
            else:
                if item < 0:
                    result.append(abs(item))
        elif mode == 'b':
            if flag and check:
                result.append(item ** 2)
            elif flag or check:
                result.append(item + 1)
        elif mode == 'c':
            for sub in item:
                if sub > 0:
                    result.append(sub)
    return result
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "high_complexity", "line_start": 2, "line_end": 27}
        ],
        "description": "Function with cyclomatic complexity >10"
    },
    {
        "id": "smell_deep_nesting_01",
        "code": """
def deeply_nested(a, b, c, d, e, f):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            return a + b + c + d + e + f
    return 0
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "deep_nesting", "line_start": 3, "line_end": 8},
            {"category": "Code Smell", "pattern": "long_parameter_list", "line_start": 2, "line_end": 9}
        ],
        "description": "Deeply nested conditionals with too many parameters"
    },
    {
        "id": "smell_long_params_01",
        "code": """
def send_email(to, cc, bcc, subject, body, html_body, attachments, priority):
    if not to:
        return False
    msg = {"to": to, "cc": cc, "bcc": bcc}
    msg["subject"] = subject
    msg["body"] = body
    msg["html"] = html_body
    msg["files"] = attachments
    msg["priority"] = priority
    return msg
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "long_parameter_list", "line_start": 2, "line_end": 11}
        ],
        "description": "Function with 8 parameters"
    },
    {
        "id": "clean_simple_function_01",
        "code": """
def add(a, b):
    return a + b
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Clean simple function with no issues"
    },
    {
        "id": "clean_well_structured_01",
        "code": """
def validate_email(email):
    if not email:
        return False
    if '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    return len(parts[1]) > 0
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Well-structured validation with early returns"
    },
    {
        "id": "clean_class_01",
        "code": """
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1
        return self.count

    def reset(self):
        self.count = 0
        return self.count
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Clean class with simple methods"
    },
    {
        "id": "design_god_function_01",
        "code": "\n".join([
            "def do_everything(data):",
            "    results = []",
        ] + [f"    x{i} = data[{i}]" for i in range(55)] + [
            "    for item in results:",
            "        if item > 0:",
            "            results.append(item)",
            "    return results"
        ]),
        "language": "Python",
        "ground_truth": [
            {"category": "Design Inefficiency", "pattern": "god_function", "line_start": 1, "line_end": 60}
        ],
        "description": "Function with >50 statements indicating too many responsibilities"
    },
    {
        "id": "smell_unused_var_01",
        "code": """
def calculate(x, y):
    temp = x * 2
    unused = y + 100
    result = x + y
    return result
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "unused_variable", "line_start": 3, "line_end": 3},
            {"category": "Code Smell", "pattern": "unused_variable", "line_start": 4, "line_end": 4}
        ],
        "description": "Variables defined but never referenced"
    },
    {
        "id": "bug_missing_return_03",
        "code": """
def parse_config(path):
    with open(path) as f:
        data = f.read()
    if data:
        config = {}
        for line in data.split('\\n'):
            if '=' in line:
                k, v = line.split('=', 1)
                config[k.strip()] = v.strip()
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Bug-Prone", "pattern": "missing_return", "line_start": 2, "line_end": 10}
        ],
        "description": "Config parser that never returns the parsed result"
    },
    {
        "id": "smell_complexity_02",
        "code": """
def route_request(method, path, auth, body, headers):
    if method == 'GET':
        if auth:
            if '/admin' in path:
                return handle_admin_get(path)
            elif '/api' in path:
                return handle_api_get(path, headers)
            else:
                return handle_get(path)
        else:
            if '/public' in path:
                return handle_public(path)
    elif method == 'POST':
        if auth:
            if body:
                return handle_post(path, body)
        else:
            return 401
    elif method == 'DELETE':
        if auth and '/admin' in path:
            return handle_delete(path)
    return 404
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "high_complexity", "line_start": 2, "line_end": 22},
            {"category": "Code Smell", "pattern": "long_parameter_list", "line_start": 2, "line_end": 22}
        ],
        "description": "Router with high branching complexity"
    },
    {
        "id": "clean_decorator_01",
        "code": """
def retry(max_attempts=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Clean retry decorator pattern"
    },
    {
        "id": "bug_missing_return_04",
        "code": """
def find_max(items):
    if not items:
        print("empty list")
    current_max = items[0]
    for item in items[1:]:
        if item > current_max:
            current_max = item
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Bug-Prone", "pattern": "missing_return", "line_start": 2, "line_end": 8}
        ],
        "description": "Finds max but never returns it"
    },
    {
        "id": "clean_list_comprehension_01",
        "code": """
def process_items(items):
    valid = [x for x in items if x is not None]
    doubled = [x * 2 for x in valid]
    return sorted(doubled)
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Clean Pythonic list processing"
    },
    {
        "id": "smell_nesting_02",
        "code": """
def validate(data):
    if data:
        if 'name' in data:
            if len(data['name']) > 0:
                if 'email' in data:
                    if '@' in data['email']:
                        if 'age' in data:
                            if data['age'] > 0:
                                return True
    return False
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "deep_nesting", "line_start": 3, "line_end": 9}
        ],
        "description": "Validation with excessive nesting instead of guard clauses"
    },
    {
        "id": "design_god_function_02",
        "code": "\n".join([
            "def initialize_system(config):",
        ] + [f"    step_{i} = config.get('step_{i}', {i})" for i in range(60)] + [
            "    return True"
        ]),
        "language": "Python",
        "ground_truth": [
            {"category": "Design Inefficiency", "pattern": "god_function", "line_start": 1, "line_end": 62}
        ],
        "description": "Massive initialization function"
    },
    {
        "id": "clean_context_manager_01",
        "code": """
class DatabaseConnection:
    def __init__(self, url):
        self.url = url
        self.conn = None

    def __enter__(self):
        self.conn = connect(self.url)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        return False
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Clean context manager implementation"
    },
    {
        "id": "mixed_issues_01",
        "code": """
def complex_handler(req, resp, db, cache, logger, config):
    temp = req.get('temp')
    if req:
        if req.get('type') == 'A':
            if req.get('sub') == '1':
                if db:
                    if cache:
                        if config.get('enabled'):
                            result = db.query(req)
                            return result
        elif req.get('type') == 'B':
            logger.info("type B")
    return None
""",
        "language": "Python",
        "ground_truth": [
            {"category": "Code Smell", "pattern": "long_parameter_list", "line_start": 2, "line_end": 14},
            {"category": "Code Smell", "pattern": "deep_nesting", "line_start": 5, "line_end": 11},
            {"category": "Code Smell", "pattern": "unused_variable", "line_start": 3, "line_end": 3}
        ],
        "description": "Multiple issues: long params, deep nesting, unused variable"
    },
    {
        "id": "clean_functional_01",
        "code": """
def pipeline(data):
    filtered = filter(lambda x: x > 0, data)
    mapped = map(lambda x: x ** 2, filtered)
    return list(mapped)
""",
        "language": "Python",
        "ground_truth": [],
        "description": "Clean functional pipeline"
    },
]


class BenchmarkEvaluator:
    def __init__(self, parser, graph_builder, feature_encoder, gat_model):
        self.parser = parser
        self.graph_builder = graph_builder
        self.encoder = feature_encoder
        self.model = gat_model

    def run_full_evaluation(self) -> Dict:
        start_time = time.time()

        per_sample_results = []
        all_gt_labels = []
        all_pred_labels = []
        all_pred_confidences = []
        category_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        pattern_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
        confidence_buckets = defaultdict(lambda: {"correct": 0, "total": 0})
        graph_complexity_vs_accuracy = []
        detection_latencies = []

        categories = ["Bug-Prone", "Code Smell", "Design Inefficiency", "Clean"]
        confusion = np.zeros((4, 4), dtype=int)

        for sample in BENCHMARK_SUITE:
            sample_start = time.time()
            result = self._evaluate_single(sample)
            sample_latency = time.time() - sample_start
            detection_latencies.append(sample_latency)
            result["latency_ms"] = round(sample_latency * 1000, 1)
            per_sample_results.append(result)

            gt_cats = set()
            for gt in sample["ground_truth"]:
                gt_cats.add(gt["category"])
            if not gt_cats:
                gt_cats.add("Clean")

            pred_cats = set()
            for pred in result["predictions"]:
                pred_cats.add(pred["category"])
            if not pred_cats:
                pred_cats.add("Clean")

            for cat in categories:
                is_gt = cat in gt_cats
                is_pred = cat in pred_cats
                if is_gt and is_pred:
                    category_metrics[cat]["tp"] += 1
                elif is_pred and not is_gt:
                    category_metrics[cat]["fp"] += 1
                elif is_gt and not is_pred:
                    category_metrics[cat]["fn"] += 1
                else:
                    category_metrics[cat]["tn"] += 1

            gt_idx = categories.index(list(gt_cats)[0]) if gt_cats else 3
            pred_idx = categories.index(list(pred_cats)[0]) if pred_cats else 3
            confusion[gt_idx][pred_idx] += 1

            for gt in sample["ground_truth"]:
                pattern = gt.get("pattern", "unknown")
                matched = any(
                    p["category"] == gt["category"] and
                    self._lines_overlap(p, gt)
                    for p in result["predictions"]
                )
                if matched:
                    pattern_metrics[pattern]["tp"] += 1
                else:
                    pattern_metrics[pattern]["fn"] += 1

            for pred in result["predictions"]:
                matched_any_gt = any(
                    pred["category"] == gt["category"] and
                    self._lines_overlap(pred, gt)
                    for gt in sample["ground_truth"]
                )
                if not matched_any_gt:
                    pat = pred.get("pattern", "unknown")
                    pattern_metrics[pat]["fp"] += 1

                conf = pred.get("confidence", 0.5)
                bucket = round(conf, 1)
                is_correct = any(
                    pred["category"] == gt["category"]
                    for gt in sample["ground_truth"]
                )
                confidence_buckets[bucket]["total"] += 1
                if is_correct:
                    confidence_buckets[bucket]["correct"] += 1

            graph_complexity_vs_accuracy.append({
                "sample_id": sample["id"],
                "num_nodes": result.get("graph_nodes", 0),
                "num_edges": result.get("graph_edges", 0),
                "ast_edges": result.get("ast_edges", 0),
                "cfg_edges": result.get("cfg_edges", 0),
                "dfg_edges": result.get("dfg_edges", 0),
                "gt_count": len(sample["ground_truth"]),
                "pred_count": len(result["predictions"]),
                "correct": result["correct_detections"],
                "missed": result["missed_detections"],
                "false_alarms": result["false_alarms"],
            })

        overall = self._compute_overall_metrics(category_metrics, categories)

        per_category = {}
        for cat in categories:
            m = category_metrics[cat]
            per_category[cat] = self._compute_prf(m["tp"], m["fp"], m["fn"], m["tn"])

        per_pattern = {}
        for pat, m in pattern_metrics.items():
            prec = m["tp"] / (m["tp"] + m["fp"]) if (m["tp"] + m["fp"]) > 0 else 0
            rec = m["tp"] / (m["tp"] + m["fn"]) if (m["tp"] + m["fn"]) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            per_pattern[pat] = {
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
                "support": m["tp"] + m["fn"]
            }

        calibration = []
        for bucket in sorted(confidence_buckets.keys()):
            b = confidence_buckets[bucket]
            calibration.append({
                "confidence_bin": bucket,
                "accuracy": round(b["correct"] / b["total"], 4) if b["total"] > 0 else 0,
                "count": b["total"]
            })

        total_time = time.time() - start_time

        return {
            "benchmark_info": {
                "total_samples": len(BENCHMARK_SUITE),
                "total_ground_truth_issues": sum(len(s["ground_truth"]) for s in BENCHMARK_SUITE),
                "clean_samples": sum(1 for s in BENCHMARK_SUITE if not s["ground_truth"]),
                "defective_samples": sum(1 for s in BENCHMARK_SUITE if s["ground_truth"]),
                "total_time_seconds": round(total_time, 2),
                "avg_latency_ms": round(np.mean(detection_latencies) * 1000, 1),
            },
            "overall_metrics": overall,
            "per_category_metrics": per_category,
            "per_pattern_metrics": per_pattern,
            "confusion_matrix": {
                "labels": categories,
                "matrix": confusion.tolist()
            },
            "confidence_calibration": calibration,
            "graph_analysis": graph_complexity_vs_accuracy,
            "per_sample_results": per_sample_results,
        }

    def _evaluate_single(self, sample: Dict) -> Dict:
        code = sample["code"]
        gt = sample["ground_truth"]

        ast_data = self.parser.parse(code, f"{sample['id']}.py")
        if not ast_data or not ast_data.get("nodes"):
            return {
                "id": sample["id"],
                "description": sample["description"],
                "predictions": [],
                "ground_truth": gt,
                "correct_detections": 0,
                "missed_detections": len(gt),
                "false_alarms": 0,
                "graph_nodes": 0,
                "graph_edges": 0,
                "ast_edges": 0,
                "cfg_edges": 0,
                "dfg_edges": 0,
            }

        graph = self.graph_builder.build(ast_data, code)
        features = self.encoder.encode(graph)
        predictions = self.model.predict(features, graph)

        correct = 0
        missed = 0
        gt_matched = set()
        pred_matched = set()

        for gi, g in enumerate(gt):
            found = False
            for pi, p in enumerate(predictions):
                if p["category"] == g["category"] and self._lines_overlap(p, g):
                    found = True
                    gt_matched.add(gi)
                    pred_matched.add(pi)
                    break
            if found:
                correct += 1
            else:
                missed += 1

        false_alarms = len([i for i in range(len(predictions)) if i not in pred_matched])

        return {
            "id": sample["id"],
            "description": sample["description"],
            "predictions": [{
                "category": p["category"],
                "pattern": p.get("pattern", ""),
                "confidence": p.get("confidence", 0),
                "severity": p.get("severity", ""),
                "line_start": p.get("line_start", 0),
                "line_end": p.get("line_end", 0),
                "description": p.get("description", ""),
            } for p in predictions],
            "ground_truth": gt,
            "correct_detections": correct,
            "missed_detections": missed,
            "false_alarms": false_alarms,
            "graph_nodes": graph["num_nodes"],
            "graph_edges": graph["num_edges"],
            "ast_edges": graph.get("ast_edge_count", 0),
            "cfg_edges": graph.get("cfg_edge_count", 0),
            "dfg_edges": graph.get("dfg_edge_count", 0),
        }

    def _lines_overlap(self, a: Dict, b: Dict) -> bool:
        a_start = a.get("line_start", 0)
        a_end = a.get("line_end", a_start)
        b_start = b.get("line_start", 0)
        b_end = b.get("line_end", b_start)
        return a_start <= b_end and b_start <= a_end

    def _compute_prf(self, tp, fp, fn, tn):
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "support": tp + fn
        }

    def _compute_overall_metrics(self, category_metrics, categories):
        total_tp = sum(category_metrics[c]["tp"] for c in categories)
        total_fp = sum(category_metrics[c]["fp"] for c in categories)
        total_fn = sum(category_metrics[c]["fn"] for c in categories)
        total_tn = sum(category_metrics[c]["tn"] for c in categories)

        micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        micro_f1 = 2 * micro_prec * micro_rec / (micro_prec + micro_rec) if (micro_prec + micro_rec) > 0 else 0

        macro_prec = np.mean([
            category_metrics[c]["tp"] / (category_metrics[c]["tp"] + category_metrics[c]["fp"])
            if (category_metrics[c]["tp"] + category_metrics[c]["fp"]) > 0 else 0
            for c in categories
        ])
        macro_rec = np.mean([
            category_metrics[c]["tp"] / (category_metrics[c]["tp"] + category_metrics[c]["fn"])
            if (category_metrics[c]["tp"] + category_metrics[c]["fn"]) > 0 else 0
            for c in categories
        ])
        macro_f1 = 2 * macro_prec * macro_rec / (macro_prec + macro_rec) if (macro_prec + macro_rec) > 0 else 0

        return {
            "micro_precision": round(micro_prec, 4),
            "micro_recall": round(micro_rec, 4),
            "micro_f1": round(micro_f1, 4),
            "macro_precision": round(float(macro_prec), 4),
            "macro_recall": round(float(macro_rec), 4),
            "macro_f1": round(float(macro_f1), 4),
        }
