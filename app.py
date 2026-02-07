"""
FastAPI app for Vercel deployment.
Handles auth and read-log API only. Static files served from public/ by Vercel.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from auth import (
    SESSION_COOKIE,
    get_log,
    login as auth_login,
    logout as auth_logout,
    register as auth_register,
    save_log,
    verify_session,
)

app = FastAPI(title="Random Technical Wiki API", version="1.0.0")


@app.post("/api/register")
async def api_register(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    err = auth_register(username, password)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return JSONResponse({"ok": True})


@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    session_id = auth_login(username, password)
    if not session_id:
        return JSONResponse({"error": "Invalid username or password"}, status_code=401)
    response = JSONResponse({"ok": True, "username": username})
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@app.post("/api/logout")
async def api_logout(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    auth_logout(session_id)
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/api/me")
async def api_me(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    username = verify_session(session_id)
    if not username:
        return JSONResponse({"username": None})
    return JSONResponse({"username": username})


@app.get("/api/read-log")
async def api_get_read_log(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    username = verify_session(session_id)
    if not username:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    log = get_log(username)
    return JSONResponse({"log": log})


@app.post("/api/read-log")
async def api_save_read_log(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    username = verify_session(session_id)
    if not username:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    body = await request.json()
    log = body.get("log", [])
    if not isinstance(log, list):
        return JSONResponse({"error": "Invalid log"}, status_code=400)
    save_log(username, log)
    return JSONResponse({"ok": True})
