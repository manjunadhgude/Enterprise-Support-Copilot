"""Measured retrieval metrics on a small, manually relevance-labeled synthetic set."""
import json, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'retrieval_eval.jsonl'

def metric_for(strategy, examples):
    recall=[]; reciprocal=[]; precision=[]; elapsed=[]; routes={}
    for row in examples:
        selected=strategy
        if strategy=='learned_router':
            predicted=app.route(row['query'])['strategy']
            selected=predicted if predicted in ('keyword','dense','hybrid') else 'hybrid'
            routes[selected]=routes.get(selected,0)+1
        elif strategy=='fixed_hybrid': selected='hybrid'
        start=time.perf_counter()
        found=app.retrieve(row['query'],app.USERS['employee'],selected)
        elapsed.append((time.perf_counter()-start)*1000)
        ranked=[]
        for item in found:
            if item['id'] not in ranked: ranked.append(item['id'])
        relevant=set(row['relevant_document_ids'])
        matched=[i+1 for i,doc_id in enumerate(ranked[:3]) if doc_id in relevant]
        recall.append(len(matched)/len(relevant))
        precision.append(len(matched)/3)
        reciprocal.append(1/min(matched) if matched else 0)
    result={'queries':len(examples),'recall_at_3':round(sum(recall)/len(recall),4),
            'precision_at_3':round(sum(precision)/len(precision),4),
            'mrr_at_3':round(sum(reciprocal)/len(reciprocal),4),
            'mean_latency_ms':round(sum(elapsed)/len(elapsed),3)}
    if routes: result['selected_retrievers']=routes
    return result

def main():
    examples=[json.loads(line) for line in DATA.read_text(encoding='utf8').splitlines() if line.strip()]
    original_db,original_model=app.DB,app.MODEL
    try:
        with tempfile.TemporaryDirectory(prefix='p1-retrieval-eval-') as tmp:
            app.DB=Path(tmp)/'eval.sqlite3'; app.MODEL=Path(tmp)/'router.json'
            app.init_db()
            report={'dataset':'manual synthetic relevance judgments','queries':len(examples),
                    'k':3,'strategies':{name:metric_for(name,examples) for name in ('keyword','dense','hybrid','fixed_hybrid','learned_router')},
                    'limitations':'Six authored questions over five synthetic documents; no independent annotators, confidence intervals, production traffic, or generalization claim. Learned routing was trained on the separate small synthetic router set; non-document route predictions fall back to hybrid.'}
            (ROOT/'retrieval_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
            lines=['# Retrieval experiment report','',f"Dataset: {report['dataset']} ({len(examples)} queries, k=3).",'',
                   '| Strategy | Recall@3 | Precision@3 | MRR@3 | Mean latency (ms) |','|---|---:|---:|---:|---:|']
            for name,metrics in report['strategies'].items():
                lines.append(f"| {name} | {metrics['recall_at_3']:.4f} | {metrics['precision_at_3']:.4f} | {metrics['mrr_at_3']:.4f} | {metrics['mean_latency_ms']:.3f} |")
            lines += ['',report['limitations'],'These measurements are a local pipeline check only. They do not establish that one retriever is better; the tiny authored test set yields identical ranking metrics across the three strategies.']
            (ROOT/'retrieval_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
            print(json.dumps(report,indent=2))
    finally:
        app.DB,app.MODEL=original_db,original_model

if __name__=='__main__': main()
