# Prates Digital — versão preparada para Vercel

Esta pasta substitui os arquivos da versão local que você enviou. O visual preto e os módulos foram mantidos. A publicação agora inclui uma API Python e armazenamento PostgreSQL para usuários, cadastros, sessões e anexos.

**O código está adaptado, mas a publicação online depende de você conectar um banco e definir duas variáveis na Vercel. Não basta subir o ZIP sem essa configuração.** A conexão real com o seu banco ainda não foi testada, porque ele ainda não foi criado.

## 1. Atualize os arquivos no GitHub

Extraia o ZIP. Coloque o **conteúdo** de `Prates-Digital-Vercel` na mesma pasta do repositório que contém o `index.html` publicado. Substitua os arquivos correspondentes e adicione os novos, especialmente a pasta `api`.

Essa pasta precisa ter, no mesmo nível:

```text
api/
  index.py
app.js
index.html
style.css
server.py
database.py
build_static.py
requirements.txt
vercel.json
.python-version
.gitignore
.vercelignore
```

Inclua também os guias e os demais arquivos do pacote. Não envie a pasta `data` local ou arquivos `.env` com valores reais ao GitHub. O pacote contém regras para excluí-los de novas publicações; regras de exclusão não removem arquivos que já tenham sido publicados anteriormente.

## 2. Confira a pasta usada pela Vercel

No projeto `pratesdigitaladm`, abra **Settings → Build and Deployment** e confira:

| Campo | Configuração |
|---|---|
| Framework Preset | **Other** |
| Root Directory | Pasta que contém `vercel.json` |
| Build Command | `python build_static.py` |
| Output Directory | `public` |
| Install Command | Deixe no padrão; a função Python usa `requirements.txt` |

Se os arquivos estão diretamente na raiz do repositório, use a raiz (`.` ou campo padrão). Se estão dentro de `Prates-Digital`, use **Prates-Digital**. Não use a pasta `public` como Root Directory.

O `vercel.json` já define o comando de build, a saída pública e o encaminhamento de `/api/...` para a função Python. Remova configurações antigas de Next.js ou de outro framework caso tenham sido colocadas nesse projeto. O pacote não usa Next.js nem precisa de `npm run build`.

Somente `index.html`, `app.js` e `style.css` são copiados para a pasta pública. O código do servidor e os dados não são publicados como arquivos estáticos.

## 3. Crie e conecte o banco

Para esta instalação, use **PostgreSQL no Neon**, que pode ser conectado à Vercel. Também há compatibilidade com uma conexão PostgreSQL com pool do Supabase.

