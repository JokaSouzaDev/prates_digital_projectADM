"""Vercel entrypoint. Rewrites retain API paths via an explicit query parameter."""
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import App


class handler(App):
    def handle_request(self, method):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        # Only accept the routing parameter on the actual function path.
        # Original /api/session paths are already correct on some runtimes.
        if parsed.path in ('/api', '/api/', '/api/index', '/api/index.py'):
            route = query.pop('_prates_route', [''])[0].strip('/')
            if not route or not all(c.isalnum() or c in '/_-' for c in route):
                return self.send(404, {'error': 'Rota da API não encontrada. Confira vercel.json.'})
            self.path = '/api/' + route + ('?' + urlencode(query, doseq=True) if query else '')
        return super().handle_request(method)
