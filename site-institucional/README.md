# Site institucional da Prates Digital

Site estático com páginas de serviços, planos, equipe, contato e privacidade. O formulário prepara a mensagem no WhatsApp para o visitante revisar e enviar.

## Estrutura

- `build.py`: conteúdo das páginas e gerador HTML.
- `dist/`: arquivos estáticos prontos para servir.
- `dist/config.js`: número de WhatsApp e e-mail de contato.

## Editar

1. Troque o número e o e-mail provisórios em `dist/config.js`. Use DDI, DDD e número, sem pontuação.
2. Ajuste textos e preços em `build.py`.
3. Execute `python build.py` para atualizar as páginas em `dist/`.
4. Publique `dist/` em um servidor estático. As rotas de navegação usam caminhos absolutos e devem ser servidas na raiz do domínio.

Os preços são referências iniciais; valide o escopo e os valores finais antes de divulgar. Não há depoimentos fictícios. As fotos são carregadas do Unsplash, e as fontes do Google Fonts.

A publicação original do site está em https://prates-digital.joka22092008.chatgpt.site (acesso privado até a liberação pública).
