// 과외나루 — page script. Everything here has a plain fallback: the page reads and works without it.

// 1. The live thing: compose the consultation text and feed it to the SMS link.
(() => {
  const form = document.getElementById('compose');
  if (!form) return;
  const out = document.getElementById('c-out');
  const link = document.getElementById('sms-link');
  const grade = document.getElementById('c-grade');
  const subject = document.getElementById('c-subject');
  const mode = document.getElementById('c-mode');
  const render = () => {
    const m = mode.value === '상담하며 결정' ? '과외' : mode.value;
    const text = `${grade.value} ${subject.value} ${m} 상담 신청합니다. 가능한 시간에 연락 부탁드립니다.`;
    out.textContent = text;
    const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
    link.href = `sms:01031315305${ios ? '&' : '?'}body=${encodeURIComponent(text)}`;
  };
  [grade, subject, mode].forEach((el) => el.addEventListener('change', render));
  form.addEventListener('submit', (e) => { e.preventDefault(); link.click(); });
  render();
})();

// 2. Mobile menu toggle.
(() => {
  const btn = document.querySelector('.menu-btn');
  if (!btn) return;
  const head = document.querySelector('.site-head');
  btn.addEventListener('click', () => {
    const open = head.classList.toggle('menu-open');
    btn.setAttribute('aria-expanded', open);
  });
  head.querySelectorAll('.gnb a').forEach((a) => a.addEventListener('click', () => head.classList.remove('menu-open')));
})();
