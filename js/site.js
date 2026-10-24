// 과외나루 — 페이지 스크립트. 스크립트가 없어도 내용은 모두 보이고 링크·전화·문자는 동작합니다.
// 여기서 하는 일: 모바일 메뉴, 상담 신청서 전송(AJAX), 하단 고정 버튼이 입력창을 가리지 않게 숨기기, 클릭 측정(GA4가 설정된 경우에만).

// 측정: 연락처·상담 내용 같은 개인정보는 보내지 않습니다. 이벤트 이름만 보냅니다.
function track(name, params) {
  if (typeof window.gtag === 'function') window.gtag('event', name, Object.assign({ transport_type: 'beacon' }, params || {}));
}
document.addEventListener('click', (e) => {
  const a = e.target.closest('[data-track]');
  if (a) track(a.dataset.track, { page_path: location.pathname });
});

// 1. 모바일 메뉴
(() => {
  const btn = document.querySelector('.menu-btn');
  if (!btn) return;
  const head = document.querySelector('.site-head');
  btn.addEventListener('click', () => {
    const open = head.classList.toggle('menu-open');
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && head.classList.contains('menu-open')) btn.click(); });
})();

// 2. 상담 신청서: 서버(FormSubmit)가 성공을 돌려줄 때만 완료 화면. 검증, 중복 전송 방지, 허니팟.
(() => {
  const form = document.getElementById('apply-form');
  if (!form) return;
  const err = document.getElementById('apply-error');
  const done = document.getElementById('apply-done');
  const submit = document.getElementById('apply-submit');
  const phone = document.getElementById('f-phone');
  const region = document.getElementById('f-region');
  let sending = false;

  const showError = (msg, el) => {
    err.textContent = msg; err.hidden = false;
    if (el) { el.setAttribute('aria-invalid', 'true'); el.focus(); }
    err.scrollIntoView({ block: 'nearest' });
  };
  form.querySelectorAll('.field').forEach((el) => el.addEventListener('input', () => el.removeAttribute('aria-invalid')));

  // 방문을 고르면 지역을 필수로
  form.querySelectorAll('input[name="방식"]').forEach((r) => r.addEventListener('change', () => {
    const visit = form.querySelector('input[name="방식"]:checked')?.value === '방문';
    region.required = visit;
    const lab = form.querySelector('label[for="f-region"]');
    if (lab) lab.innerHTML = visit ? '지역 <b>*</b> <small>(방문 희망 시 시·구·동까지)</small>' : '지역 <small>(방문 희망 시 시·구·동까지)</small>';
  }));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (sending) return;
    err.hidden = true;
    if (form.querySelector('input[name="_honey"]').value) return; // 봇
    const digits = phone.value.replace(/\D/g, '');
    if (digits.length < 9 || digits.length > 11) return showError('연락처를 숫자 9~11자리로 입력해 주세요.', phone);
    const grade = document.getElementById('f-grade');
    if (!grade.value) return showError('학년을 선택해 주세요.', grade);
    if (!form.querySelector('input[name="과목"]:checked')) return showError('희망 과목을 하나 이상 선택해 주세요.', form.querySelector('input[name="과목"]'));
    const mode = form.querySelector('input[name="방식"]:checked');
    if (!mode) return showError('수업 방식을 선택해 주세요.', form.querySelector('input[name="방식"]'));
    if (mode.value === '방문' && !region.value.trim()) return showError('방문 희망 시 지역을 입력해 주세요.', region);
    const agree = form.querySelector('input[name="개인정보동의"]');
    if (!agree.checked) return showError('개인정보 수집·이용에 동의해 주세요.', agree);

    const fd = new FormData(form);
    const data = {};
    for (const [k, v] of fd.entries()) {
      if (k === '_honey') continue;
      data[k] = data[k] ? data[k] + ', ' + v : v;
    }
    data['연락처'] = digits.replace(/(\d{3})(\d{3,4})(\d{4})/, '$1-$2-$3');
    data['접수시각'] = new Date().toLocaleString('ko-KR');

    sending = true; submit.disabled = true; const label = submit.textContent; submit.textContent = '보내는 중…';
    try {
      const res = await fetch(form.action, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, body: JSON.stringify(data) });
      let json = null; try { json = await res.json(); } catch (_) {}
      const ok = res.ok && json && String(json.success) === 'true';
      if (!ok) throw new Error((json && json.message) || ('서버 응답 ' + res.status));
      form.hidden = true; done.hidden = false; done.focus();
      track('form_submit_success', { page_path: location.pathname });
    } catch (ex) {
      track('form_submit_error', { page_path: location.pathname });
      showError('전송에 실패했습니다. 잠시 후 다시 시도하시거나, 전화 010-3131-5305 또는 문자로 남겨 주세요.');
      submit.disabled = false; submit.textContent = label; sending = false;
    }
  });
})();

// 3. 하단 고정 버튼: 신청서나 푸터가 보이면 숨겨서 입력창을 가리지 않게
(() => {
  const bar = document.getElementById('quickbar');
  if (!bar || !('IntersectionObserver' in window)) return;
  const targets = [document.getElementById('apply-form'), document.querySelector('.site-foot')].filter(Boolean);
  if (!targets.length) return;
  const vis = new Map();
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => vis.set(en.target, en.isIntersecting));
    bar.classList.toggle('is-hidden', [...vis.values()].some(Boolean));
  }, { threshold: 0.05 });
  targets.forEach((t) => io.observe(t));
})();
