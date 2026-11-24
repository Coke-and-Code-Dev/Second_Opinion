"""Build and serve an isolated, synthetic-only Render demonstration."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'tai'


def build():
    # Never generate over an existing local dataset, including a partial one.
    if DATA.exists():
        raise SystemExit('Refusing to build: data/tai already exists. Use a clean checkout.')
    subprocess.run([sys.executable, 'src/simulation/simulate_tai.py', '--plants', '4',
                    '--target-rows', '80000', '--quality-scale', '0'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, 'src/pipeline.py'], cwd=ROOT, check=True)


def serve():
    import server
    server.build_index(DATA / 'pipeline', DATA / 'extracted')
    if server.state['phase'] != 'ready' or not server.state['metrics']:
        raise SystemExit('Synthetic demo results could not be loaded: ' + str(server.state))

    class DemoHandler(server.Handler):
        def do_GET(self):
            if self.path == '/':
                html = (server.WEB / 'index.html').read_text(encoding='utf-8')
                notice = ('<div style="padding:12px;text-align:center;background:#d9efe2;'
                          'color:#173c2d;font-weight:700">Demo using simulated data</div>')
                # Keep the assistant elements for the original script's event bindings,
                # but hide them: this public demo never accepts keys or sends API calls.
                script = ("<script>document.getElementById('askBox').hidden=true;"
                          "document.getElementById('changeSource').hidden=true;"
                          "document.getElementById('connect').hidden=true;poll();</script>")
                body = html.replace('<body>', '<body>' + notice, 1).replace('</body>', script + '</body>').encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def do_POST(self):
            # Do not expose file selection or AI provider requests on the internet.
            self.send_json({'error': 'Unavailable in the public demo'}, 403)

    port = int(os.environ.get('PORT', '10000'))
    print(f'Synthetic demo listening on port {port}', flush=True)
    server.LocalServer(('0.0.0.0', port), DemoHandler).serve_forever()


if __name__ == '__main__':
    build() if '--build' in sys.argv else serve()
