"""Cookie-based user routes; passwords are sent only to Supabase Auth."""
import secrets
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class PasswordLogin(StrictModel):
    email: str = Field(min_length=3, max_length=254,
                       pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=8, max_length=1024)


class School(StrictModel):
    name: str = Field(min_length=1, max_length=200)


class UserChange(StrictModel):
    role: Literal['student', 'teacher', 'manager', 'admin'] | None
    school_id: UUID | None
    status: Literal['pending', 'approved', 'disabled']


class DeviceSchool(StrictModel):
    school_id: UUID | None


class Roster(StrictModel):
    student_ids: list[UUID] = Field(min_length=1, max_length=200)
    device_ids: list[UUID] = Field(min_length=1, max_length=200)


class SessionCreate(Roster):
    school_id: UUID
    name: str = Field(min_length=1, max_length=200)


def install_user_routes(app, repository, auth, *, cookie_secure=True, public_origin=None):
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # FastAPI's default error response can echo an invalid password input.
        return JSONResponse({'detail': 'Invalid request fields'}, status_code=422)

    @app.middleware('http')
    async def browser_security(request: Request, call_next):
        path = request.url.path
        if path.startswith('/v1/') and path != '/v1/telemetry' and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            expected = public_origin or str(request.base_url).rstrip('/')
            if origin is not None and origin != expected:
                return JSONResponse({'detail': 'Invalid request origin'}, status_code=403)
            cookie = request.cookies.get('tlm_csrf', '')
            token = request.headers.get('x-csrf-token', '')
            if not cookie or not secrets.compare_digest(cookie, token):
                return JSONResponse({'detail': 'CSRF token required'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        return response

    def csrf(response):
        response.set_cookie('tlm_csrf', secrets.token_urlsafe(32), secure=cookie_secure,
                            httponly=False, samesite='strict', path='/')

    def cookies(response, data):
        if not data.get('access_token') or not data.get('refresh_token'):
            raise HTTPException(
                503, 'Auth pilot must have email confirmation disabled')
        response.set_cookie('tlm_access', data['access_token'], httponly=True, secure=cookie_secure,
                            samesite='strict', path='/', max_age=int(data.get('expires_in', 3600)))
        response.set_cookie('tlm_refresh', data['refresh_token'], httponly=True, secure=cookie_secure,
                            samesite='strict', path='/', max_age=30*24*3600)
        csrf(response)

    async def actor(request):
        return await auth.get_user(request.cookies.get('tlm_access'))

    async def invoke(request, method, *args):
        uid = await actor(request)
        return await run_in_threadpool(method, uid, *args)

    @app.get('/v1/auth/csrf')
    def bootstrap(response: Response):
        csrf(response)
        return {'status': 'ready'}

    @app.post('/v1/auth/register', status_code=201)
    async def register(data: PasswordLogin, response: Response):
        session = await auth.register(data.email, data.password)
        uid = await auth.get_user(session.get('access_token'))
        profile = await run_in_threadpool(repository.profile, uid)
        cookies(response, session)
        return profile

    @app.post('/v1/auth/login')
    async def login(data: PasswordLogin, response: Response):
        session = await auth.login(data.email, data.password)
        uid = await auth.get_user(session.get('access_token'))
        profile = await run_in_threadpool(repository.profile, uid)
        cookies(response, session)
        return profile

    @app.post('/v1/auth/refresh')
    async def refresh(request: Request, response: Response):
        token = request.cookies.get('tlm_refresh')
        if not token:
            raise HTTPException(401, 'Refresh session required')
        session = await auth.refresh(token)
        await auth.get_user(session.get('access_token'))
        cookies(response, session)
        return {'status': 'refreshed'}

    @app.post('/v1/auth/logout')
    async def logout(request: Request):
        try:
            token = request.cookies.get('tlm_access')
            try:
                await auth.get_user(token)
            except HTTPException as error:
                if error.status_code != 401:
                    raise
                refresh_token = request.cookies.get('tlm_refresh')
                if not refresh_token:
                    raise
                token = (await auth.refresh(refresh_token))['access_token']
            await auth.logout(token)
            response = JSONResponse({'status': 'logged_out'})
        except HTTPException as error:
            # Clear the browser even if the provider is unavailable; report that
            # remote revocation did not succeed so it is never silently claimed.
            response = JSONResponse(
                {'detail': error.detail}, status_code=error.status_code)
        for name in ('tlm_access', 'tlm_refresh', 'tlm_csrf'):
            response.delete_cookie(
                name, path='/', secure=cookie_secure, httponly=name != 'tlm_csrf', samesite='strict')
        return response

    @app.get('/v1/auth/me')
    async def me(request: Request):
        return await invoke(request, repository.profile)

    @app.get('/v1/admin/schools')
    async def schools(request: Request):
        return await invoke(request, repository.schools)

    @app.post('/v1/admin/schools', status_code=201)
    async def school(data: School, request: Request):
        return await invoke(request, repository.schools, data.name)

    @app.get('/v1/admin/users')
    async def users(request: Request):
        return await invoke(request, repository.users)

    @app.patch('/v1/admin/users/{user_id}')
    async def user(user_id: UUID, data: UserChange, request: Request):
        return await invoke(request, repository.users, user_id, data)

    @app.get('/v1/admin/devices')
    async def devices(request: Request):
        return await invoke(request, repository.devices)

    @app.patch('/v1/admin/devices/{device_id}')
    async def device(device_id: UUID, data: DeviceSchool, request: Request):
        return await invoke(request, repository.devices, device_id, data.school_id)

    @app.get('/v1/sessions/options')
    async def options(request: Request):
        return await invoke(request, repository.options)

    @app.get('/v1/sessions')
    async def sessions(request: Request):
        return await invoke(request, repository.sessions)

    @app.post('/v1/sessions', status_code=201)
    async def session(data: SessionCreate, request: Request):
        return await invoke(request, repository.create_session, data)

    @app.put('/v1/sessions/{session_id}/roster')
    async def roster(session_id: UUID, data: Roster, request: Request):
        return await invoke(request, repository.roster, session_id, data)

    @app.post('/v1/sessions/{session_id}/start')
    async def start(session_id: UUID, request: Request):
        return await invoke(request, repository.transition, session_id, 'start')

    @app.post('/v1/sessions/{session_id}/finish')
    async def finish(session_id: UUID, request: Request):
        return await invoke(request, repository.transition, session_id, 'finish')

    @app.get('/v1/sessions/{session_id}/telemetry')
    async def history(session_id: UUID, request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=2147483647)):
        return await invoke(request, repository.telemetry, session_id, limit, offset)

    @app.get('/v1/telemetry')
    async def telemetry(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=2147483647)):
        return await invoke(request, repository.telemetry, None, limit, offset)

    assets = Path(__file__).with_name('dashboard')
    app.mount('/assets', StaticFiles(directory=assets), name='assets')

    @app.get('/', include_in_schema=False)
    def dashboard():
        return FileResponse(assets/'index.html')
