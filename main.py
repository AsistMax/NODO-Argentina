from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI(title="NODO Argentina V12 107% - Final Bueno")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.isdir("bloque1"):
    app.mount("/bloque1", StaticFiles(directory="bloque1", html=True), name="bloque1")
if os.path.isdir("bloque2"):
    app.mount("/bloque2", StaticFiles(directory="bloque2", html=True), name="bloque2")
if os.path.isdir("bloque3"):
    app.mount("/bloque3", StaticFiles(directory="bloque3", html=True), name="bloque3")

def render_template(name, request):
    template = templates.get_template(name)
    return HTMLResponse(template.render({"request": request}))

@app.get("/health")
def health():
    has_supabase = bool(os.getenv("SUPABASE_URL"))
    return {"status": "OK 107%", "bloques": ["/bloque1", "/bloque2", "/bloque3"], "supabase": has_supabase}

@app.get("/")
def root():
    return RedirectResponse(url="/bloque1")

@app.get("/app", response_class=HTMLResponse)
async def app_redirect(request: Request):
    return RedirectResponse(url="/bloque1")
