"""Build, verify or serve the portable Phase 5 viewer without ML dependencies."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from anytime_ncm.viewer import build, verify, OUT


def serve(root, port):
    """Only the portable artifact is served; no arbitrary repository browsing."""
    document = (root/OUT/"viewer.html").read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/","/viewer.html"):
                self.send_error(404);return
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(document)))
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Cache-Control","no-store")
            self.end_headers();self.wfile.write(document)
        def log_message(self,*args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1",port),Handler)
    print("Viewer: http://127.0.0.1:"+str(server.server_port)+"/",flush=True)
    print("Ctrl+C to stop. The HTML also opens directly without a server.",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("build","verify","serve"))
    p.add_argument("--firewall-root",type=Path)
    p.add_argument("--port",type=int,default=8765)
    args=p.parse_args()
    if args.action=="serve":
        if not 0<=args.port<=65535:p.error("port must be in 0..65535")
        serve(ROOT,args.port);return
    result = build(ROOT,args.firewall_root) if args.action=="build" else verify(ROOT,args.firewall_root)
    if args.action=="build":
        print(json.dumps({"studies":result["studies"],"bridge":result["bridge"]},indent=2))
    else:print(json.dumps(result,indent=2))
    assert "torch" not in sys.modules and "numpy" not in sys.modules
    print("PASS: no torch/numpy imports or model calls.")
if __name__=="__main__":main()
