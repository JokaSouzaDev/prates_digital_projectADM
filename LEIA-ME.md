# Prates Digital — Administrativo

Sistema administrativo com predominância de preto e detalhes em laranja. Interface em português, valores em reais, acesso individual e banco de dados SQLite. Não depende de bibliotecas externas nem de internet para o uso local.

## Abrir no Windows

1. Se recebeu o ZIP, extraia todo o conteúdo para uma pasta.
2. Abra **Iniciar-Prates.cmd** com dois cliques.
3. O navegador abrirá em **http://127.0.0.1:8765**. Mantenha a janela do servidor aberta enquanto usa o sistema.
4. No primeiro acesso, crie sua conta de administrador e guarde o código de recuperação.
5. Em **Equipe e acessos**, crie a conta do outro sócio e entregue a ele a senha inicial e o código de recuperação de sua própria conta.

Neste computador, o iniciador utiliza o Python incluído no ambiente do Codex. Em outro computador, instale Python 3.11 ou superior. Também é possível iniciar com `python start.py` na pasta do projeto.

O arquivo `index.html` depende do servidor: abrir somente esse arquivo por duplo clique não inicia o sistema.

## Primeira configuração

- Preencha os dados da empresa em **Configurações**. A logo é opcional.
- Os dez serviços discutidos já estão cadastrados, sem preços inventados. Ajuste preços, custos, prazos e escopo em **Serviços e pacotes**.
- Cadastre os clientes, responsabilidades e metas reais. O banco entregue não contém vendas nem clientes de demonstração.
- Joaquim e Kauã constam nas opções de movimentação dos sócios. As contas de acesso são criadas por vocês; nenhuma senha vem pronta.

## Fluxo comercial e operacional

1. Cadastre o contato no **Funil de vendas** e o cliente em **Clientes**.
2. Monte uma proposta com um ou mais serviços, quantidades, preços, desconto e parcelamento.
3. Use **Abrir → Imprimir / PDF** e selecione “Salvar como PDF” na janela do navegador.
4. Registre a aprovação. “Converter em venda” gera a venda, parcelas, projeto e briefing. Na conversão, o primeiro vencimento é a data atual; confira os dados antes de confirmar.
5. Também é possível cadastrar a venda diretamente, incluindo entrada e parcelas mensais do saldo. A entrada gera uma conta a receber; ela não é considerada recebida automaticamente.
6. Em **Contas a receber**, abra a conta e registre cada pagamento, inclusive pagamentos parciais.
7. Acompanhe o projeto pelo quadro, com responsável, prazo, checklist e aprovação do cliente. No computador, arraste os cartões; no celular, altere a situação em Editar.
8. Use **Conteúdo e redes** e **Agenda e tarefas** em lista ou calendário.

Contratos registram termos, vigência, assinatura informada e anexos. O registro de assinatura não equivale a uma assinatura eletrônica. O histórico guarda as versões anteriores dos cadastros.

## Financeiro e metas

- Vendas e recebimentos são indicadores separados.
- O resultado gerencial usa recebimentos menos despesas efetivamente pagas no período.
- A verba de mídia usa categoria própria, fora do resultado operacional da agência.
- Aportes, retiradas e reembolsos são registrados em **Sócios**. Não duplique um reembolso em Despesas.
- Contas com recebimentos não podem ser apagadas ou ter pagamentos editados. Estornos são lançamentos separados com categoria correspondente e referência ao lançamento original.
- Vendas com pagamentos não são canceladas automaticamente. A conciliação de estornos e do histórico deve ser tratada separadamente.
- Mensalidades: **Abrir → Gerar cobrança** cria a próxima conta a receber e avança o vencimento em um mês. Não há cobrança bancária ou envio ao cliente.
- Despesa mensal: **Abrir → Gerar próximo mês** cria uma única próxima despesa. Repita a partir do novo registro no próximo ciclo.
- Metas de vendas, quantidade, recebimentos, clientes e entregas usam os dados do sistema. Renovações e indicadores personalizados têm realização manual.
- Uma meta com responsável filtra os registros atribuídos àquela pessoa. Para uma meta geral, deixe o responsável sem seleção.
- Os indicadores de campanhas são inseridos manualmente. CPL, CPA, CTR e ROAS são calculados a partir desses valores.
- Relatórios exportam CSV compatível com planilhas e imprimem em PDF pelo navegador.
- O balanço é gerencial pelo regime de caixa; não representa um balanço patrimonial contábil ou saldo bancário conciliado.

