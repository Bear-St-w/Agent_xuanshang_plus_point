#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
悬赏终端 · Bounty Terminal
=========================
一个独立的悬赏看板：当前悬赏 / 排行榜 / 赏金猎人墙 / 发布悬赏。

它是「工作台」(D:\\工作台\\app.py) 的**只读镜像 + 发布代理**：
  · 读  GET  {WORKBENCH}/api/bounty
  · 发  POST {WORKBENCH}/api/bounty          {"act":"set", ...} / {"act":"clear"}
  · 抢  POST {WORKBENCH}/站长_to_all_悬赏    {"who": "..."}

启动：  python app.py
端口：  DSH_XS_PORT  (默认 6001；6000 被 Chromium 封锁不能用)

原作者：Bear-St-w   ·   MIT
"""
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WORKBENCH = os.environ.get('DSH_XS_WORKBENCH', 'http://127.0.0.1:5001').rstrip('/')
BOUNTY_PATH = os.environ.get('DSH_XS_BOUNTY_PATH', '/api/bounty')
GRAB_PATH = os.environ.get('DSH_XS_GRAB_PATH', '/站长_to_all_悬赏')
PORT = int(os.environ.get('DSH_XS_PORT', '6001'))
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(HERE, 'index.html')


def _http(method, path, payload=None, timeout=6):
    url = WORKBENCH + path
    data = None
    headers = {'Accept': 'application/json'}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json; charset=utf-8'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', 'replace')
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, {'ok': False, 'error': '上游返回的不是 JSON', 'raw': body[:400]}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {'ok': False, 'error': '上游 HTTP %d' % e.code}
    except urllib.error.URLError as e:
        return 502, {'ok': False, 'error': '连不上工作台：%s' % e.reason}
    except Exception as e:
        return 500, {'ok': False, 'error': str(e)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _body(self):
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode('utf-8', 'replace') or '{}')
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            try:
                with open(INDEX_HTML, 'rb') as f:
                    self._send(200, f.read(), 'text/html; charset=utf-8')
            except FileNotFoundError:
                self._send(500, 'index.html 缺失', 'text/plain; charset=utf-8')
            return
        if self.path == '/api/bounty':
            code, out = _http('GET', BOUNTY_PATH)
            self._json(200 if code == 200 else 502, out)
            return
        if self.path == '/api/meta':
            self._json(200, {'ok': True, 'workbench': WORKBENCH,
                             'time': time.time(), 'server': 'bounty-terminal'})
            return
        self._json(404, {'ok': False, 'error': 'not found'})

    def do_POST(self):
        if self.path == '/api/bounty':
            body = self._body()
            code, out = _http('POST', BOUNTY_PATH, body)
            self._json(code if code >= 400 else 200, out)
            return
        if self.path == '/api/grab':
            body = self._body()
            code, out = _http('POST', GRAB_PATH, body)
            self._json(code if code >= 400 else 200, out)
            return
        self._json(404, {'ok': False, 'error': 'not found'})


def main():
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print('  悬赏终端  http://127.0.0.1:%d' % PORT)
    print('  工作台    %s' % WORKBENCH)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n  已停止')
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
