"""Small SQL compatibility layer for the existing SQLite application.

PostgreSQL mode never writes to the deployment filesystem. Each context owns
one connection and transaction; Vercel instances share the same remote database.
"""
import os
import sqlite3


class ConfigurationError(Exception):
    pass


class LocalConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


class Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None

    def __iter__(self):
        for row in self.cursor:
            yield Row(row)


def postgres_sql(sql):
    # These statements are fixed application SQL, never user-provided SQL.
    if sql == 'BEGIN IMMEDIATE':
        return 'SELECT pg_advisory_xact_lock(734281095)'
    if sql.startswith('INSERT OR IGNORE INTO settings'):
        sql = sql.replace('INSERT OR IGNORE', 'INSERT', 1) + ' ON CONFLICT (id) DO NOTHING'
    elif sql.startswith('INSERT OR REPLACE INTO attempts'):
        sql = sql.replace('INSERT OR REPLACE', 'INSERT', 1) + ' ON CONFLICT (key) DO UPDATE SET count=EXCLUDED.count, until=EXCLUDED.until'
    # Preserve question marks inside SQL string literals.
    out, quoted, i = [], False, 0
    while i < len(sql):
        char = sql[i]
        if char == "'":
            if quoted and i+1 < len(sql) and sql[i+1] == "'":
                out.append("''"); i += 2; continue
            quoted = not quoted
        out.append('%s' if char == '?' and not quoted else char)
        i += 1
    return ''.join(out)


class PostgresConnection:
    def __init__(self, url, sqlite_schema):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError:
            raise ConfigurationError('A dependência PostgreSQL não foi instalada. Publique também requirements.txt e faça um novo deploy.') from None
        if not url.startswith(('postgresql://', 'postgres://')):
            raise ConfigurationError('DATABASE_URL precisa ser a conexão PostgreSQL do banco, e não uma chave de API ou endereço do painel.')
        try:
            self.connection = psycopg.connect(
                url, autocommit=True, row_factory=dict_row,
                prepare_threshold=None, connect_timeout=10,
                sslmode='require',
            )
        except psycopg.Error:
            if getattr(self, 'connection', None): self.connection.close()
            raise ConfigurationError('Não foi possível conectar ao banco online. Confira DATABASE_URL, a senha, a disponibilidade do banco e use a conexão com pool do provedor.') from None
        self.integrity_error = psycopg.IntegrityError
        self.sqlite_schema = sqlite_schema

    def __enter__(self):
        try:
            self.begin()
        except Exception:
            self.connection.close()
            raise
        return self

    def begin(self):
        self.connection.execute('BEGIN')
        # Transaction poolers may switch backend connections after each commit.
        # Session-level SET outside a transaction would not be reliable there.
        self.connection.execute('SET LOCAL search_path TO prates')
        self.connection.execute("SET LOCAL statement_timeout TO '20000ms'")
        self.connection.execute("SET LOCAL lock_timeout TO '15000ms'")

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.connection.execute('ROLLBACK' if exc_type else 'COMMIT')
        finally:
            self.connection.close()

    def execute(self, sql, params=()):
        try:
            cursor = self.connection.execute(postgres_sql(sql), params or None)
            return Cursor(cursor)
        except self.integrity_error as exc:
            raise sqlite3.IntegrityError('Conflito de integridade no PostgreSQL') from exc

    def executescript(self, script):
        self.execute('BEGIN IMMEDIATE')
        self.execute('CREATE SCHEMA IF NOT EXISTS prates')
        script = script.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'BIGSERIAL PRIMARY KEY').replace(' REAL', ' DOUBLE PRECISION')
        for statement in script.split(';'):
            if statement.strip(): self.execute(statement.strip())
        self.execute('CREATE TABLE IF NOT EXISTS upload_blobs(id TEXT PRIMARY KEY REFERENCES attachments(id) ON DELETE CASCADE, content BYTEA NOT NULL)')

    def commit(self):
        self.connection.execute('COMMIT')
        # Existing handlers explicitly commit before sending a success response.
        # A fresh transaction keeps the context manager safe for any later reads.
        self.begin()

    def backup(self, target):
        """Export a portable SQLite snapshot, compatible with the local edition."""
        target.executescript(self.sqlite_schema)
        tables = ['users','records','settings','attachments','attempts','audit']
        for table in tables:
            for row in self.execute('SELECT * FROM '+table):
                keys = list(row.keys())
                placeholders = ','.join('?' for _ in keys)
                target.execute(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({placeholders})', tuple(row.values()))
        # Do not revive active sessions when a snapshot is restored.
        target.commit()
