// ════════════════════════════════════════════════
// TELEGRAM WEB APP — Milliy sertifikat qo'llab-quvvatlaydi
// ════════════════════════════════════════════════
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.disableClosingConfirmation?.();
}

let questions   = [];
let answers     = [];   // 'correct'|'wrong'|'skip'|{w1:'...', w2:'...'}|null
let current     = 0;
let score       = 0;
let answered    = false;
let meta        = {};

const DEMO = [
  { id:1, t:"Fe'lning necha zamonlari bor?", a:"2 ta", b:"3 ta", c:"4 ta", d:"5 ta", ok:"B", img:"", type:"choice" },
  { id:2, t:"Qaysi so'z olmosh turkumiga kiradi?", a:"kitob", b:"men", c:"yaxshi", d:"yugurmoq", ok:"B", img:"", type:"choice" },
];

// ══════════════════════════════════════════════
// YUKLASH
// ══════════════════════════════════════════════

async function loadQuestionsFromHash() {
  showLoader(true);
  const params = new URLSearchParams(window.location.search);
  const hash   = params.get('data') || window.location.hash.slice(1);

  if (!hash) {
    console.warn('Data yo\'q — demo');
    questions = DEMO;
    meta      = { subject:'onatili', category:'aralash', is_attestation:false };
    initTest();
    showLoader(false);
    return;
  }

  try {
    const b64    = hash.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(b64);
    const bytes  = Uint8Array.from(binary, c => c.charCodeAt(0));
    const ds     = new DecompressionStream('deflate');
    const writer = ds.writable.getWriter();
    const reader = ds.readable.getReader();
    writer.write(bytes);
    writer.close();
    const chunks = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    const total = chunks.reduce((s, c) => s + c.length, 0);
    const out   = new Uint8Array(total);
    let   off   = 0;
    for (const c of chunks) { out.set(c, off); off += c.length; }
    const parsed = JSON.parse(new TextDecoder('utf-8').decode(out));
    questions = Array.isArray(parsed) ? parsed : (parsed.questions || parsed);
    meta      = Array.isArray(parsed) ? {} : (parsed.meta || {});
    console.log(`✅ ${questions.length} ta savol yuklandi`, meta);
    initTest();
  } catch (e) {
    console.error('Xato:', e);
    questions = DEMO;
    meta      = {};
    initTest();
  }
  showLoader(false);
}

function showLoader(on) {
  const el = document.getElementById('loader');
  if (el) el.style.display = on ? 'flex' : 'none';
}

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════

function initTest() {
  if (!questions.length) {
    document.getElementById('qtxt').textContent = '❌ Savollar topilmadi!';
    return;
  }
  answers = new Array(questions.length).fill(null);
  score   = 0;
  current = 0;

  const SUBJ = { onatili:'📚 Ona tili', adabiyot:'📖 Adabiyot' };
  document.getElementById('hdr-title').textContent = SUBJ[meta.subject] || '📚 Test';
  const subEl = document.getElementById('hdr-sub');
  if (subEl) subEl.textContent = meta.category || '';

  if (tg) {
    tg.setHeaderColor?.('#0f1523');
    tg.setBackgroundColor?.('#0f1523');
  }

  buildGrid();
  renderQuestion(0);
  document.getElementById('test-screen').style.display   = 'block';
  document.getElementById('result-screen').style.display = 'none';
}

// ══════════════════════════════════════════════
// GRID
// ══════════════════════════════════════════════

function buildGrid() {
  const g = document.getElementById('grid');
  g.innerHTML = '';
  questions.forEach((q, i) => {
    const btn       = document.createElement('button');
    btn.className   = 'gbtn' + (i === 0 ? ' cur' : '');
    btn.id          = 'gb-' + i;
    btn.textContent = i + 1;
    // Yozma savollar boshqa rangda
    if (isWritten(q)) btn.classList.add('written');
    btn.onclick = () => jumpTo(i);
    g.appendChild(btn);
  });
}

function updateGrid() {
  questions.forEach((q, i) => {
    const btn = document.getElementById('gb-' + i);
    if (!btn) return;
    btn.className = 'gbtn' + (isWritten(q) ? ' written' : '');
    if      (i === current)            btn.classList.add('cur');
    else if (answers[i] === 'correct') btn.classList.add('ok');
    else if (answers[i] === 'wrong')   btn.classList.add('err');
    else if (answers[i] === 'skip')    btn.classList.add('skp');
    else if (answers[i] && typeof answers[i] === 'object') btn.classList.add('ok');
  });
}

