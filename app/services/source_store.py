from contextlib import contextmanager
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse

import httpx

DB_PATH = Path(os.getenv('EXPLORER_DB', str(Path(__file__).resolve().parents[2] / 'data/explorer.db')))
MAX_ARCHIVE = int(os.getenv('MAX_ARCHIVE_MB', '20')) * 1024 * 1024
MAX_FILE = int(os.getenv('MAX_SOURCE_KB', '256')) * 1024
MAX_FILES = int(os.getenv('MAX_SOURCE_FILES', '1000'))
EXCLUDED = set('node_modules vendor dist build target bin obj .git .venv venv __pycache__ coverage .next .nuxt .cache .idea .vscode'.split())
BINARY_EXT = set('.png .jpg .jpeg .gif .ico .pdf .woff .woff2 .ttf .mp4 .mp3 .zip .gz .tar .exe .dll .so .pyc .class .jar .db .sqlite .lock .map'.split())
LANGUAGES = {'.py':'Python', '.js':'JavaScript', '.jsx':'JavaScript', '.ts':'TypeScript', '.tsx':'TypeScript', '.java':'Java', '.go':'Go', '.rs':'Rust', '.cs':'C#', '.rb':'Ruby', '.php':'PHP', '.cpp':'C++', '.c':'C', '.swift':'Swift', '.kt':'Kotlin', '.sql':'SQL', '.sh':'Shell', '.vue':'Vue', '.html':'HTML', '.css':'CSS'}


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()


