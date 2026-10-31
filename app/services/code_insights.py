import re
from collections import Counter
from functools import lru_cache
from pathlib import PurePosixPath
from app.services import source_store as store

FUNCTIONS = [
    r'\b(?:async\s+)?(?:def|function\s*\*?|fn|fun)\s+([A-Za-z_$]\w*)\s*(?:<[^>]*>)?\s*\(',
    r'\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(',
    r'\b(?:const|let|var)\s+([A-Za-z_$]\w*)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_]\w*)\s*=>',
    r'^\s*(?:(?:public|private|protected|internal|static|async|virtual|override|final|synchronized|abstract)\s+)+(?:[\w<>\[\],?.]+\s+)+([A-Za-z_]\w*)\s*\(',
]
TYPES = r'\b(?:class|interface|struct|enum|trait|record)\s+([A-Za-z_]\w*)'
SUPPORTED = {'Python','JavaScript','TypeScript','Java','C#','Go','Rust','Kotlin','Swift','PHP','C','C++'}


def declarations(text, language):
    if language not in SUPPORTED:
        return []
    cleaned = re.sub(r'/\*[\s\S]*?\*/|\x22{3}[\s\S]*?\x22{3}|\x27{3}[\s\S]*?\x27{3}', lambda m:'\n'*m.group().count('\n'), text)
    result=set()
    for number,line in enumerate(cleaned.splitlines(),1):
        if line.lstrip().startswith(('#','//','*','--')):
            continue
        line=re.sub(r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27','""',line)
        for pattern in FUNCTIONS:
            for match in re.finditer(pattern,line):
                result.add(('function',match.group(1),number))
        for match in re.finditer(TYPES,line):
            result.add(('type',match.group(1),number))
    return [{'kind':kind,'name':name,'line':line} for kind,name,line in sorted(result,key=lambda x:(x[2],x[0],x[1]))]


def readme_description(text):
    for paragraph in re.split(r'\n\s*\n',text):
        value=' '.join(paragraph.strip().split())
        if len(value)>60 and not value.startswith(('#','!','[','<','|','```','-','*','Copyright')):
            return re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',value)[:420]
    return ''


@lru_cache(maxsize=4)
def insights(project_id):
    metadata=store.project(project_id)
    with store.connect() as con:
        rows=[dict(r) for r in con.execute('SELECT path,content,language FROM sources WHERE project_id=? ORDER BY path',(project_id,))]
        passages=con.execute('SELECT count(*) FROM passages WHERE project_id=?',(project_id,)).fetchone()[0]
    folders=set();symbols=[];roots=set();sizes=[];blank=0;tests=0;total_bytes=0
    manifest_names={'package.json','pyproject.toml','go.mod','cargo.toml','pom.xml','composer.json','build.gradle','requirements.txt'}
    containers={'apps','applications','packages','microservices','services','lambda','functions','crates'}
    for row in rows:
        p=PurePosixPath(row['path']);parts=p.parts;lines=row['content'].splitlines()
        folders.update('/'.join(parts[:i]) for i in range(1,len(parts)))
        count=len(lines);blank+=sum(not line.strip() for line in lines);total_bytes+=len(row['content'].encode())
        sizes.append({'path':row['path'],'lines':count,'language':row['language']})
        tests+=bool(re.search(r'(^|/)(tests?|__tests__|specs?)(/|_)|[._](test|spec)\.',row['path'],re.I))
        symbols.extend(dict(s,path=row['path'],language=row['language']) for s in declarations(row['content'],row['language']))
        if p.name.lower() in manifest_names or p.suffix=='.csproj':
            roots.add(str(p.parent) if str(p.parent)!='.' else '')
        for i,part in enumerate(parts[:-2]):
            if part in containers and parts[i+1] not in containers and part!='applications':
                roots.add('/'.join(parts[:i+2]))
    roots={r for r in roots if not re.search(r'(^|/)(tests?|docs?|examples|manual-instrumentation[^/]*)(/|$)',r)}
    if not roots:
        roots={r['path'].split('/')[0] for r in rows if '/' in r['path']} or {''}
    grouped={r:[] for r in roots}
    for row in rows:
        matches=[r for r in roots if not r or row['path'].startswith(r+'/')]
        if matches:grouped[max(matches,key=len)].append(row)
    components=[]
    for root,group in grouped.items():
        if not group:continue
        langs=Counter(r['language'] for r in group)
        readme=next((r for r in group if PurePosixPath(r['path']).parent==PurePosixPath(root or '.') and PurePosixPath(r['path']).name.lower().startswith('readme')),None)
        entries=sorted((r['path'] for r in group if re.search(r'(^|/)(main|app|index|server|program|startup)\.',r['path'],re.I)),key=len)[:3]
        description=readme_description(readme['content']) if readme else ''
        detected=[]
        for label,pattern in [('HTTP controllers/routes',r'/(controllers|handlers|routes)/'),('service logic',r'/services/'),('data repositories',r'/repositories/'),('browser assets',r'/(wwwroot|public|frontend)/')]:
            if any(re.search(pattern,r['path'],re.I) for r in group):detected.append(label)
        if not description:description='Contains '+', '.join(detected)+'.' if detected else f"Source package with {len(group)} indexed files. Open its files to explore the implementation."
        components.append({'name':root.rsplit('/',1)[-1] if root else metadata['name'].split('/')[-1],'path':root,'file_count':len(group),'languages':dict(langs),'description':description,'description_path':readme['path'] if readme and readme_description(readme['content']) else None,'entry_files':entries})
    return {'functions':sum(s['kind']=='function' for s in symbols),'types':sum(s['kind']=='type' for s in symbols),
            'symbol_note':'Pattern-based declaration estimates, not a complete parser. Methods or syntax may be missed; comments and strings are excluded where recognized.',
            'detection_languages':sorted(SUPPORTED & {r['language'] for r in rows}),
            'folders':len(folders),'test_files':tests,'blank_lines':blank,'bytes':total_bytes,'passages':passages,
            'skipped_files':len(metadata['skipped']),'skipped_reasons':dict(Counter(s['reason'] for s in metadata['skipped'])),
            'largest_files':sorted(sizes,key=lambda r:-r['lines'])[:5],
            'components':sorted(components,key=lambda c:-c['file_count']), 'symbols':symbols}