function jumpTo(i) {
  // Faqat javob berilgan (correct/wrong/object) savollarga o'tib bo'lmaydi
  // null va skip uchun o'tish mumkin
  if (answers[i] !== null && answers[i] !== 'skip') return;
  if (answers[i] === 'skip') answers[i] = null; // qayta ishlash uchun reset
  current = i;
  renderQuestion(i);
}

// ══════════════════════════════════════════════
// SAVOL RENDER
// ══════════════════════════════════════════════

function isWritten(q) {
  return q.type === 'written' || q.qtype === 'written';
}

function renderQuestion(i) {
  answered = false;
  const q     = questions[i];
  const total = questions.length;

  const pct = Math.round((i + 1) / total * 100);
  document.getElementById('prg-fill').style.width  = pct + '%';
  document.getElementById('prg-label').textContent = `${i + 1} / ${total}`;
  const pctEl = document.getElementById('prg-pct');
  if (pctEl) pctEl.textContent = pct + '%';
  document.getElementById('hdr-score').textContent = score + ' ball';
  document.getElementById('qnum').textContent = `SAVOL ${i + 1}`;
  document.getElementById('qtxt').textContent = q.t || q.question_text || '';

  const imgEl = document.getElementById('qimg');
  const imgSrc = q.img || '';
  imgEl.style.display = imgSrc ? 'block' : 'none';
  if (imgSrc) imgEl.src = imgSrc;

  const fb = document.getElementById('fb');
  fb.className = 'fb';
  fb.style.display = 'none';
  fb.innerHTML = '';

  document.getElementById('btn-skip').style.display = 'inline-flex';
  document.getElementById('btn-next').style.display = 'none';
  document.getElementById('btn-finish').style.display = 'none';

  if (isWritten(q)) {
    renderWrittenQuestion(q);
  } else {
    renderChoiceQuestion(q);
  }

  updateGrid();
}

function renderChoiceQuestion(q) {
  const opts = document.getElementById('opts');
  opts.innerHTML = '';
  opts.style.display = 'block';

  // Yozma qism konteynerini yashirish
  const wc = document.getElementById('written-container');
  if (wc) wc.style.display = 'none';

  const LBLS  = ['A', 'B', 'C', 'D'];
  const TEXTS = [q.a||'', q.b||'', q.c||'', q.d||''];
  LBLS.forEach((lbl, idx) => {
    const div = document.createElement('div');
    div.className = 'opt';
    div.id        = 'opt-' + lbl;
    div.innerHTML = `<span class="opt-ltr">${lbl}</span><span class="opt-txt">${TEXTS[idx]}</span>`;
    div.onclick   = () => selectOption(lbl);
    opts.appendChild(div);
  });
}

function renderWrittenQuestion(q) {
  const opts = document.getElementById('opts');
  opts.innerHTML = '';
  opts.style.display = 'none';

  // Yozma javob konteyneri
  let wc = document.getElementById('written-container');
  if (!wc) {
    wc = document.createElement('div');
    wc.id = 'written-container';
    opts.parentNode.insertBefore(wc, opts.nextSibling);
  }
  wc.style.display = 'block';

  const parts = q.parts || q.written_parts || 1;

  wc.innerHTML = '';

  if (parts === 1) {
    wc.innerHTML = `
      <div class="written-hint">✏️ Javobingizni yozing:</div>
      <textarea id="written-ans-1" class="written-textarea" placeholder="Bu yerga javob yozing..." rows="4"></textarea>
      <button class="written-submit-btn" onclick="submitWritten()">✅ Javobni tekshirish</button>
    `;
  } else {
    wc.innerHTML = `
      <div class="written-hint">✏️ Ikkita qism uchun javob yozing:</div>
      <div class="written-part-label">1-qism:</div>
      <textarea id="written-ans-1" class="written-textarea" placeholder="1-qism javobi..." rows="3"></textarea>
      <div class="written-part-label">2-qism:</div>
      <textarea id="written-ans-2" class="written-textarea" placeholder="2-qism javobi..." rows="3"></textarea>
      <button class="written-submit-btn" onclick="submitWritten()">✅ Javobni tekshirish</button>
    `;
  }
}

// ══════════════════════════════════════════════
// VARIANT TANLASH
// ══════════════════════════════════════════════

