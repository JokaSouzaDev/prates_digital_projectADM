(() => {
  const cfg = window.PRATES_CONFIG || {};
  const menuButton = document.querySelector('.menu-toggle');
  const menu = document.querySelector('.menu');
  menuButton?.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    document.body.classList.toggle('menu-open', open);
  });
  document.querySelectorAll('.menu a').forEach(a => a.addEventListener('click', () => {
    menu.classList.remove('open'); document.body.classList.remove('menu-open');
    menuButton?.setAttribute('aria-expanded', 'false');
  }));
  const message = 'Olá, equipe Prates Digital! Gostaria de conversar sobre um projeto.';
  const wa = (text) => `https://wa.me/${cfg.whatsapp}?text=${encodeURIComponent(text)}`;
  document.querySelectorAll('[data-contact="whatsapp"]').forEach(a => { a.href = wa(message); a.target = '_blank'; a.rel = 'noopener noreferrer'; });
  document.querySelectorAll('[data-contact="email"]').forEach(a => a.href = `mailto:${cfg.email}?subject=${encodeURIComponent('Contato pelo site da Prates Digital')}`);

  const form = document.querySelector('#quote-form');
  if (form) {
    const params = new URLSearchParams(location.search);
    const service = params.get('servico'); const plan = params.get('plano');
    if (service) [...form.querySelectorAll('[name="servico"]')].find(x => x.value === service)?.click();
    if (plan) form.elements.plano.value = plan;
    const error = form.querySelector('.form-error');
    const getInfo = () => {
      const data = new FormData(form);
      const services = data.getAll('servico');
      if (!form.reportValidity()) return null;
      if (!services.length) {
        error.textContent = 'Escolha pelo menos uma opção em “O que você procura?”.'; error.hidden = false;
        form.querySelector('fieldset').scrollIntoView({behavior:'smooth',block:'center'});
        return null;
      }
      error.hidden = true;
      return `Olá, equipe Prates Digital! Gostaria de pedir um orçamento.\n\nNome: ${data.get('nome')}\nE-mail: ${data.get('email')}\nEmpresa/projeto: ${data.get('empresa') || 'Não informado'}\nServiços: ${services.join(', ')}\nPlano: ${data.get('plano') || 'A definir'}\n\nDescrição: ${data.get('descricao')}`;
    };
    form.addEventListener('submit', e => {
      e.preventDefault(); const text = getInfo(); if (!text) return;
      const link = document.createElement('a'); link.href = wa(text); link.target = '_blank'; link.rel = 'noopener noreferrer';
      document.body.append(link); link.click(); link.remove();
    });
    document.querySelector('#email-form')?.addEventListener('click', e => {
      e.preventDefault(); const text = getInfo(); if (!text) return;
      location.href = `mailto:${cfg.email}?subject=${encodeURIComponent('Pedido de orçamento — Prates Digital')}&body=${encodeURIComponent(text)}`;
    });
  }

  const progress = document.querySelector('.progress');
  let ticking = false;
  const update = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    if (progress) progress.style.transform = `scaleX(${max > 0 ? scrollY / max : 0})`;
    ticking = false;
  };
  addEventListener('scroll', () => { if (!ticking) { requestAnimationFrame(update); ticking = true; } }, {passive:true}); update();
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); io.unobserve(entry.target); }
    }), {threshold:.08, rootMargin:'0px 0px -20px 0px'});
    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  } else document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
})();
