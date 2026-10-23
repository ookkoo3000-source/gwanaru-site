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

// 2. Index with preview: pointing at a subject bar shows its drawing in the fixed frame.
(() => {
  const bars = document.querySelectorAll('.bar[data-preview]');
  const frame = document.querySelector('.preview');
  if (!bars.length || !frame) return;
  const slides = frame.querySelectorAll('.preview__slide');
  const show = (id) => slides.forEach((s) => s.classList.toggle('is-on', s.dataset.id === id));
  show(bars[0].dataset.preview);
  bars.forEach((bar) => {
    const on = () => show(bar.dataset.preview);
    bar.addEventListener('pointerenter', on);
    bar.addEventListener('focusin', on);
    bar.addEventListener('toggle', () => { if (bar.open) on(); });
  });
})();

// 3. Only one subject bar open at a time, so the list stays a list.
(() => {
  const bars = [...document.querySelectorAll('.bars .bar')];
  bars.forEach((bar) => bar.addEventListener('toggle', () => {
    if (bar.open) bars.forEach((o) => { if (o !== bar) o.open = false; });
  }));
})();
