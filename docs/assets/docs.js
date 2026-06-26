(function () {
  const KEY = 'dohub-docs-lang';

  function applyLang(lang) {
    const l = lang === 'en' ? 'en' : 'vi';
    document.documentElement.lang = l;
    document.querySelectorAll('.lang-block').forEach((el) => {
      el.classList.toggle('hidden', el.dataset.lang !== l);
    });
    document.querySelectorAll('[data-lang-btn]').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.langBtn === l);
      btn.setAttribute('aria-pressed', btn.dataset.langBtn === l ? 'true' : 'false');
    });
    try {
      localStorage.setItem(KEY, l);
    } catch (_) {
      /* ignore */
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    let saved = 'vi';
    try {
      saved = localStorage.getItem(KEY) || 'vi';
    } catch (_) {
      /* ignore */
    }
    applyLang(saved);
    document.querySelectorAll('[data-lang-btn]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        applyLang(btn.dataset.langBtn);
      });
    });
  });
})();