def init():
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT, metadata TEXT, overview TEXT);
        CREATE TABLE IF NOT EXISTS conversation_turns(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT REFERENCES projects(id) ON DELETE CASCADE, question TEXT, answer TEXT);
        CREATE TABLE IF NOT EXISTS sources(project_id TEXT REFERENCES projects(id) ON DELETE CASCADE, path TEXT, content TEXT, language TEXT, PRIMARY KEY(project_id,path));
        CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(project_id UNINDEXED, path, symbols, content, start_line UNINDEXED, end_line UNINDEXED, tokenize='porter unicode61');
        ''')


def symbols(text):
    patterns = [r'\b(?:def|class|interface|function|func|fn|struct|enum|trait)\s+(\w+)', r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^\n]*\)|\w+)\s*=>', r'\b(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\],?]+\s+(\w+)\s*\(']
    return sorted({m for pattern in patterns for m in re.findall(pattern, text)})


def unpack(data):
    if len(data) > MAX_ARCHIVE:
        raise ValueError('Archive exceeds configured size limit.')
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError('Upload a valid ZIP archive.')
    files, skipped = {}, []
    with archive:
        entries = archive.infolist()
        if len(entries) > 10000 or sum(x.file_size for x in entries) > 100 * 1024 * 1024:
            raise ValueError('Archive has too many entries or exceeds 100 MiB expanded.')
        names, seen = [], set()
        for item in entries:
            name = item.filename.replace('\\', '/')
            if name.startswith('/') or '..' in name.split('/') or ':' in name or '\0' in name:
                raise ValueError('Unsafe archive path.')
            path = str(PurePosixPath(name))
            if path in seen:
                raise ValueError('Duplicate archive path.')
            seen.add(path)
            if stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1:
                raise ValueError('Symlinks and encrypted entries are unsupported.')
            if not item.is_dir():
                names.append((item, path))
        roots = {p.split('/')[0] for _, p in names}
        strip_root = len(roots) == 1 and all('/' in p for _, p in names) and next(iter(roots)) not in EXCLUDED and not next(iter(roots)).startswith('.')
        for item, path in names:
            path = path.split('/', 1)[1] if strip_root else path
            parts = PurePosixPath(path).parts
            basename = parts[-1].lower()
            reason = None
            if any(p in EXCLUDED or p.startswith('.') for p in parts[:-1]):
                reason = 'excluded directory'
            elif basename.startswith('.') or basename.endswith(('.pem', '.key', '.p12')) or basename in {'credentials', 'credentials.json', 'secrets.json'}:
                reason = 'hidden or credential file'
            elif PurePosixPath(path).suffix.lower() in BINARY_EXT or '.min.' in basename or basename in {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'}:
                reason = 'generated or binary file'
            elif item.file_size > MAX_FILE:
                reason = 'file exceeds configured size limit'
            if reason:
                skipped.append({'path':path, 'reason':reason})
                continue
            raw = archive.read(item)
            try:
                text = raw.decode('utf-8-sig')
                if '\0' in text:
                    raise UnicodeError()
            except UnicodeError:
                skipped.append({'path':path, 'reason':'binary or non-UTF-8 text'})
                continue
            files[path] = text
            if len(files) > MAX_FILES:
                raise ValueError('Too many eligible files. Reduce the repository or increase MAX_SOURCE_FILES.')
    if not files:
        raise ValueError('No eligible UTF-8 source or documentation files found.')
    return files, skipped


def ingest(data, name, origin=None):
    files, skipped = unpack(data)
    project_id = uuid.uuid4().hex
    counts = {}
    for path in files:
        lang = LANGUAGES.get(PurePosixPath(path).suffix.lower(), 'Text/configuration')
        counts[lang] = counts.get(lang, 0) + 1
    metadata = {'id':project_id, 'name':name, 'file_count':len(files), 'total_lines':sum(len(x.splitlines()) for x in files.values()), 'languages':counts, 'skipped':skipped, 'origin':origin, 'sha256':hashlib.sha256(data).hexdigest()}
    with connect() as con:
        con.execute('DELETE FROM passages')
        con.execute('DELETE FROM projects')
        con.execute('INSERT INTO projects VALUES (?,?,?,NULL)', (project_id, name, json.dumps(metadata)))
        for path, content in files.items():
            language = LANGUAGES.get(PurePosixPath(path).suffix.lower(), 'Text/configuration')
            con.execute('INSERT INTO sources VALUES (?,?,?,?)', (project_id,path,content,language))
            lines = content.splitlines()
            for start in range(0, len(lines), 60):
                chunk = '\n'.join(lines[start:start+80])
                con.execute('INSERT INTO passages VALUES (?,?,?,?,?,?)', (project_id,path,' '.join(symbols(chunk)),chunk,start+1,min(start+80,len(lines))))
    return metadata


def project(project_id=None):
    with connect() as con:
        row = con.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone() if project_id else con.execute('SELECT * FROM projects LIMIT 1').fetchone()
    if not row:
        raise ValueError('Repository not found. Import a repository first.')
    value = json.loads(row['metadata'])
    value['overview'] = json.loads(row['overview']) if row['overview'] else None
    return value


def list_files(project_id, contains=''):
    with connect() as con:
        rows = con.execute('SELECT path,language FROM sources WHERE project_id=? ORDER BY path', (project_id,)).fetchall()
    return [dict(r) for r in rows if contains.lower() in r['path'].lower()]


def read(project_id, path, start=1, end=80):
    with connect() as con:
        row = con.execute('SELECT content FROM sources WHERE project_id=? AND path=?', (project_id,path)).fetchone()
    if not row:
        raise ValueError('File not found in this repository.')
    lines = row['content'].splitlines()
    if start < 1 or end < start or start > len(lines):
        raise ValueError('Invalid source line range.')
    end = min(end, len(lines), start+119)
    return {'file_path':path, 'start_line':start, 'end_line':end, 'snippet':'\n'.join(lines[start-1:end])}


def search(project_id, query, limit=8):
    stop = {'where','what','how','does','the','a','an','is','are','in','this','to','of','for','and','it','which','when','i','can'}
    tokens = [w for w in re.findall(r'[\w]+', query.lower()) if w not in stop][:24]
    if not tokens:
        return []
    expression = ' OR '.join('"'+w+'"*' for w in tokens)
    with connect() as con:
        rows = con.execute('''SELECT path AS file_path, content AS snippet, start_line,end_line,symbols,bm25(passages,0,4,6,1) AS score FROM passages WHERE passages MATCH ? AND project_id=? ORDER BY score LIMIT ?''', (expression,project_id,limit)).fetchall()
    return [dict(r, reason='Lexical match in source, path, or symbol names') for r in rows]


async def github_archive(url, branch=None):
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or len(parts) != 2 or parsed.query or parsed.fragment:
        raise ValueError('Use https://github.com/owner/repository and enter the branch separately.')
    owner, repo = parts[0], parts[1].removesuffix('.git')
    if not all(re.fullmatch(r'[A-Za-z0-9_.-]+', x) for x in (owner,repo)):
        raise ValueError('Invalid GitHub owner or repository.')
    async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
        base = f'https://api.github.com/repos/{owner}/{repo}'
        response = await client.get(base, headers={'Accept':'application/vnd.github+json'})
        response.raise_for_status()
        ref = branch or response.json()['default_branch']
        response = await client.get(base+'/commits/'+quote(ref,safe=''), headers={'Accept':'application/vnd.github+json'})
        response.raise_for_status()
        sha = response.json()['sha']
        if not re.fullmatch('[a-f0-9]{40}', sha):
            raise ValueError('Invalid commit returned by GitHub.')
        data = bytearray()
        async with client.stream('GET',f'https://codeload.github.com/{owner}/{repo}/zip/{sha}') as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_ARCHIVE:
                    raise ValueError('GitHub archive exceeds configured size limit.')
    return bytes(data), f'{owner}/{repo}', {'url':f'https://github.com/{owner}/{repo}', 'commit':sha, 'branch':ref}


def conversation(project_id, limit=30):
    project(project_id)
    with connect() as con:
        rows=con.execute('SELECT id,question,answer FROM conversation_turns WHERE project_id=? ORDER BY id DESC LIMIT ?', (project_id,limit)).fetchall()
    return [{'id':r['id'],'question':r['question'],'answer':json.loads(r['answer'])} for r in reversed(rows)]


def save_turn(project_id,question,answer):
    with connect() as con:
        cursor=con.execute('INSERT INTO conversation_turns(project_id,question,answer) VALUES (?,?,?)',(project_id,question,json.dumps(answer)))
    return {'id':cursor.lastrowid,'question':question,'answer':answer}


def clear_conversation(project_id):
    project(project_id)
    with connect() as con:
        con.execute('DELETE FROM conversation_turns WHERE project_id=?',(project_id,))
