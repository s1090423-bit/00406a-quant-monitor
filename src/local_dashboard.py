"""Local-only live dashboard: downloads latest successful GitHub Actions artifact."""
import http.server
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from dashboard import render
from engine import load_prices

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"output"/"live"
REPO="s1090423-bit/00406a-quant-monitor"
GH=Path.home()/".local/bin/gh"
CACHE={"updated":0,"run_id":None,"error":None}
LOCK=threading.Lock()

def refresh():
    with LOCK:
        if time.time()-CACHE["updated"]<240 and (OUT/"index.html").exists():
            return
        try:
            raw=subprocess.check_output([str(GH),"run","list","--repo",REPO,
                "--workflow","monitor.yml","--limit","8","--json","databaseId,conclusion,status"],
                text=True,timeout=25)
            runs=json.loads(raw)
            latest=next((r for r in runs if r.get("conclusion")=="success"),None)
            if not latest:
                raise RuntimeError("沒有可下載的成功執行紀錄")
            rid=latest["databaseId"]
            if rid!=CACHE["run_id"] or not (OUT/"index.html").exists():
                with tempfile.TemporaryDirectory() as temp:
                    subprocess.run([str(GH),"run","download",str(rid),"--repo",REPO,
                        "--dir",temp],check=True,capture_output=True,text=True,timeout=75)
                    files=list(Path(temp).rglob("latest.json"))
                    if not files: raise RuntimeError("缺少最新訊號檔案")
                    folder=files[0].parent
                    signal=json.loads((folder/"latest.json").read_text())
                    research=json.loads((folder/"research.json").read_text())
                    prices=load_prices(folder/"prices.csv") if (folder/"prices.csv").exists() else None
                    OUT.mkdir(parents=True,exist_ok=True)
                    (OUT/"index.html").write_text(render(signal,research,prices),encoding="utf-8")
                    (OUT/"latest.json").write_text(json.dumps(signal,ensure_ascii=False,indent=2))
                    (OUT/"research.json").write_text(json.dumps(research,ensure_ascii=False,indent=2))
                CACHE["run_id"]=rid
            CACHE["error"]=None
            CACHE["updated"]=time.time()
        except Exception as e:
            CACHE["error"]=str(e)
            CACHE["updated"]=time.time()
            if not (OUT/"index.html").exists():
                OUT.mkdir(parents=True,exist_ok=True)
                (OUT/"index.html").write_text("<html lang='zh-Hant'><meta charset='utf-8'><h1>資料暫時無法更新</h1><p>請稍後重新整理，或檢查 GitHub Actions。</p></html>")

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/status.json":
            data=json.dumps(CACHE,ensure_ascii=False).encode()
            self.send_response(200);self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data);return
        if path not in ("/","/index.html"):
            self.send_error(404);return
        refresh()
        page=(OUT/"index.html").read_text(encoding="utf-8")
        banner="<div style='font:14px sans-serif;padding:10px 16px;background:#eaf2ff;color:#163b6c;text-align:center'>本機自動更新：每5分鐘檢查 GitHub 最新成功報告；資料仍可能延遲。<a href='/'>手動更新</a></div>"
        if CACHE["error"]:
            banner="<div style='padding:12px;background:#fff2d8;color:#703b00'>更新失敗，顯示上次成功報告："+CACHE["error"].replace("<","&lt;")+"</div>"+banner
        page=page.replace("<body>","<body>"+banner+"<script>setTimeout(()=>location.reload(),300000)</script>",1)
        data=page.encode()
        self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
    def log_message(self,*args): pass

if __name__=="__main__":
    server=http.server.ThreadingHTTPServer(("127.0.0.1",8765),Handler)
    print("Dashboard: http://127.0.0.1:8765",flush=True)
    server.serve_forever()