function selectOption(label) {
  if (answered) return;
  answered = true;

  const q       = questions[current];
  const correct = q.ok || q.correct_answer || '';
  const isOk    = label === correct;

  document.querySelectorAll('.opt').forEach(o => {
    o.classList.add('off');
    o.onclick = null;
  });

  document.getElementById('opt-' + label).classList.add(isOk ? 'correct' : 'wrong');
  if (!isOk) document.getElementById('opt-' + correct)?.classList.add('hint');

  answers[current] = isOk ? 'correct' : 'wrong';
  if (isOk) score++;
  document.getElementById('hdr-score').textContent = score + ' ball';

  const TEXTS       = { A: q.a, B: q.b, C: q.c, D: q.d };
  const fb          = document.getElementById('fb');
  const solutionUrl = meta.solution_url || '';
  const qid = q.id || '';
  const qidHtml = qid ? `<br><span style="font-size:11px;opacity:0.6;">ID: ${qid}</span>` : '';
  const linkHtml = solutionUrl
    ? `${qidHtml}<br><a href="${solutionUrl}" target="_blank" style="color:inherit;opacity:0.85;font-size:12px;text-decoration:underline;">📹 Yechimni ko'rish (ID: ${qid})</a>`
    : qidHtml;

  fb.style.display = 'flex';
  if (isOk) {
    fb.className = 'fb ok';
    fb.innerHTML = `✅ To'g'ri javob!${linkHtml}`;
  } else {
    fb.className = 'fb err';
    fb.innerHTML = `❌ Noto'g'ri! To'g'ri: <b>${correct}) ${TEXTS[correct] || ''}</b>${linkHtml}`;
  }

  document.getElementById('btn-skip').style.display = 'none';
  const isLast  = current === questions.length - 1;
  const allDone = answers.every(a => a !== null);
  if (allDone || isLast) {
    document.getElementById('btn-finish').style.display = 'inline-flex';
  } else {
    document.getElementById('btn-next').style.display = 'inline-flex';
  }

  updateGrid();
  tg?.HapticFeedback?.impactOccurred(isOk ? 'medium' : 'heavy');
}

// ══════════════════════════════════════════════
// YOZMA JAVOB TEKSHIRISH
// ══════════════════════════════════════════════

function checkKeywords(userText, keywordsStr) {
  if (!keywordsStr) return true; // kalit so'z yo'q = har qanday javob to'g'ri
  const keywords = keywordsStr.split(',').map(k => k.trim().toLowerCase()).filter(Boolean);
  if (!keywords.length) return true;
  const userLower = userText.toLowerCase();
  // Kamida 1 ta kalit so'z bo'lsa to'g'ri
  return keywords.some(kw => userLower.includes(kw));
}

function submitWritten() {
  if (answered) return;

  const q     = questions[current];
  const parts = q.parts || q.written_parts || 1;

  const ans1El = document.getElementById('written-ans-1');
  const ans1   = ans1El ? ans1El.value.trim() : '';

  if (!ans1) {
    ans1El?.classList.add('shake');
    setTimeout(() => ans1El?.classList.remove('shake'), 500);
    return;
  }

  answered = true;

  // Tekstareani o'qib bo'lmas qiling
  if (ans1El) { ans1El.disabled = true; }

  let ans2 = '';
  const ans2El = document.getElementById('written-ans-2');
  if (ans2El) { ans2 = ans2El.value.trim(); ans2El.disabled = true; }

  // Submit tugmasini yashirish
  const submitBtn = document.querySelector('.written-submit-btn');
  if (submitBtn) submitBtn.style.display = 'none';

  // Tekshirish
  const kw1 = q.kw1 || q.keywords_1 || '';
  const kw2 = q.kw2 || q.keywords_2 || '';

  const ok1 = checkKeywords(ans1, kw1);
  const ok2 = parts < 2 ? true : checkKeywords(ans2, kw2);
  const allOk = ok1 && ok2;

  // Grid uchun
  answers[current] = { w1: ans1, w2: ans2, ok1, ok2 };
  if (allOk) score++;
  document.getElementById('hdr-score').textContent = score + ' ball';

  // Feedback
  const fb = document.getElementById('fb');
  fb.style.display = 'flex';

  let fbHtml = '';
  if (parts === 1) {
    if (ok1) {
      fbHtml = `✅ <b>To'g'ri!</b> Javobingizda kalit so'z topildi.`;
      fb.className = 'fb ok';
    } else {
      const hint = kw1 ? `<br>💡 Kalit so'z: <b>${kw1.split(',')[0].trim()}</b>` : '';
      fbHtml = `❌ <b>Noto'g'ri.</b>${hint}`;
      fb.className = 'fb err';
    }
  } else {
    const icon1 = ok1 ? '✅' : '❌';
    const icon2 = ok2 ? '✅' : '❌';
    const hint1 = (!ok1 && kw1) ? ` (kalit so'z: <b>${kw1.split(',')[0].trim()}</b>)` : '';
    const hint2 = (!ok2 && kw2) ? ` (kalit so'z: <b>${kw2.split(',')[0].trim()}</b>)` : '';
    fbHtml = `${icon1} 1-qism${hint1}<br>${icon2} 2-qism${hint2}`;
    fb.className = allOk ? 'fb ok' : (ok1 || ok2 ? 'fb partial' : 'fb err');
  }
  fb.innerHTML = fbHtml;

  document.getElementById('btn-skip').style.display = 'none';
  const isLast  = current === questions.length - 1;
  const allDone = answers.every(a => a !== null);
  if (allDone || isLast) {
    document.getElementById('btn-finish').style.display = 'inline-flex';
  } else {
    document.getElementById('btn-next').style.display = 'inline-flex';
  }

  updateGrid();
  tg?.HapticFeedback?.notificationOccurred(allOk ? 'success' : 'error');
}

