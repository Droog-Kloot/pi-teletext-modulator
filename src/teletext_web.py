#!/usr/bin/env python3
"""LAN TTI file manager. Python 3 standard library only."""
import base64
import hashlib
import hmac
import html
import os
from pathlib import Path
import re
import secrets
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit
from email.parser import BytesParser
from email.policy import default

PAGES = Path(os.environ.get('TTI_PAGES_DIR', '/home/admin/raspi5-teletext/pages')).resolve()
USER = os.environ.get('TTI_WEB_USER', 'admin')
PASSWORD = os.environ.get('TTI_WEB_PASSWORD', '')
HOST = os.environ.get('TTI_WEB_HOST', '0.0.0.0')
PORT = int(os.environ.get('TTI_WEB_PORT', '8080'))
MAX_BODY = 2 * 1024 * 1024
TOKEN = secrets.token_urlsafe(32)
CSS = '''body{font:16px system-ui,sans-serif;background:#111827;color:#f3f4f6;max-width:1000px;margin:30px auto;padding:0 16px}a{color:#93c5fd}header{display:flex;justify-content:space-between;align-items:center;gap:12px}main,.panel{background:#1f2937;border-radius:12px;padding:20px;margin:18px 0}button,input[type=submit]{background:#2563eb;color:white;border:0;border-radius:6px;padding:9px 13px;cursor:pointer}input[type=file],textarea{max-width:100%}textarea{box-sizing:border-box;width:100%;height:60vh;background:#030712;color:#e5e7eb;font:14px monospace;padding:12px;border:1px solid #4b5563}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:10px;border-bottom:1px solid #374151}form.inline{display:inline}small{color:#9ca3af}.danger{background:#b91c1c}.notice{background:#064e3b;padding:12px;border-radius:8px}'''

def safe_name(name):
    name = name.replace('\\', '/')
    if '/' in name or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.tti', name, re.I):
        raise ValueError('Ongeldige bestandsnaam; gebruik letters, cijfers, _ of -.')
    return name

def target(name):
    p = PAGES / safe_name(name)
    if p.is_symlink() or (p.exists() and not p.is_file()):
        raise ValueError('Ongeldig bestandstype')
    return p

def atomic_write(path, content):
    fd, tmp = tempfile.mkstemp(prefix='.tti-upload-', dir=PAGES)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

