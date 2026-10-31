import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.services import source_store as store
from app.services.explorer_agent import validate_output
from app.main import app


def archive(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for name,text in files.items():
            z.writestr(name,text)
    return out.getvalue()


@pytest.fixture
def db(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB_PATH',tmp_path/'test.db')
    store.init()


def test_full_source_and_mixed_root(db):
    p=store.ingest(archive({'README.md':'Example','app/main.ts':'const timeoutSetting = 30;\n'+'// padding\n'*100+'export function uniquetailmarker() {}','worker.go':'package main\nfunc processJob() {}'}),'mixed')
    assert store.search(p['id'],'uniquetailmarker')[0]['file_path']=='app/main.ts'
    assert store.search(p['id'],'timeoutSetting')
    assert store.search(p['id'],'processJob')
    result=store.search(p['id'],'uniquetailmarker')[0]
    assert result['snippet']==store.read(p['id'],result['file_path'],result['start_line'],result['end_line'])['snippet']


def test_exclusions_and_atomic_failure(db,monkeypatch):
    monkeypatch.setattr(store,'MAX_FILE',50)
    p=store.ingest(archive({'repo/main.js':'function hello() {}','repo/huge.py':'x'*51,'repo/node_modules/a.js':'secret','repo/.env':'KEY=secret'}),'safe')
    assert p['file_count']==1
    assert len(p['skipped'])==3
    with pytest.raises(ValueError):
        store.ingest(archive({'../escape.py':'bad'}),'bad')
    assert store.project()['id']==p['id']


def test_replacement_and_empty_search(db):
    p=store.ingest(archive({'a.py':'def old_symbol(): pass'}),'old')
    q=store.ingest(archive({'b.java':'class NewProject {}'}),'new')
    assert not store.search(q['id'],'old_symbol')
    assert not store.list_files(p['id'])
    assert not store.search(q['id'],'???')


def test_citation_rejection():
    with pytest.raises(ValueError):
        validate_output({'summary':'claim','findings':[{'evidence_ids':['invented']}], 'flows':[]},{'E1':{}})


def test_http_workflow(db):
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        r=client.post('/api/explorer/upload',files={'file':('demo.zip',archive({'index.js':'export function greet() { return "hello"; }'}),'application/zip')})
        assert r.status_code==200,r.text
        pid=r.json()['id']
        assert client.get(f'/api/explorer/{pid}/search',params={'q':'greet'}).json()
        assert client.get(f'/api/explorer/{pid}/source',params={'path':'../.env'}).status_code==404
        assert client.get('/api/explorer/status').json()['project']['id']==pid


@pytest.mark.parametrize('url',['http://github.com/a/b','https://localhost/a/b','https://github.com.evil/a/b','https://github.com/a/b/tree/main'])
def test_github_url_validation(url):
    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(store.github_archive(url))


def test_unknown_citation_in_valid_structure():
    with pytest.raises(ValueError,match='unsupported citations'):
        validate_output({'summary':'claim','findings':[{'title':'T','text':'Claim','basis':'source','evidence_ids':['E404']}], 'flows':[]},{'E1':{}})


def test_agent_workflow_caches_validated_overview(db,monkeypatch):
    import asyncio,json
    from types import SimpleNamespace
    from app.services import explorer_agent as agent
    p=store.ingest(archive({'main.js':'function greet() { return "hello"; }'}),'javascript')
    monkeypatch.setattr(agent,'FEATHERLESS_API_KEY','test-key')
    class FakeAgent:
        def __init__(self,**kwargs):
            assert len(kwargs['tools'])==3
        async def invoke_async(self,prompt):
            payload=json.loads(prompt)
            assert payload['initial_evidence'][0]['snippet'].startswith('function greet')
            return SimpleNamespace()
    async def fake_format(system,evidence,question):
        assert evidence['E1']['snippet'].startswith('function greet')
        return {'summary':'Greeting function','flows':[],'findings':[{'title':'Greeting','text':'Returns hello','basis':'source','evidence_ids':['E1']}]}
    monkeypatch.setattr(agent,'Agent',FakeAgent)
    monkeypatch.setattr(agent,'format_analysis',fake_format)
    result=asyncio.run(agent.analyze(p['id']))
    assert result['evidence']['E1']['start_line']==1
    assert store.project(p['id'])['overview']['summary']=='Greeting function'


def test_budget_stops_unbounded_exploration():
    from app.services.explorer_agent import Budget
    budget=Budget()
    for _ in range(6):budget.check(None)
    with pytest.raises(RuntimeError):budget.check(None)


def test_exploration_transitions_to_answer_after_three_rounds():
    from types import SimpleNamespace
    from app.services.explorer_agent import Budget
    budget=Budget()
    event=SimpleNamespace(end_turn=None)
    budget.finish(event)
    budget.finish(event)
    assert event.end_turn is None
    budget.finish(event)
    assert event.end_turn


def call_fixture():
    evidence = {
        'E1': {'file_path':'ui/client.ts','snippet':'function load() { return fetch("/pets"); }'},
        'E2': {'file_path':'api/main.rs','snippet':'#[get("/pets")] async fn pets() { repository.list().await }'},
    }
    output = {'summary':'Pets app','findings':[{'title':'Client','text':'Loads pets','basis':'source','evidence_ids':['E1']}],
              'flows':[{'title':'Load pets','basis':'source','steps':[
                  {'id':'ui','label':'Client','symbol':'load','file_path':'ui/client.ts','kind':'frontend','evidence_ids':['E1']},
                  {'id':'api','label':'Pets API','symbol':'pets','file_path':'api/main.rs','kind':'service','evidence_ids':['E2']}],
                  'connections':[{'source':'ui','target':'api','relation':'http','call':'fetch("/pets")','endpoint':'/pets','evidence_ids':['E1','E2']}]}]}
    return output,evidence


def test_implementation_call_evidence_retained():
    output,evidence=call_fixture()
    assert len(validate_output(output,evidence)['flows'][0]['connections'])==1


@pytest.mark.parametrize('failure',['readme','fabricated_call','missing_target','comment'])
def test_reject_unsubstantiated_dependency(failure):
    output,evidence=call_fixture()
    if failure=='readme':
        evidence['E1']['file_path']='README.md'
        output['flows'][0]['steps'][0]['file_path']='README.md'
    elif failure=='fabricated_call':
        output['flows'][0]['connections'][0]['call']='fetch("/payments")'
    elif failure=='missing_target':
        output['flows'][0]['connections'][0]['evidence_ids']=['E1']
    else:
        evidence['E1']['snippet']='// fetch("/pets")'
    result=validate_output(output,evidence)
    assert result['flows']==[]


def test_http_target_requires_matching_route():
    output,evidence=call_fixture()
    evidence['E2']['snippet']='#[get("/payments")] async fn payments() {}'
    assert validate_output(output,evidence)['flows']==[]


def test_non_call_identifier_does_not_create_dependency():
    output,evidence=call_fixture()
    output['flows'][0]['connections'][0].update(relation='reads',call='process.env.TABLE_NAME')
    evidence['E1']['snippet']='const table = process.env.TABLE_NAME;'
    assert validate_output(output,evidence)['flows']==[]


def test_dependency_schema_cannot_silently_accept_legacy_narrative_nodes():
    output,evidence=call_fixture()
    del output['flows'][0]['steps'][0]['id']
    with pytest.raises(ValueError,match='incomplete answer structure'):
        validate_output(output,evidence)


def test_formatter_explicitly_requests_summary_tool(monkeypatch):
    import asyncio,json
    from types import SimpleNamespace
    from app.services import explorer_agent as agent
    output,evidence=call_fixture()
    class Client:
        def __init__(self,**kwargs):
            self.chat=SimpleNamespace(completions=self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def create(self,**kwargs):
            assert kwargs['tool_choice']['function']['name']=='record_analysis'
            assert 'findings' in kwargs['tools'][0]['function']['parameters']['required']
            assert 'flows' not in kwargs['tools'][0]['function']['parameters']['properties']
            call=SimpleNamespace(function=SimpleNamespace(name='record_analysis',arguments=json.dumps(output)))
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])
    monkeypatch.setattr(agent,'AsyncOpenAI',Client)
    assert asyncio.run(agent.format_analysis('system',evidence))==output


def test_code_inventory_and_declaration_locations(db):
    from app.services.code_insights import insights
    p=store.ingest(archive({
        'README.md':'An example project with independent application packages for testing inventory.',
        'services/api/package.json':'{}',
        'services/api/index.ts':'// function imaginary() {}\nexport function actual() {}\nexport class Client {}\nconst run = () => 1;',
        'services/api/tests/main.test.ts':'function testActual() {}',
        'services/worker/go.mod':'module worker',
        'services/worker/main.go':'package main\nfunc process() {}\ntype Job struct {}',
        'node_modules/pkg/a.js':'function ignored() {}',
    }),'inventory')
    result=insights(p['id'])
    assert result['functions']==4
    assert result['test_files']==1
    assert result['skipped_files']==1
    assert result['passages']>0
    assert {c['name'] for c in result['components']}=={'api','worker'}
    symbol=next(s for s in result['symbols'] if s['name']=='actual')
    assert symbol['line']==2
    assert 'function actual' in store.read(p['id'],symbol['path'],2,2)['snippet']
    assert not any(s['name']=='imaginary' for s in result['symbols'])


def test_conversation_context_persistence_clear_and_failed_turn(db,monkeypatch):
    from app.routers import explorer
    p=store.ingest(archive({'main.py':'def hello(): pass'}),'chat')
    histories=[]
    async def fake_analyze(project_id,question,conversation):
        histories.append(conversation)
        if question=='fail':raise ValueError('Try again')
        return {'summary':question,'findings':[],'evidence':{}}
    monkeypatch.setattr(explorer,'analyze',fake_analyze)
    url=f'/api/explorer/{p["id"]}'
    with TestClient(app) as client:
        assert client.post(url+'/ask',json={'question':'What is hello?'}).status_code==200
        assert client.post(url+'/ask',json={'question':'What calls it?'}).status_code==200
        assert histories[0]==[]
        assert histories[1][0]['question']=='What is hello?'
        assert client.post(url+'/ask',json={'question':'fail'}).status_code==400
        assert len(client.get(url+'/conversation').json())==2
    with TestClient(app) as client:
        assert len(client.get(url+'/conversation').json())==2
        assert client.delete(url+'/conversation').status_code==200
        assert client.get(url+'/conversation').json()==[]
    store.save_turn(p['id'],'question',{'summary':'answer'})
    store.ingest(archive({'new.py':'x=1'}),'new')
    with store.connect() as con:
        assert con.execute('SELECT count(*) FROM conversation_turns').fetchone()[0]==0


def test_follow_up_rereads_evidence_and_bounds_history(db,monkeypatch):
    import asyncio,json
    from types import SimpleNamespace
    from app.services import explorer_agent as agent
    p=store.ingest(archive({'main.js':'function greet() { return "hello"; }'}),'followup')
    previous={'question':'greet','answer':{'summary':'Prior answer','findings':[], 'evidence':{'OLD':{'file_path':'main.js','start_line':1,'end_line':1,'snippet':'stale text'}}}}
    history=[previous]*8
    monkeypatch.setattr(agent,'FEATHERLESS_API_KEY','test-key')
    class FakeAgent:
        def __init__(self,**kwargs):pass
        async def invoke_async(self,prompt):
            data=json.loads(prompt)
            assert len(data['conversation'])==6
            assert all(e['snippet']!='stale text' for e in data['initial_evidence'])
            return SimpleNamespace()
    async def fake_format(system,evidence,question,conversation):
        assert len(conversation)==6
        assert 'OLD' not in evidence
        assert evidence['E1']['snippet'].startswith('function greet')
        return {'summary':'Returns hello','findings':[{'title':'Greeting','text':'Returns hello','basis':'source','evidence_ids':['E1']}], 'flows':[]}
    monkeypatch.setattr(agent,'Agent',FakeAgent)
    monkeypatch.setattr(agent,'format_analysis',fake_format)
    result=asyncio.run(agent.analyze(p['id'],'What does it return?',history))
    assert result['evidence']['E1']['file_path']=='main.js'
    assert store.project(p['id'])['overview'] is None


@pytest.mark.parametrize('first',[
    {'summary':'Partial','findings':[{'text':'A greeting','evidence_ids':['E1']}]},
    {'summary':'Wrong citation','findings':[{'title':'Greeting','text':'A greeting','evidence_ids':['invented'],'basis':'source'}]},
    [], None,
])
def test_formatter_recovers_with_json_mode(monkeypatch,first):
    import asyncio,json
    from types import SimpleNamespace as NS
    from app.services import explorer_agent as agent
    output={'summary':'A greeting','findings':[{'title':'Greeting','text':'Returns hello','evidence_ids':['E1'],'basis':'source'}],'limitations':[]}
    requests=[]
    class Client:
        def __init__(self,**kwargs):self.chat=NS(completions=self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def create(self,**kwargs):
            requests.append(kwargs)
            if len(requests)==1:
                assert '$ref' not in json.dumps(kwargs['tools'])
                return NS(choices=[NS(message=NS(tool_calls=[NS(function=NS(name='record_analysis',arguments=json.dumps(first)))],content=None))])
            assert kwargs['response_format']=={'type':'json_object'}
            assert 'tools' not in kwargs
            assert 'validation_error' in kwargs['messages'][-1]['content']
            return NS(choices=[NS(message=NS(content=json.dumps(output),tool_calls=[]))])
    monkeypatch.setattr(agent,'AsyncOpenAI',Client)
    result=asyncio.run(agent.format_analysis('system',{'E1':{'snippet':'return "hello";'}}))
    assert result['summary']=='A greeting'
    assert len(requests)==2


def test_formatter_does_not_accept_unsupported_citations_after_retry(monkeypatch):
    import asyncio,json
    from types import SimpleNamespace as NS
    from app.services import explorer_agent as agent
    output={'summary':'Claim','findings':[{'title':'Claim','text':'Unsupported','evidence_ids':['E99'],'basis':'source'}]}
    class Client:
        def __init__(self,**kwargs):self.chat=NS(completions=self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def create(self,**kwargs):return NS(choices=[NS(message=NS(content=json.dumps(output),tool_calls=[]))])
    monkeypatch.setattr(agent,'AsyncOpenAI',Client)
    with pytest.raises(ValueError,match='unsupported citations'):
        asyncio.run(agent.format_analysis('system',{'E1':{}}))


def test_formatter_empty_evidence_returns_honest_no_match():
    import asyncio
    from app.services.explorer_agent import format_analysis
    result=asyncio.run(format_analysis('system',{},'unknown'))
    assert result['findings']==[]
    assert 'could not find source evidence' in result['summary']


def test_formatter_unwraps_provider_properties_without_inventing_fields():
    import json
    from app.services.explorer_agent import parse_analysis,check_analysis
    answer={'summary':'Returns hello','findings':[{'title':'Greeting','text':'Returns hello','evidence_ids':['E1'],'basis':'source'}],'limitations':[]}
    parsed=parse_analysis(json.dumps({'properties':answer}))
    assert check_analysis(parsed,{'E1':{}})['summary']=='Returns hello'
    parsed['findings'][0]['evidence_ids']=['invented']
    with pytest.raises(ValueError,match='unsupported citations'):check_analysis(parsed,{'E1':{}})
    schema={'properties':{'summary':{'type':'string'},'findings':{'type':'array'}}}
    assert parse_analysis(json.dumps(schema))==schema


def test_explain_selection_validates_and_forwards_source(db,monkeypatch):
    from app.routers import explorer
    p=store.ingest(archive({'main.py':'first = 1\nsecond = 2\nthird = 3'}),'selection')
    received=[]
    async def fake_analyze(project_id,question,**options):
        received.append(options['source_context'])
        return {'summary':'Selected code','findings':[],'evidence':{}}
    monkeypatch.setattr(explorer,'analyze',fake_analyze)
    with TestClient(app) as client:
        url=f'/api/explorer/{p["id"]}/ask'
        selected={'path':'main.py','start':2,'end':3}
        assert client.post(url,json={'question':'Explain this','source':selected}).status_code==200
        assert received==[selected]
        for bad in [{'path':'missing.py','start':1,'end':2},{'path':'main.py','start':3,'end':2},{'path':'main.py','start':1,'end':121}]:
            assert client.post(url,json={'question':'Explain this','source':bad}).status_code==400
        assert len(received)==1


def test_selected_source_is_first_evidence(db,monkeypatch):
    import asyncio,json
    from types import SimpleNamespace
    from app.services import explorer_agent as agent
    p=store.ingest(archive({'main.py':'first = 1\nsecond = 2\nthird = 3'}),'selection')
    monkeypatch.setattr(agent,'FEATHERLESS_API_KEY','test-key')
    class FakeAgent:
        def __init__(self,**kwargs):pass
        async def invoke_async(self,prompt):
            payload=json.loads(prompt)
            assert payload['selected_source']['start']==2
            assert payload['initial_evidence'][0]['snippet']=='second = 2\nthird = 3'
            return SimpleNamespace()
    async def fake_format(system,evidence,question):
        assert evidence['E1']['start_line']==2
        return {'summary':'Two assignments','findings':[{'title':'Assignments','text':'Sets two values','basis':'source','evidence_ids':['E1']}],'flows':[]}
    monkeypatch.setattr(agent,'Agent',FakeAgent)
    monkeypatch.setattr(agent,'format_analysis',fake_format)
    result=asyncio.run(agent.analyze(p['id'],'Explain this',source_context={'path':'main.py','start':2,'end':3}))
    assert result['evidence']['E1']['end_line']==3