## Acesso, recuperação e dados

- Senhas são armazenadas com PBKDF2, salt individual e 300 mil iterações.
- Sessões expiram em 12 horas e usam cookie HttpOnly e SameSite Strict.
- Operações exigem token de sessão. Há limitação de tentativas de login e recuperação.
- Perfis: administrador, financeiro, comercial e produção. As permissões são verificadas no servidor.
- O código de recuperação é de uso único e permite definir uma nova senha. A recuperação gera um novo código. Não há envio de e-mail nesta versão.
- Alterações concorrentes são detectadas para evitar que uma pessoa sobrescreva os dados da outra sem perceber.
- Anexos têm limite de 5 MB e só podem ser baixados por quem tem acesso ao módulo.
- O banco fica em `data/prates.sqlite3`, e os anexos em `data/uploads/`.

## Backup e restauração

O iniciador cria uma cópia diária ao abrir o sistema, quando já existe banco, em `data/backups/`. Nenhuma cópia antiga é removida automaticamente. Também é possível baixar um ZIP completo em **Configurações → Backup**. Mantenha cópias fora deste computador.

Para restaurar:

1. Encerre o servidor.
2. Guarde uma cópia da pasta `data` atual, sem apagá-la.
3. Extraia o backup em uma pasta separada e confira os arquivos.
4. Substitua `data/prates.sqlite3` e a pasta `data/uploads` pelos arquivos do backup correspondente.
5. Inicie o sistema novamente. Use as credenciais que existiam na data do backup.

Backups contêm dados privados e informações de autenticação. Compartilhe apenas com quem administra a empresa.

## Uso por Joaquim e Kauã

No mesmo computador, cada pessoa usa sua própria conta. Para dois computadores na mesma rede, uma única máquina deve manter o servidor e o banco. Um responsável técnico pode iniciar com `PRATES_HOST=0.0.0.0`, liberar a porta na rede privada e acessar pelo IP dessa máquina. Não crie duas cópias independentes do banco para tentar sincronizar a operação.

O sistema entregue roda localmente e não foi publicado na internet. Para acesso remoto contínuo, será necessário definir hospedagem e domínio, HTTPS, serviço de inicialização e política de backups. A configuração `PRATES_SECURE_COOKIE=1` deve ser usada quando servido por HTTPS. O servidor padrão é destinado ao uso local; uma publicação pública precisa de uma camada de hospedagem adequada.

## Integrações da etapa seguinte

Como previsto no escopo, não estão conectados bancos, Pix/cartão, WhatsApp, Meta/Google Ads, emissão fiscal ou assinatura eletrônica. Também não há portal do cliente. Os botões de registro financeiro são controles internos e não movimentam dinheiro.

## Verificação realizada

Testes cobriram criação de conta, recuperação, permissões, proteção das operações, cadastro de cliente, venda e parcelas com arredondamento, entrada, pagamento parcial, rejeição de valor excedente, cancelamento com rollback, conversão de proposta, geração mensal sem duplicação por reenvio, anexos, backup e persistência. As telas foram verificadas no navegador em computador e celular, incluindo os módulos e o checklist.

## Arquivos principais

- `server.py`: servidor, autenticação, dados e regras de negócio.
- `app.js`: telas e interações.
- `style.css`: identidade visual e impressão.
- `index.html`: página inicial.
- `start.py`: inicialização e backup diário.
- `Iniciar-Prates.cmd` e `Iniciar-Prates.ps1`: abertura no Windows.

Não remova a pasta `data` depois de começar a usar.