class Handler(BaseHTTPRequestHandler):
    def send_html(self, body, status=200):
        raw = ('<!doctype html><html lang="nl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Teletext beheer</title><style>'+CSS+'</style><body><header><h1>📺 Teletext beheer</h1><a href="/">Alle pagina’s</a></header>'+body+'</body></html>').encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(raw)

    def auth(self):
        expected = 'Basic ' + base64.b64encode(f'{USER}:{PASSWORD}'.encode()).decode()
        if PASSWORD and hmac.compare_digest(self.headers.get('Authorization', ''), expected):
            return True
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Teletext beheer", charset="UTF-8"')
        self.send_header('Content-Length', '0')
        self.end_headers()
        return False

    def token_input(self):
        return '<input type="hidden" name="token" value="'+TOKEN+'">'

    def do_GET(self):
        if not self.auth(): return
        route = urlsplit(self.path)
        if route.path == '/':
            rows = []
            for p in sorted(PAGES.iterdir(), key=lambda x:x.name.lower()):
                if p.is_file() and not p.is_symlink() and p.suffix.lower() == '.tti':
                    name = html.escape(p.name)
                    rows.append(f'<tr><td>{name}</td><td>{p.stat().st_size} bytes</td><td><a href="/edit?name={quote(p.name)}">Bekijken / bewerken</a></td></tr>')
            self.send_html('<main><h2>Pagina’s</h2><table><tr><th>Bestand</th><th>Grootte</th><th>Actie</th></tr>'+''.join(rows)+'</table>'+('' if rows else '<p>Er zijn nog geen TTI-bestanden.</p>')+'</main><div class="panel"><h2>TTI uploaden</h2><form method="post" action="/upload" enctype="multipart/form-data">'+self.token_input()+'<input type="file" name="tti" accept=".tti" required> <button>Uploaden</button></form><p><small>Maximaal 2 MB per upload. Een bestaand bestand met dezelfde naam wordt vervangen.</small></p></div>')
        elif route.path == '/edit':
            try:
                name = parse_qs(route.query).get('name', [''])[0]
                p = target(name)
                if not p.is_file(): raise ValueError('Bestand bestaat niet')
                data = p.read_bytes()
                if len(data) > MAX_BODY: raise ValueError('Bestand is te groot')
                content = data.decode('latin-1')
                safe = html.escape(p.name)
                self.send_html('<main><h2>'+safe+'</h2><p><small>Tekstweergave volgens Latin-1; speciale TTI-besturingscodes kunnen onzichtbaar zijn. Bewerk alleen als je het formaat kent.</small></p><form method="post" action="/save">'+self.token_input()+'<input type="hidden" name="name" value="'+safe+'"><textarea name="content" spellcheck="false">'+html.escape(content)+'</textarea><p><button>Opslaan</button></p></form><form method="post" action="/delete" onsubmit="return confirm(\'Deze pagina echt verwijderen?\')">'+self.token_input()+'<input type="hidden" name="name" value="'+safe+'"><button class="danger">Verwijderen</button></form></main>')
            except (ValueError, OSError) as e: self.send_html('<main>'+html.escape(str(e))+'</main>', 404)
        else: self.send_html('<main>Niet gevonden</main>', 404)

    def do_POST(self):
        if not self.auth(): return
        # Refuse cross-origin browser form submissions; CSRF token is also required.
        origin = self.headers.get('Origin')
        if origin:
            host = self.headers.get('Host', '')
            if urlsplit(origin).netloc != host or urlsplit(origin).scheme != 'http':
                self.send_html('<main>Ongeldige herkomst</main>', 403); return
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if not 0 < n <= MAX_BODY: raise ValueError('Upload of formulier te groot (max 2 MB)')
            raw = self.rfile.read(n)
            ctype = self.headers.get('Content-Type', '')
            if self.path == '/upload':
                if not ctype.lower().startswith('multipart/form-data;'):
                    raise ValueError('Upload moet multipart/form-data zijn')
                message = BytesParser(policy=default).parsebytes(('Content-Type: '+ctype+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
                fields = {part.get_param('name', header='content-disposition'):part for part in message.iter_parts()}
                if not hmac.compare_digest(str(fields['token'].get_content()).strip(), TOKEN): raise ValueError('Ongeldige sessietoken')
                part = fields['tti']
                filename = part.get_filename()
                if not filename: raise ValueError('Geen bestand geselecteerd')
                data = part.get_payload(decode=True)
                if not data: raise ValueError('Leeg bestand')
                p = target(filename)
                atomic_write(p, data)
                result = 'Geüpload: '+p.name
            elif self.path in ('/save', '/delete'):
                if not ctype.lower().startswith('application/x-www-form-urlencoded'):
                    raise ValueError('Ongeldig formulier')
                fields = parse_qs(raw.decode('utf-8'), keep_blank_values=True)
                if not hmac.compare_digest(fields.get('token', [''])[0], TOKEN): raise ValueError('Ongeldige sessietoken')
                p = target(fields.get('name', [''])[0])
                if not p.is_file(): raise ValueError('Bestand bestaat niet')
                if self.path == '/delete':
                    p.unlink()
                    result = 'Verwijderd: '+p.name
                else:
                    content = fields.get('content', [''])[0].encode('latin-1')
                    atomic_write(p, content)
                    result = 'Opgeslagen: '+p.name
            else: self.send_html('<main>Niet gevonden</main>', 404); return
            self.send_html('<main><div class="notice">'+html.escape(result)+'</div><p><a href="/">Terug naar overzicht</a></p></main>')
        except (ValueError, KeyError, UnicodeError, OSError) as e:
            self.send_html('<main>Fout: '+html.escape(str(e))+'</main>', 400)

if __name__ == '__main__':
    if not PASSWORD:
        raise SystemExit('Stel TTI_WEB_PASSWORD in via de systemd EnvironmentFile.')
    PAGES.mkdir(parents=True, exist_ok=True)
    print(f'Teletext webbeheer: http://{HOST}:{PORT} ; map {PAGES}', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()