"""Import an existing local data directory into an EMPTY PostgreSQL workspace.

Usage: set DATABASE_URL privately, then python migrate_local.py --source /path/to/data
The source is read-only. This command does not merge two existing workspaces.
"""
import argparse
import re
import sqlite3
from pathlib import Path
import server


def main():
    parser = argparse.ArgumentParser(description='Migrar dados locais para um banco online vazio.')
    parser.add_argument('--source', required=True, help='Pasta data da instalação local ou backup extraído')
    args = parser.parse_args()
    source = Path(args.source).resolve()
    if not server.DATABASE_URL:
        raise SystemExit('Configure DATABASE_URL no ambiente antes de executar a migração.')
    db = source/'prates.sqlite3'
    if not db.is_file(): raise SystemExit('prates.sqlite3 não encontrado na pasta informada.')
    local = sqlite3.connect(db.as_uri()+'?mode=ro', uri=True)
    local.row_factory = sqlite3.Row
    tables = ['users','records','settings','attachments','attempts','audit']
    rows = {t:list(local.execute('SELECT * FROM '+t)) for t in tables}
    if not rows['users']: raise SystemExit('O banco local não contém usuários; use a configuração inicial online.')
    blobs = {}
    for row in rows['attachments']:
        aid=row['id']
        if not re.fullmatch('[a-f0-9]{32}',aid):raise SystemExit('Identificador de anexo inválido no banco local.')
        path=source/'uploads'/aid
        if not path.is_file():raise SystemExit('Falta um arquivo referenciado pelo backup. A migração não foi executada.')
        if path.stat().st_size>server.MAX_UPLOAD:
            raise SystemExit('Existe anexo maior que 3 MB. Reduza-o ou use armazenamento de arquivos dedicado antes da migração.')
        blobs[aid]=path.read_bytes()
    server.ensure_ready()
    with server.conn() as target:
        target.execute('BEGIN IMMEDIATE')
        if target.execute('SELECT 1 FROM users').fetchone():
            raise SystemExit('O destino já contém usuários. Migração cancelada; nenhum dado foi sobrescrito.')
        if target.execute("SELECT 1 FROM records WHERE entity!='services'").fetchone():
            raise SystemExit('O destino já contém registros. Migração cancelada.')
        # A freshly initialized target contains only the default service catalog.
        target.execute('DELETE FROM records')
        target.execute('DELETE FROM settings')
        for table in tables:
            for row in rows[table]:
                keys=list(row.keys())
                target.execute(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join("?" for _ in keys)})',tuple(row))
        for aid,content in blobs.items():
            target.execute('INSERT INTO upload_blobs VALUES(?,?)',(aid,content))
        target.execute("SELECT setval(pg_get_serial_sequence('prates.audit','id'), COALESCE((SELECT MAX(id) FROM audit),1), EXISTS(SELECT 1 FROM audit))")
    local.close()
    print('Migração concluída. Usuários, registros e anexos preservados. Entre novamente com suas credenciais locais.')


if __name__=='__main__':main()
