from typing import Dict, List
from datetime import datetime


class ReportGenerator:
    def generate(self, analysis_results: Dict) -> Dict:
        summary = analysis_results.get('summary', {})
        files = analysis_results.get('files', [])
        graph_stats = analysis_results.get('graph_stats', {})

        total = summary.get('total_issues', 0)
        bugs = summary.get('bugs', 0)
        smells = summary.get('code_smells', 0)
        design = summary.get('design_issues', 0)
        files_analyzed = analysis_results.get('files_analyzed', 0)

        if files_analyzed == 0:
            health_score = 100.0
        else:
            issue_density = total / max(files_analyzed, 1)
            severity_weight = (
                summary['severity_distribution'].get('critical', 0) * 3 +
                summary['severity_distribution'].get('warning', 0) * 1.5 +
                summary['severity_distribution'].get('info', 0) * 0.5
            )
            health_score = max(0, 100 - issue_density * 10 - severity_weight * 2)
            health_score = round(min(100, health_score), 1)

        if health_score >= 80:
            health_grade = 'A'
        elif health_score >= 60:
            health_grade = 'B'
        elif health_score >= 40:
            health_grade = 'C'
        elif health_score >= 20:
            health_grade = 'D'
        else:
            health_grade = 'F'

        hotspots = []
        for f in files:
            if f.get('issues'):
                hotspots.append({
                    'path': f['path'],
                    'issue_count': len(f['issues']),
                    'critical_count': sum(1 for i in f['issues'] if i.get('severity') == 'critical'),
                    'top_issue': f['issues'][0]['category'] if f['issues'] else '',
                })
        hotspots.sort(key=lambda x: (x['critical_count'], x['issue_count']), reverse=True)

        pattern_counts = {}
        for f in files:
            for issue in f.get('issues', []):
                pattern = issue.get('pattern', issue.get('category', 'Unknown'))
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        recommendations = []
        if bugs > 0:
            recommendations.append({
                'priority': 'high',
                'text': f'Address {bugs} bug-prone pattern(s) — these represent potential runtime failures'
            })
        if smells > 0:
            recommendations.append({
                'priority': 'medium',
                'text': f'Refactor {smells} code smell(s) to improve maintainability'
            })
        if design > 0:
            recommendations.append({
                'priority': 'low',
                'text': f'Consider addressing {design} design inefficiency(ies) for long-term code health'
            })

        return {
            'health_score': health_score,
            'health_grade': health_grade,
            'total_issues': total,
            'hotspots': hotspots[:10],
            'pattern_distribution': pattern_counts,
            'recommendations': recommendations,
            'graph_analysis': {
                'total_nodes': analysis_results.get('total_nodes', 0),
                'total_edges': analysis_results.get('total_edges', 0),
                'ast_edges': graph_stats.get('total_ast_edges', 0),
                'cfg_edges': graph_stats.get('total_cfg_edges', 0),
                'dfg_edges': graph_stats.get('total_dfg_edges', 0),
                'density': graph_stats.get('avg_graph_density', 0),
            },
            'generated_at': datetime.now().isoformat()
        }
