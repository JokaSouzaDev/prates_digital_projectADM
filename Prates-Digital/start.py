"""Starts Prates Digital and opens the default browser."""
import io, os, sqlite3, threading, webbrowser, zipfile
from datetime import date
from pathlib import Path
from http.server import ThreadingHTTPServer
import server

def backup():
    if not server.DB.exists():return
    target=server.DATA/'backups'/('prates-'+date.today().isoformat()+'.zip')
    if target.exists():return
    target.parent.mkdir(exist_ok=True)
    src=sqlite3.connect(server.DB);memory=sqlite3.connect(':memory:')
    try:
        src.backup(memory)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('prates.sqlite3',memory.serialize())
            for f in (server.DATA/'uploads').iterdir():
                if f.is_file():z.write(f,'uploads/'+f.name)
    finally:src.close();memory.close()

if __name__=='__main__':
    backup();server.initialize()
    host=os.environ.get('PRATES_HOST','127.0.0.1');port=int(os.environ.get('PRATES_PORT','8765'))
    url=f'http://127.0.0.1:{port}'
    try:httpd=ThreadingHTTPServer((host,port),server.App)
    except OSError:
        print(f'Nao foi possivel abrir a porta {port}. Verifique se o sistema ja esta aberto.')
        input('Pressione Enter para sair.');raise SystemExit(1)
    print('\nPRATES DIGITAL | Administrativo\n')
    print(f'Abra: {url}\nMantenha esta janela aberta durante o uso.\nPara encerrar, pressione Ctrl+C.\n')
    threading.Timer(1,lambda:webbrowser.open(url)).start()
    try:httpd.serve_forever()
    except KeyboardInterrupt:print('\nSistema encerrado.')
    finally:httpd.server_close()
