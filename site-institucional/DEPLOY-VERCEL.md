# Publicar o site na Vercel

Importe o repositório `JokaSouzaDev/prates_digital_projectADM` como um novo projeto. Em **Root Directory**, selecione `site-institucional`. O arquivo `vercel.json` define Framework Preset como Other e Output Directory como `dist`. Não use a raiz do repositório, pois ela contém o sistema administrativo.

Antes de divulgar o endereço, troque o WhatsApp e o e-mail provisórios em `dist/config.js`. Se alterar textos ou preços em `build.py`, execute `python build.py` e envie também os arquivos atualizados de `dist/` para o GitHub.

O site usa URLs absolutas e deve ser servido na raiz do projeto Vercel.
