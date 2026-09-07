"""Publish only public UI assets, never databases, secrets or Python source."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
public = root / 'public'
public.mkdir(exist_ok=True)
for filename in ('index.html', 'app.js', 'style.css'):
    shutil.copyfile(root / filename, public / filename)
print('Interface preparada em public/. API Python publicada separadamente.')
