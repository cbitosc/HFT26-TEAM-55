import asyncio

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from app.services import source_store as store
from app.services.explorer_agent import analyze

router = APIRouter(prefix='/api/explorer', tags=['explorer'])
operation_lock = asyncio.Lock()


class GitHubRequest(BaseModel):
    url: str = Field(max_length=500)
    branch: str | None = Field(default=None,max_length=200)


class SourceSelection(BaseModel):
    path: str = Field(min_length=1,max_length=1000)
    start: int = Field(ge=1)
    end: int = Field(ge=1)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=2,max_length=1500)
    source: SourceSelection | None = None


async def exclusive(action):
    if operation_lock.locked():
        raise HTTPException(409,'Another import or AI analysis is running. Wait for it to finish.')
    async with operation_lock:
        try:
            return await action()
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(400,str(exc)) from exc
        except (TimeoutError,asyncio.TimeoutError):
            raise HTTPException(504,'Analysis timed out. Source search remains available; retry with a narrower question.')
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502,f'GitHub returned HTTP {exc.response.status_code}. Check the public URL, branch, or rate limit.') from exc
        except Exception:
            raise HTTPException(502,'Provider or network request failed. Check Featherless model availability, API key, and tool-calling support.')


@router.get('/status')
def status():
    from app.config import FEATHERLESS_API_KEY, FEATHERLESS_AGENT_MODEL
    import os
    try:
        project = store.project()
    except ValueError:
        project = None
    return {'project':project,'ai_configured':bool(FEATHERLESS_API_KEY.strip()),'model':FEATHERLESS_AGENT_MODEL}


@router.post('/upload')
async def upload(file: UploadFile = File(...)):
    async def action():
        data = bytearray()
        while chunk := await file.read(65536):
            data.extend(chunk)
            if len(data) > store.MAX_ARCHIVE:
                raise ValueError('Archive exceeds configured size limit.')
        return await run_in_threadpool(store.ingest,bytes(data),file.filename or 'repository.zip')
    try:
        return await exclusive(action)
    finally:
        await file.close()


@router.post('/github')
async def github(request: GitHubRequest):
    async def action():
        data,name,origin = await store.github_archive(request.url,request.branch)
        return await run_in_threadpool(store.ingest,data,name,origin)
    return await exclusive(action)


@router.get('/{project_id}/files')
def files(project_id: str, contains: str = ''):
    return store.list_files(project_id,contains)


@router.get('/{project_id}/search')
def search(project_id: str, q: str = ''):
    return store.search(project_id,q[:1500])


@router.get('/{project_id}/source')
def source(project_id: str, path: str, start: int = 1, end: int = 80):
    try:
        return store.read(project_id,path,start,end)
    except ValueError as exc:
        raise HTTPException(404,str(exc))


@router.post('/{project_id}/overview')
async def overview(project_id: str):
    return await exclusive(lambda: analyze(project_id))


@router.post('/{project_id}/ask')
async def ask(project_id: str, request: QuestionRequest):
    async def action():
        history=store.conversation(project_id,6)
        options={'conversation':history}
        if request.source:
            source=request.source.model_dump()
            if source['end'] < source['start'] or source['end']-source['start']>=120:
                raise ValueError('Select between 1 and 120 source lines.')
            store.read(project_id,source['path'],source['start'],source['end'])
            options['source_context']=source
        result=await analyze(project_id,request.question,**options)
        turn=store.save_turn(project_id,request.question,result)
        return dict(result,turn_id=turn['id'])
    return await exclusive(action)


@router.get('/{project_id}/insights')
def insights(project_id: str):
    from app.services.code_insights import insights as inspect
    try:
        return inspect(project_id)
    except ValueError as exc:
        raise HTTPException(404,str(exc)) from exc


@router.get('/{project_id}/conversation')
def conversation(project_id: str):
    try:
        return store.conversation(project_id)
    except ValueError as exc:
        raise HTTPException(404,str(exc)) from exc


@router.delete('/{project_id}/conversation')
async def clear_conversation(project_id: str):
    async def action():
        store.clear_conversation(project_id)
        return {'cleared':True}
    return await exclusive(action)
