// ════════════════════════════════════════════════
// TELEGRAM WEB APP
// ════════════════════════════════════════════════
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.disableClosingConfirmation?.();
}

// ════════════════════════════════════════════════
// HOLAT (STATE)
// ════════════════════════════════════════════════
let questions = [];
let answers   = [];   // null | 'correct' | 'wrong' | 'skip'
let current   = 0;
let score     = 0;
let answered  = false;
let meta      = {};   // subject, category, subcategory, difficulty, is_attestation

// ════════════════════════════════════════════════
// DEMO — hash bo'lmasa ishlatiladi
// ════════════════════════════════════════════════
const DEMO = [
  { id:1,  t:"Fe'lning necha zamonlari bor?",            a:"2 ta",    b:"3 ta",    c:"4 ta",   d:"5 ta",              ok:"B", img:"" },
  { id:2,  t:"Qaysi so'z olmosh turkumiga kiradi?",      a:"kitob",   b:"men",     c:"yaxshi", d:"yugurmoq",          ok:"B", img:"" },
  { id:3,  t:"O'zbek tilida unli tovushlar soni nechta?",a:"5",       b:"6",       c:"7",      d:"8",                 ok:"B", img:"" },
  { id:4,  t:"Ko'plik qo'shimchasi qaysi?",              a:"-ning",   b:"-lar",    c:"-ga",    d:"-dan",              ok:"B", img:"" },
  { id:5,  t:"Antonim nima?",                            a:"Ma'nodosh so'zlar", b:"Qarama-qarshi ma'noli so'zlar", c:"Shakldosh so'zlar", d:"Ko'p ma'noli so'zlar", ok:"B", img:"" },
];

