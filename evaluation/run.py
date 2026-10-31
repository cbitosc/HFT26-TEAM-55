import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services import source_store as store

questions = json.loads((ROOT/'evaluation/questions.json').read_text())
with tempfile.TemporaryDirectory() as temp:
    store.DB_PATH = Path(temp)/'evaluation.db'
    store.init()
    data = io.BytesIO()
    with zipfile.ZipFile(data,'w') as archive:
        archive.write(ROOT/'README.md','README.md')
        for path in sorted((ROOT/'app').rglob('*')):
            if path.suffix in {'.py','.html','.js','.css'}:
                archive.write(path,str(path.relative_to(ROOT)))
    project = store.ingest(data.getvalue(),'CodeCompass evaluation')
    rows=[]
    for item in questions:
        results=store.search(project['id'],item['question'],5)
        hit=any(r['file_path']==item['expected_file'] for r in results)
        rows.append(dict(item,hit_at_5=hit,returned_paths=[r['file_path'] for r in results]))
    report={'method':'Lexical retrieval, expected file among top five passages. Source-reviewed labels; not a measure of LLM answer correctness or generalization.', 'hits':sum(r['hit_at_5'] for r in rows),'total':len(rows),'results':rows}
    (ROOT/'evaluation/results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Relevant-file hit@5: {report['hits']}/{report['total']}")