Você pode criar o Neon pela integração disponível no Marketplace/Storage da Vercel e conectá-lo ao projeto, ou criar pelo painel do Neon e configurar a conexão manualmente. O [guia oficial de conexão Neon–Vercel](https://neon.com/docs/guides/vercel-manual) explica as opções.

No painel do banco, obtenha a conexão **PostgreSQL com pool**, que começa com `postgresql://`. Guarde-a apenas na configuração do servidor. Não use uma chave `anon`, `publishable` ou uma URL HTTP de API no lugar dessa conexão.

Em **Vercel → projeto → Settings → Environment Variables**, configure para **Production**:

| Nome | Valor |
|---|---|
| `DATABASE_URL` | A conexão PostgreSQL completa fornecida pelo banco |
| `PRATES_SETUP_KEY` | Uma chave privada aleatória com pelo menos 24 caracteres, criada por você |

Se a integração já criou `DATABASE_URL`, confira se ela está vinculada ao projeto e ao ambiente Production. A chave de instalação pode ser criada com um gerenciador de senhas. Ela é diferente da senha que você usará para entrar no sistema.

Não coloque esses valores em `app.js`, no GitHub, em prints públicos ou na conversa. O arquivo `.env.example` contém somente modelos e não deve ser usado com os valores de exemplo em produção.

## 4. Faça um novo deploy

Depois de salvar as variáveis, use **Deployments → Redeploy** na Vercel. Mudanças de variáveis só valem para novos deployments, conforme a [documentação da Vercel](https://vercel.com/docs/environment-variables).

Quando terminar, abra:

```text
https://pratesdigitaladm.vercel.app/api/session
```

O resultado deve ser um objeto JSON com campos como `setup` e `user`. Se faltar a conexão, a API agora retorna uma mensagem clara em JSON. Se aparecer “The page could not be found”, confira Root Directory, a pasta `api` e `vercel.json`.

Não compartilhe o conteúdo completo da resposta se você já estiver autenticado, pois a resposta contém informações da sessão.

## 5. Crie os acessos

1. Abra a página principal do site.
2. Informe a **chave de instalação** que definiu em `PRATES_SETUP_KEY`.
3. Crie o primeiro administrador com nome, e-mail e senha.
4. Guarde o código de recuperação mostrado ao terminar.
5. Em **Equipe e acessos**, cadastre a conta do outro sócio.

A chave de instalação protege a criação do primeiro administrador em um endereço público. Ela não é exibida ao visitante nem enviada dentro do JavaScript. Mantenha a variável configurada; depois da primeira conta, novos usuários só são criados por um administrador autenticado.

As tabelas e o catálogo de serviços são criados automaticamente no primeiro acesso válido ao banco. Preços permanecem editáveis, sem valores inventados. O banco usa um schema próprio chamado `prates`.

## Como os dados ficam salvos

- Na Vercel, `DATABASE_URL` é obrigatória. O sistema não tenta gravar um SQLite temporário.
- Usuários, vendas, clientes, pagamentos, metas e sessões ficam no PostgreSQL.
- Anexos ficam no mesmo banco, como conteúdo binário protegido pelas permissões da API. Não há links públicos para os arquivos.
- O limite por anexo passou a **3 MB**, para caber no limite de requisição da Vercel após a codificação do upload.
- Um novo deploy não apaga os cadastros do banco externo.
- As conexões são encerradas após cada requisição, e a configuração por transação funciona com conexões de pool.
- Transações e verificação de versão preservam os fluxos de vendas, pagamentos e cobranças contra reenvios e alterações concorrentes.

## Backup e migração de dados locais

O backup diário do iniciador Windows se aplica somente ao uso local. Para a versão online, configure os backups do provedor PostgreSQL. Como os anexos ficam no mesmo banco, eles entram no backup do provedor.

O botão de exportação no sistema continua gerando um ZIP com banco SQLite e anexos, compatível com a versão local, enquanto o pacote couber no limite de resposta da Vercel. Acima desse limite, a aplicação mostra uma mensagem para usar o backup do provedor. Sessões ativas não são copiadas para o backup exportado.

Se você já possui cadastros na instalação local e quer levá-los para o banco online, **não crie primeiro uma conta online**. Use `migrate_local.py` com o banco de destino vazio:

```text
python -m pip install -r requirements.txt
python migrate_local.py --source "CAMINHO_DA_PASTA_DATA"
```

Configure `DATABASE_URL` privadamente no ambiente antes de executar. O script lê a origem sem alterá-la, verifica os anexos e recusa sobrescrever um destino que já tenha usuários ou registros da operação. Usa uma única transação para importar os dados. Depois, entre com as credenciais da instalação local.

O script também aceita uma pasta de backup extraído contendo `prates.sqlite3` e `uploads/`. Não mescla duas instalações ativas. Arquivos maiores que 3 MB precisam ser tratados antes de migrar.

## Continuar usando localmente

Sem `DATABASE_URL` e fora da Vercel, os iniciadores Windows continuam usando SQLite local. Se você definir `DATABASE_URL`, a aplicação local usará o banco online. A configuração do ambiente deve ser intencional para não testar alterações com dados reais.

O `.env.example` é apenas documentação. Os iniciadores não carregam arquivos `.env` automaticamente.

As instruções de operação dos módulos estão em `GUIA-LOCAL.md`; as regras desta página prevalecem para hospedagem, banco, backup e anexos na versão Vercel.

## Verificações realizadas e pendentes

Verificado neste ambiente: sintaxe Python/JavaScript, build dos arquivos públicos, 11 testes de rotas/configuração/segurança, criação de conta, login, recuperação, venda com entrada e parcelas, pagamento parcial, permissões, proposta, mensalidade, anexos, exportação e persistência local. A interface também foi verificada para as mensagens de configuração e de API ausente.

**Ainda pendente:** instalar as dependências na Vercel, conectar um PostgreSQL real e conferir o fluxo no endereço publicado. O pacote não foi enviado automaticamente ao GitHub nem à sua conta Vercel. Não houve teste real da conexão PostgreSQL ou da migração online neste ambiente.

Para repetir os testes locais:

```text
python -m unittest discover -s tests -v
python tests/integration_local.py
```

## Referências técnicas

- [Funções Python em api/ e suporte a BaseHTTPRequestHandler](https://vercel.com/docs/functions/runtimes/python/api-directory)
- [Rewrites da Vercel](https://vercel.com/docs/routing/rewrites)
- [Limites das funções](https://vercel.com/docs/functions/limitations)
- [Transações com Psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