// ══════════════════════════════════════════════
// NAVIGATSIYA
// ══════════════════════════════════════════════

function skipQuestion() {
  answers[current] = 'skip';
  updateGrid();

  // 1. Avval current+1 dan boshlab null savollarni qidir
  for (let i = current + 1; i < questions.length; i++) {
    if (answers[i] === null) { current = i; renderQuestion(i); return; }
  }
  // 2. Boshidan null savollarni qidir
  for (let i = 0; i < current; i++) {
    if (answers[i] === null) { current = i; renderQuestion(i); return; }
  }
  // 3. Null qolmadi — endi skip savollarni qidir (current+1 dan)
  for (let i = current + 1; i < questions.length; i++) {
    if (answers[i] === 'skip') { current = i; renderQuestion(i); return; }
  }
  // 4. Boshidan skip savollarni qidir
  for (let i = 0; i < current; i++) {
    if (answers[i] === 'skip') { current = i; renderQuestion(i); return; }
  }
  // 5. Hamma savol tugadi
  showResult();
}

function nextQuestion() {
  // 1. current+1 dan null savol qidir
  for (let i = current + 1; i < questions.length; i++) {
    if (answers[i] === null) { current = i; renderQuestion(i); return; }
  }
  // 2. Boshidan null savol qidir
  for (let i = 0; i <= current; i++) {
    if (answers[i] === null) { current = i; renderQuestion(i); return; }
  }
  // 3. Skip savollar bormi
  for (let i = 0; i < questions.length; i++) {
    if (answers[i] === 'skip') { current = i; renderQuestion(i); return; }
  }
  showResult();
}

function findNext(from) {
  for (let i = from; i < questions.length; i++) {
    if (answers[i] === null || answers[i] === 'skip') return i;
  }
  for (let i = 0; i < from; i++) {
    if (answers[i] === null || answers[i] === 'skip') return i;
  }
  return -1;
}

function findNextByStatus(from, status) {
  for (let i = from; i < questions.length; i++) {
    if (answers[i] === status) return i;
  }
  for (let i = 0; i < from; i++) {
    if (answers[i] === status) return i;
  }
  return -1;
}

// ══════════════════════════════════════════════
// NATIJA
// ══════════════════════════════════════════════

