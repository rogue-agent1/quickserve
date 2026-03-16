#!/usr/bin/env python3
"""quickserve - Quick file server with upload support."""
import http.server, argparse, os, sys, json, time, cgi, urllib.parse

class Handler(http.server.SimpleHTTPRequestHandler):
    upload_enabled = False
    
    def do_POST(self):
        if not self.server.upload_enabled:
            self.send_error(403, "Upload disabled"); return
        
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' in content_type:
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                     environ={'REQUEST_METHOD': 'POST',
                                             'CONTENT_TYPE': content_type})
            if 'file' in form:
                item = form['file']
                if item.filename:
                    fname = os.path.basename(item.filename)
                    fpath = os.path.join(self.directory, fname)
                    with open(fpath, 'wb') as f:
                        f.write(item.file.read())
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f"Uploaded: {fname}\n".encode())
                    print(f"  ↑ Upload: {fname} ({os.path.getsize(fpath)} bytes)")
                    return
        self.send_error(400, "Bad request")
    
    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404); return None
        
        entries.sort(key=lambda a: (not os.path.isdir(os.path.join(path, a)), a.lower()))
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        
        rel = urllib.parse.unquote(self.path)
        html = f"""<!DOCTYPE html><html><head><title>Index of {rel}</title>
        <style>body{{font-family:monospace;margin:2em}}a{{text-decoration:none}}
        tr:hover{{background:#f0f0f0}}</style></head><body>
        <h1>📁 Index of {rel}</h1><table><tr><th>Name</th><th>Size</th><th>Modified</th></tr>"""
        
        if rel != '/':
            html += '<tr><td><a href="../">⬆️ ..</a></td><td></td><td></td></tr>'
        
        for name in entries:
            if name.startswith('.'): continue
            fp = os.path.join(path, name)
            stat = os.stat(fp)
            if os.path.isdir(fp):
                html += f'<tr><td>📁 <a href="{urllib.parse.quote(name)}/">{name}/</a></td><td>-</td>'
            else:
                size = stat.st_size
                for u in ['B','KB','MB','GB']:
                    if size < 1024: break
                    size /= 1024
                html += f'<tr><td>📄 <a href="{urllib.parse.quote(name)}">{name}</a></td><td>{size:.1f}{u}</td>'
            html += f'<td>{time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))}</td></tr>'
        
        if self.server.upload_enabled:
            html += '</table><hr><form method="POST" enctype="multipart/form-data">'
            html += '<input type="file" name="file"><button type="submit">Upload</button></form>'
        else:
            html += '</table>'
        html += '</body></html>'
        self.wfile.write(html.encode())
        return None

def main():
    p = argparse.ArgumentParser(description='Quick file server')
    p.add_argument('directory', nargs='?', default='.')
    p.add_argument('-p', '--port', type=int, default=8000)
    p.add_argument('-b', '--bind', default='0.0.0.0')
    p.add_argument('-u', '--upload', action='store_true', help='Enable uploads')
    args = p.parse_args()
    
    Handler.directory = os.path.abspath(args.directory)
    server = http.server.HTTPServer((args.bind, args.port), Handler)
    server.upload_enabled = args.upload
    
    print(f"Serving {os.path.abspath(args.directory)} on http://{args.bind}:{args.port}")
    if args.upload: print("📤 Upload enabled")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopped.")

if __name__ == '__main__':
    main()