// ════════════════════════════════════════════════
// HASH DAN SAVOLLAR + META O'QISH
// Format: base64url(zlib(JSON({meta, questions})))
// ════════════════════════════════════════════════
async function loadQuestionsFromHash() {
  showLoader(true);
  // ?data= query param dan o'qish (hash ishlamaydi WebAppInfo da)
  const params = new URLSearchParams(window.location.search);
  const hash   = params.get('data') || window.location.hash.slice(1);

  if (!hash) {
    console.warn('Data yo\'q — demo ishlatiladi');
    questions = DEMO;
    meta      = { subject:'onatili', category:'aralash', difficulty:'easy', is_attestation:false };
    initTest();
    showLoader(false);
    return;
  }

  try {
    // base64url → bytes
    const b64    = hash.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(b64);
    const bytes  = Uint8Array.from(binary, c => c.charCodeAt(0));

    // zlib decompress
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

    // Format: {meta:{...}, questions:[...]} YOKI to'g'ridan massiv
    if (Array.isArray(parsed)) {
      questions = parsed;
      meta      = {};
    } else {
      questions = parsed.questions || parsed;
      meta      = parsed.meta      || {};
    }

    console.log(`✅ ${questions.length} ta savol yuklandi`, meta);
    initTest();

  } catch (e) {
    console.error('Hash xatosi:', e);
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

// ════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════
function initTest() {
  if (!questions.length) {
    document.getElementById('question-text').textContent = '❌ Savollar topilmadi!';
    return;
  }
  answers = new Array(questions.length).fill(null);
  score   = 0;
  current = 0;

  // Sarlavha
  const SUBJ = { onatili:'📚 Ona tili', adabiyot:'📖 Adabiyot' };
  const DIFF = { easy:'🟢 Oson', medium:"🟡 O'rta", hard:'🔴 Qiyin' };
  const title = SUBJ[meta.subject] || '📚 Test';
  const sub   = meta.subcategory ? ` › ${meta.subcategory}` : '';
  const diff  = DIFF[meta.difficulty] || '';
  document.getElementById('header-title').textContent = title;
  const subEl = document.getElementById('header-sub');
  if (subEl) subEl.textContent = (meta.category || '') + sub + (diff ? ' · ' + diff : '');

  // Telegram sarlavha rangi
  if (tg) {
    tg.setHeaderColor?.('#0a0e1a');
    tg.setBackgroundColor?.('#0a0e1a');
  }

  buildGrid();
  renderQuestion(0);
  document.getElementById('test-screen').style.display  = 'block';
  document.getElementById('result-screen').style.display = 'none';
}

// ════════════════════════════════════════════════
// GRID (savollar paneli)
// ════════════════════════════════════════════════
function buildGrid() {
  const g = document.getElementById('grid');
  g.innerHTML = '';
  questions.forEach((_, i) => {
    const btn       = document.createElement('button');
    btn.className   = 'grid-btn' + (i === 0 ? ' current' : '');
    btn.id          = 'gb-' + i;
    btn.textContent = i + 1;
    btn.onclick     = () => jumpTo(i);
    g.appendChild(btn);
  });
}

function updateGrid() {
  questions.forEach((_, i) => {
    const btn = document.getElementById('gb-' + i);
    if (!btn) return;
    btn.className = 'grid-btn';
    if      (i === current)            btn.classList.add('current');
    else if (answers[i] === 'correct') btn.classList.add('g-correct');
    else if (answers[i] === 'wrong')   btn.classList.add('g-wrong');
    else if (answers[i] === 'skip')    btn.classList.add('g-skip');
  });
}

function jumpTo(i) {
  // Faqat javob berilmagan savollarga o'tish mumkin
  if (answers[i] !== null) return;
  current = i;
  renderQuestion(i);
}

// ════════════════════════════════════════════════
// SAVOL RENDER
// ════════════════════════════════════════════════
function renderQuestion(i) {
  answered = false;
  const q     = questions[i];
  const total = questions.length;

  // Matn (minimal yoki to'liq format)
  const qText = q.t || q.question_text || '';

  // Progress
  const pct = Math.round((i + 1) / total * 100);
  document.getElementById('progress-fill').style.width  = pct + '%';
  document.getElementById('progress-label').textContent = `${i + 1} / ${total}`;
  const pctEl = document.getElementById('progress-pct');
  if (pctEl) pctEl.textContent = pct + '%';
  document.getElementById('score-badge').textContent    = score + ' ball';

  // Savol
  document.getElementById('question-num').textContent  = `SAVOL ${i + 1}`;
  document.getElementById('question-text').textContent = qText;

  // Rasm
  const imgEl  = document.getElementById('question-img');
  const imgSrc = q.img || '';
  imgEl.style.display = imgSrc ? 'block' : 'none';
  if (imgSrc) imgEl.src = imgSrc;

  // Variantlar
  const opts   = document.getElementById('options');
  opts.innerHTML = '';
  const LBLS   = ['A', 'B', 'C', 'D'];
  const TEXTS  = [q.a||'', q.b||'', q.c||'', q.d||''];

  LBLS.forEach((lbl, idx) => {
    const div = document.createElement('div');
    div.className = 'option';
    div.id        = 'opt-' + lbl;
    div.innerHTML = `<span class="option-letter">${lbl}</span><span class="option-text">${TEXTS[idx]}</span>`;
    div.onclick   = () => selectOption(lbl);
    opts.appendChild(div);
  });

  // Feedback yashirish
  const fb = document.getElementById('feedback');
  fb.className     = 'feedback';
  fb.style.display = 'none';
  fb.innerHTML     = '';

  // Tugmalar
  document.getElementById('btn-skip').style.display   = 'inline-flex';
  document.getElementById('btn-next').style.display   = 'none';
  document.getElementById('btn-finish').style.display = 'none';

  updateGrid();
}

// ════════════════════════════════════════════════
// VARIANT TANLASH
// ════════════════════════════════════════════════
function selectOption(label) {
  if (answered) return;
  answered = true;

  const q       = questions[current];
  const correct = q.ok || q.correct_answer || '';
  const isOk    = label === correct;

  // Barcha variantlarni o'chirish
  document.querySelectorAll('.option').forEach(o => {
    o.classList.add('disabled');
    o.onclick = null;
  });

  // Ranglar
  document.getElementById('opt-' + label).classList.add(isOk ? 'correct' : 'wrong');
  if (!isOk) document.getElementById('opt-' + correct)?.classList.add('show-correct');

  // Holat yangilash
  answers[current] = isOk ? 'correct' : 'wrong';
  if (isOk) score++;
  document.getElementById('score-badge').textContent = score + ' ball';

  // Feedback
  const TEXTS = { A: q.a, B: q.b, C: q.c, D: q.d };
  const fb    = document.getElementById('feedback');
  fb.style.display = 'block';
  if (isOk) {
    fb.className = 'feedback fb-correct';
    fb.innerHTML = '✅ To\'g\'ri javob!';
  } else {
    fb.className = 'feedback fb-wrong';
    fb.innerHTML = `❌ Noto'g'ri! To'g'ri: <b>${correct}) ${TEXTS[correct] || ''}</b>`;
  }

  // Keyingi tugma
  document.getElementById('btn-skip').style.display = 'none';
  const isLast = current === questions.length - 1;
  const allDone = answers.every(a => a !== null);
  if (allDone || isLast) {
    document.getElementById('btn-finish').style.display = 'inline-flex';
  } else {
    document.getElementById('btn-next').style.display = 'inline-flex';
  }

  updateGrid();
  tg?.HapticFeedback?.impactOccurred(isOk ? 'medium' : 'heavy');
}

// ════════════════════════════════════════════════
// O'TKAZISH / KEYINGI
// ════════════════════════════════════════════════
function skipQuestion() {
  answers[current] = 'skip';
  updateGrid();
  const next = findNext(current + 1);
  if (next !== -1) { current = next; renderQuestion(current); }
  else showResult();
}

function nextQuestion() {
  const next = findNext(current + 1);
  if (next !== -1) { current = next; renderQuestion(current); }
  else showResult();
}

function findNext(from) {
  for (let i = from; i < questions.length; i++) {
    if (answers[i] === null) return i;
  }
  // Boshidan ham izlash (o'tkazilgan savollar)
  for (let i = 0; i < from; i++) {
    if (answers[i] === null) return i;
  }
  return -1;
}

// ════════════════════════════════════════════════
// NATIJA EKRANI
// ════════════════════════════════════════════════
function showResult() {
  const total   = questions.length;
  const correct = answers.filter(a => a === 'correct').length;
  const wrong   = answers.filter(a => a === 'wrong').length;
  const skip    = answers.filter(a => a === 'skip' || a === null).length;
  const pct     = total > 0 ? Math.round(correct / total * 100) : 0;

  document.getElementById('test-screen').style.display   = 'none';
  document.getElementById('result-screen').style.display = 'flex';

  // Baho
  const grades = [
    [90, '🏆', "A'lo (5)", '#22c55e'],
    [70, '🎉', 'Yaxshi (4)', '#3b82f6'],
    [50, '📚', 'Qoniqarli (3)', '#f59e0b'],
    [0,  '😔', 'Qoniqarsiz (2)', '#ef4444'],
  ];
  const [, emoji, grade, color] = grades.find(([min]) => pct >= min);

  document.getElementById('result-emoji').textContent  = emoji;
  document.getElementById('result-grade').textContent  = grade;
  document.getElementById('result-score').textContent  = pct + '%';
  document.getElementById('result-score').style.color  = color;
  document.getElementById('r-correct').textContent     = correct;
  document.getElementById('r-wrong').textContent       = wrong;
  document.getElementById('r-skip').textContent        = skip;

  // Natija gridi
  const rg = document.getElementById('result-grid');
  rg.innerHTML = '';
  const colMap = { correct:'#22c55e', wrong:'#ef4444', skip:'#f59e0b' };
  answers.forEach((a, i) => {
    const d = document.createElement('div');
    d.className   = 'rgrid-cell';
    d.style.background = colMap[a] || '#2a2a40';
    d.style.color      = a ? 'white' : '#6b6b8a';
    d.textContent = i + 1;
    rg.appendChild(d);
  });

  // Yuborish tugmasi
  if (tg) {
    tg.MainButton.setText('📤 Natijani yuborish');
    tg.MainButton.show();
    tg.MainButton.onClick(sendResult);
  }
  tg?.HapticFeedback?.notificationOccurred('success');
}

// ════════════════════════════════════════════════
// NATIJA YUBORISH → BOT
// ════════════════════════════════════════════════
function sendResult() {
  const total   = questions.length;
  const correct = answers.filter(a => a === 'correct').length;
  const wrong   = answers.filter(a => a === 'wrong').length;
  const skip    = answers.filter(a => a === 'skip' || a === null).length;
  const pct     = total > 0 ? Math.round(correct / total * 100) : 0;

  const payload = JSON.stringify({
    correct,
    wrong,
    skip,
    total,
    score:          pct,
    // Meta — bot tomonida natijani to'g'ri saqlash uchun
    subject:        meta.subject        || 'onatili',
    category:       meta.category       || 'aralash',
    subcategory:    meta.subcategory    || null,
    difficulty:     meta.difficulty     || null,
    is_attestation: meta.is_attestation || false,
  });

  if (tg) {
    tg.sendData(payload);
  } else {
    alert(`Natija: ${pct}% (${correct}/${total})`);
  }
}

// ════════════════════════════════════════════════
// GLOBAL — HTML inline onclick uchun
// ════════════════════════════════════════════════
window.skipQuestion = skipQuestion;
window.nextQuestion = nextQuestion;
window.showResult   = showResult;
window.sendResult   = sendResult;

// ════════════════════════════════════════════════
// START
// ════════════════════════════════════════════════
loadQuestionsFromHash();