function showResult() {
  // ✅ QO'SHILDI: Skip va null savollarni xato deb belgilash
  answers = answers.map(a => (a === null || a === 'skip') ? 'wrong' : a);

  const total   = questions.length;
  let correct   = 0, wrong = 0, skip = 0, writtenCorrect = 0, writtenWrong = 0;

  answers.forEach((a, i) => {
    if (a === 'correct')       correct++;
    else if (a === 'wrong')    wrong++;
    else if (a === 'skip' || a === null) skip++;
    else if (typeof a === 'object') {
      const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
      if (allOk) { correct++; writtenCorrect++; }
      else       { wrong++;   writtenWrong++;   }
    }
  });

  const pct = total > 0 ? Math.round(correct / total * 100) : 0;

  document.getElementById('test-screen').style.display   = 'none';
  document.getElementById('result-screen').style.display = 'flex';

  const grades = [
    [90, '🏆', "A'lo (5)"],
    [70, '🎉', 'Yaxshi (4)'],
    [50, '📚', 'Qoniqarli (3)'],
    [0,  '😔', 'Qoniqarsiz (2)'],
  ];
  const [, emoji, grade] = grades.find(([min]) => pct >= min);

  document.getElementById('r-emoji').textContent   = emoji;
  document.getElementById('r-grade').textContent   = grade;
  document.getElementById('r-score').textContent   = pct + '%';
  document.getElementById('r-correct').textContent = correct;
  document.getElementById('r-wrong').textContent   = wrong;
  document.getElementById('r-skip').textContent    = skip;

  const rg = document.getElementById('result-grid');
  rg.innerHTML = '';
  const colMap = { correct:'ok', wrong:'err', skip:'skp' };
  answers.forEach((a, i) => {
    const d = document.createElement('div');
    if (typeof a === 'object' && a !== null) {
      const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
      d.className = 'gbtn written ' + (allOk ? 'ok' : 'err');
    } else {
      d.className = 'gbtn ' + (colMap[a] || '');
    }
    d.textContent = i + 1;
    if (a === 'skip' || a === null) {
      d.onclick = () => retrySkipped(i);
      d.title = 'Bosing — bu savolga qaytish';
      d.style.cursor = 'pointer';
      d.style.border = '2px solid #f59e0b';
    }
    rg.appendChild(d);
  });

  // To'g'ri javoblar ro'yxati
  const answerList = document.getElementById('answer-list');
  if (answerList) {
    answerList.innerHTML = '';
    questions.forEach((q, i) => {
      if (q.type === 'written') return;
      const TEXTS = { A: q.a, B: q.b, C: q.c, D: q.d };
      const userAns = answers[i];
      const correctKey = q.ok || q.correct_answer || '';
      const icon = userAns === 'correct' ? '✅' : userAns === 'skip' || userAns === null ? '⏭' : '❌';
      const div = document.createElement('div');
      div.style.cssText = 'font-size:13px;padding:4px 0;border-bottom:0.5px solid rgba(255,255,255,0.08);';
      div.innerHTML = `${icon} <b>${i+1}.</b> ${q.t || ''}<br><span style="opacity:0.7;font-size:12px;">✅ ${correctKey}) ${TEXTS[correctKey]||''}</span>`;
      answerList.appendChild(div);
    });
  }

  tg?.HapticFeedback?.notificationOccurred('success');
  // ✅ QO'SHILDI: Natijani avtomatik yuborish
  setTimeout(() => sendResult(), 800);
}

function retrySkipped(idx) {
  // O'tkazilgan savolga qaytish
  const skippedIndexes = answers
    .map((a, i) => (a === 'skip' || a === null) ? i : -1)
    .filter(i => i >= 0);
  if (skippedIndexes.length === 0) return;

  // Natija ekranini yashirib, test ekranini ko'rsatish
  document.getElementById('result-screen').style.display = 'none';
  document.getElementById('test-screen').style.display   = 'block';

  answers[idx] = null;
  current = idx;
  renderQuestion(idx);
}

function sendResult() {
  const total   = questions.length;
  let correct   = 0, wrong = 0, skip = 0;

  answers.forEach((a, i) => {
    if (a === 'correct') correct++;
    else if (a === 'wrong') wrong++;
    else if (a === 'skip' || a === null) skip++;
    else if (typeof a === 'object') {
      const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
      if (allOk) correct++; else wrong++;
    }
  });

  const pct = total > 0 ? Math.round(correct / total * 100) : 0;

  // Xato va to'g'ri savol IDlarini yig'ish
  const wrongIds   = [];
  const correctIds = [];
  answers.forEach((a, i) => {
    const qid = questions[i]?.id;
    if (!qid) return;
    if (a === 'wrong') wrongIds.push(qid);
    else if (a === 'correct') correctIds.push(qid);
    else if (typeof a === 'object' && a !== null) {
      const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
      if (allOk) correctIds.push(qid); else wrongIds.push(qid);
    }
  });

  const payload = JSON.stringify({
    correct, wrong, skip, total, score: pct,
    subject:        meta.subject        || 'onatili',
    category:       meta.category       || 'aralash',
    subcategory:    meta.subcategory    || null,
    difficulty:     meta.difficulty     || null,
    is_attestation: meta.is_attestation || false,
    wrong_ids:   wrongIds,
    correct_ids: correctIds,
  });

  console.log('sendResult chaqirildi, payload:', payload);
  if (tg) {
    console.log('tg.sendData chaqirilmoqda...');
    try {
      tg.sendData(payload);
      console.log('tg.sendData muvaffaqiyatli!');
    } catch(e) {
      console.error('tg.sendData xato:', e);
    }
  } else {
    console.warn('tg mavjud emas');
    alert(`Natija: ${pct}% (${correct}/${total})`);
  }
}

window.skipQuestion  = skipQuestion;
window.nextQuestion  = nextQuestion;
window.showResult    = showResult;
window.sendResult    = sendResult;
window.submitWritten = submitWritten;
window.retrySkipped  = retrySkipped;

loadQuestionsFromHash();