"""Reproducible tiny synthetic holdout evaluation; writes measured outputs."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

def main():
 original=app.MODEL
 # Deterministic stratified holdout: every 3rd example within each class is test data.
 by={}
 for row in app.TRAIN: by.setdefault(row[1],[]).append(row)
 train=[]; test=[]
 for label,rows in sorted(by.items()):
  test.extend(rows[::3]); train.extend(rows[1::3]+rows[2::3])
 app.MODEL=app.ROOT/'experiments'/'router_eval_temp.json'; app.MODEL.parent.mkdir(exist_ok=True)
 app.train_router(train)
 correct=0; per={}
 for q,y in test:
  pred=app.route(q)['strategy']; correct+=pred==y; per.setdefault(y,[0,0]); per[y][1]+=1; per[y][0]+=pred==y
 accuracy=correct/max(1,len(test)); classes={k:{'correct':v[0],'total':v[1],'accuracy':round(v[0]/v[1],4)} for k,v in per.items()}
 app.MODEL=original; app.train_router()
 report={'dataset':'synthetic hand-labeled router examples','split':'deterministic stratified by label, every third held out','train_n':len(train),'test_n':len(test),'router_accuracy':round(accuracy,4),'per_class':classes,'fixed_hybrid_baseline_accuracy':None,'baseline_note':'Not measured: no human relevance labels for optimal retrieval strategy; do not compare classifier accuracy against retrieval quality.','limitations':'Small synthetic test set; examples are authored from templates and are not representative of enterprise traffic.'}
 (app.ROOT/'experiments'/'router_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 lines=['# Router evaluation report','',f"- Training examples: {len(train)}",f"- Held-out examples: {len(test)}",f"- Held-out accuracy: {accuracy:.3f}",'','Per-class:']
 lines += [f"- {k}: {v['correct']}/{v['total']} ({v['accuracy']:.3f})" for k,v in classes.items()]
 lines += ['', 'No fixed-hybrid comparison is reported: the small synthetic dataset has strategy labels but no independent relevance judgments. This is not evidence of real-world routing gains.']
 (app.ROOT/'experiments'/'router_report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 print(json.dumps(report,indent=2))
if __name__=='__main__': main()
