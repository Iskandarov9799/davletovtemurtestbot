// ════════════════════════════════════════════════
// TELEGRAM WEB APP
// GitHub Pages → tg.sendData() → Bot → DB
// ════════════════════════════════════════════════
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  tg.disableClosingConfirmation?.();
}

let questions  = [];
let answers    = [];
let current    = 0;
let score      = 0;
let answered   = false;
let meta       = {};
let resultSent = false;

const DEMO = [
  { id:1, t:"Fe'lning necha zamonlari bor?",      a:"2 ta", b:"3 ta", c:"4 ta", d:"5 ta",       ok:"B", type:"choice" },
  { id:2, t:"Qaysi so'z olmosh turkumiga kiradi?", a:"kitob", b:"men", c:"yaxshi", d:"yugurmoq", ok:"B", type:"choice" },
];

// ══════════════════════════════════════════════
// YUKLASH
// ══════════════════════════════════════════════
async function loadQuestionsFromHash() {
  showLoader(true);
  const params = new URLSearchParams(window.location.search);
  const hash   = params.get('data') || window.location.hash.slice(1);

  if (!hash) {
    questions = DEMO;
    meta      = { subject:'onatili', category:'demo', is_attestation:false };
    initTest();
    showLoader(false);
    return;
  }

  try {
    const b64    = hash.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(b64);
    const bytes  = Uint8Array.from(binary, c => c.charCodeAt(0));

    let jsonText;
    if (typeof DecompressionStream !== 'undefined') {
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
      let off = 0;
      for (const c of chunks) { out.set(c, off); off += c.length; }
      jsonText = new TextDecoder('utf-8').decode(out);
    } else {
      jsonText = decodeURIComponent(escape(binary));
    }

    const parsed = JSON.parse(jsonText);
    questions    = Array.isArray(parsed) ? parsed : (parsed.questions || parsed);
    meta         = Array.isArray(parsed) ? {} : (parsed.meta || {});
    console.log(`✅ ${questions.length} ta savol yuklandi`, meta);
    initTest();
  } catch (e) {
    console.error('Savollar yuklanmadi:', e);
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
    const el = document.getElementById('question-text') || document.getElementById('qtxt');
    if (el) el.textContent = '❌ Savollar topilmadi!';
    showLoader(false);
    return;
  }
  answers    = new Array(questions.length).fill(null);
  score      = 0;
  current    = 0;
  resultSent = false;

  const SUBJ = { onatili:'📚 Ona tili', adabiyot:'📖 Adabiyot' };
  const titleEl = document.getElementById('header-title') || document.getElementById('hdr-title');
  if (titleEl) titleEl.textContent = SUBJ[meta.subject] || '📚 Test';
  const subEl = document.getElementById('header-sub') || document.getElementById('hdr-sub');
  if (subEl) subEl.textContent = meta.category || '';

  if (tg) {
    tg.setHeaderColor?.('#0a0e1a');
    tg.setBackgroundColor?.('#0a0e1a');
  }

  buildGrid();
  renderQuestion(0);
  document.getElementById('test-screen').style.display   = 'block';
  document.getElementById('result-screen').style.display = 'none';
}

// ══════════════════════════════════════════════
// GRID — style.css: .grid-btn, .current, .g-correct, .g-wrong, .g-skip
// ══════════════════════════════════════════════
function buildGrid() {
  const g = document.getElementById('grid');
  if (!g) return;
  g.innerHTML = '';
  questions.forEach((q, i) => {
    const btn       = document.createElement('button');
    btn.className   = 'grid-btn' + (i === 0 ? ' current' : '');
    btn.id          = 'gb-' + i;
    btn.textContent = i + 1;
    if (isWritten(q)) btn.classList.add('written');
    btn.onclick = () => jumpTo(i);
    g.appendChild(btn);
  });
}

function updateGrid() {
  questions.forEach((q, i) => {
    const btn = document.getElementById('gb-' + i);
    if (!btn) return;
    btn.className = 'grid-btn' + (isWritten(q) ? ' written' : '');
    if      (i === current)            btn.classList.add('current');
    else if (answers[i] === 'correct') btn.classList.add('g-correct');
    else if (answers[i] === 'wrong')   btn.classList.add('g-wrong');
    else if (answers[i] === 'skip')    btn.classList.add('g-skip');
    else if (answers[i] && typeof answers[i] === 'object') {
      const allOk = answers[i].ok1 && (questions[i]?.written_parts < 2 || answers[i].ok2);
      btn.classList.add(allOk ? 'g-correct' : 'g-wrong');
    }
  });
}

function jumpTo(i) {
  if (answers[i] !== null && answers[i] !== 'skip') return;
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

  // Progress
  const pct = Math.round((i + 1) / total * 100);
  const fillEl = document.getElementById('progress-fill') || document.getElementById('prg-fill');
  if (fillEl) fillEl.style.width = pct + '%';
  const numEl = document.getElementById('progress-num') || document.getElementById('prg-label');
  if (numEl) numEl.textContent = `${i + 1} / ${total}`;
  const pctEl = document.getElementById('progress-pct') || document.getElementById('prg-pct');
  if (pctEl) pctEl.textContent = pct + '%';

  // Score
  const scoreEl = document.getElementById('score-badge') || document.getElementById('hdr-score');
  if (scoreEl) scoreEl.textContent = score + ' ball';

  // Savol
  const badgeEl = document.getElementById('question-badge') || document.getElementById('qnum');
  if (badgeEl) badgeEl.textContent = `SAVOL ${i + 1}`;
  const textEl = document.getElementById('question-text') || document.getElementById('qtxt');
  if (textEl) textEl.textContent = q.t || q.question_text || '';

  // Rasm
  const imgEl  = document.getElementById('question-img') || document.getElementById('qimg');
  if (imgEl) {
    const imgSrc = q.img || '';
    imgEl.style.display = imgSrc ? 'block' : 'none';
    if (imgSrc) imgEl.src = imgSrc;
  }

  // Feedback reset
  const fb = document.getElementById('feedback') || document.getElementById('fb');
  if (fb) { fb.className = 'feedback'; fb.style.display = 'none'; fb.innerHTML = ''; }

  // Tugmalar
  const btnSkip   = document.getElementById('btn-skip');
  const btnNext   = document.getElementById('btn-next');
  const btnFinish = document.getElementById('btn-finish');
  if (btnSkip)   btnSkip.style.display   = 'inline-flex';
  if (btnNext)   btnNext.style.display   = 'none';
  if (btnFinish) btnFinish.style.display = 'none';

  isWritten(q) ? renderWrittenQuestion(q) : renderChoiceQuestion(q);
  updateGrid();
}

// ══════════════════════════════════════════════
// VARIANTLAR — style.css: .option, .option-letter, .option-text
// ══════════════════════════════════════════════
function renderChoiceQuestion(q) {
  const opts = document.getElementById('options') || document.getElementById('opts');
  if (!opts) return;
  opts.innerHTML    = '';
  opts.style.display = 'flex';

  const wc = document.getElementById('written-container');
  if (wc) wc.style.display = 'none';

  const LBLS  = ['A', 'B', 'C', 'D'];
  const TEXTS = [q.a||'', q.b||'', q.c||'', q.d||''];
  LBLS.forEach((lbl, idx) => {
    if (!TEXTS[idx]) return;
    const div     = document.createElement('div');
    div.className = 'option';
    div.id        = 'opt-' + lbl;
    div.innerHTML = `<span class="option-letter">${lbl}</span><span class="option-text">${TEXTS[idx]}</span>`;
    div.onclick   = () => selectOption(lbl);
    opts.appendChild(div);
  });
}

function renderWrittenQuestion(q) {
  const opts = document.getElementById('options') || document.getElementById('opts');
  if (opts) { opts.innerHTML = ''; opts.style.display = 'none'; }

  let wc = document.getElementById('written-container');
  if (!wc) {
    wc    = document.createElement('div');
    wc.id = 'written-container';
    // question-card ichiga qo'shamiz
    const card = document.querySelector('.question-card') || document.querySelector('.qcard');
    if (card) card.appendChild(wc);
    else if (opts) opts.parentNode.insertBefore(wc, opts.nextSibling);
  }
  wc.style.display = 'block';

  const parts  = q.parts || q.written_parts || 1;
  wc.innerHTML = parts === 1 ? `
    <div class="written-hint">✏️ Javobingizni yozing:</div>
    <textarea id="written-ans-1" class="written-textarea" placeholder="Bu yerga javob yozing..." rows="4"></textarea>
    <button class="written-submit-btn" onclick="submitWritten()">✅ Javobni tekshirish</button>
  ` : `
    <div class="written-hint">✏️ Ikkita qism uchun javob yozing:</div>
    <div class="written-part-label">1-qism:</div>
    <textarea id="written-ans-1" class="written-textarea" placeholder="1-qism javobi..." rows="3"></textarea>
    <div class="written-part-label">2-qism:</div>
    <textarea id="written-ans-2" class="written-textarea" placeholder="2-qism javobi..." rows="3"></textarea>
    <button class="written-submit-btn" onclick="submitWritten()">✅ Javobni tekshirish</button>
  `;
}

// ══════════════════════════════════════════════
// VARIANT TANLASH
// style.css: .option.correct, .option.wrong, .option.show-correct, .option.disabled
// ══════════════════════════════════════════════
function selectOption(label) {
  if (answered) return;
  answered = true;

  const q       = questions[current];
  const correct = q.ok || q.correct_answer || '';
  const isOk    = label === correct;

  document.querySelectorAll('.option').forEach(o => {
    o.classList.add('disabled');
    o.onclick = null;
  });

  document.getElementById('opt-' + label)?.classList.add(isOk ? 'correct' : 'wrong');
  if (!isOk) document.getElementById('opt-' + correct)?.classList.add('show-correct');

  answers[current] = isOk ? 'correct' : 'wrong';
  if (isOk) score++;
  const scoreEl = document.getElementById('score-badge') || document.getElementById('hdr-score');
  if (scoreEl) scoreEl.textContent = score + ' ball';

  const TEXTS    = { A: q.a, B: q.b, C: q.c, D: q.d };
  const fb       = document.getElementById('feedback') || document.getElementById('fb');
  const solUrl   = meta.solution_url || '';
  const qid      = q.id || '';
  const linkHtml = solUrl
    ? `<br><a href="${solUrl}" target="_blank" style="color:inherit;font-size:12px;text-decoration:underline;">📹 Yechimni ko'rish (ID: ${qid})</a>`
    : (qid ? `<br><span style="font-size:11px;opacity:0.5;">ID: ${qid}</span>` : '');

  if (fb) {
    fb.style.display = 'flex';
    fb.className     = isOk ? 'feedback correct-fb' : 'feedback wrong-fb';
    fb.innerHTML     = isOk
      ? `✅ To'g'ri javob!${linkHtml}`
      : `❌ Noto'g'ri! To'g'ri: <b>${correct}) ${TEXTS[correct]||''}</b>${linkHtml}`;
  }

  const btnSkip = document.getElementById('btn-skip');
  if (btnSkip) btnSkip.style.display = 'none';
  checkAllDone();
  updateGrid();
  tg?.HapticFeedback?.impactOccurred(isOk ? 'medium' : 'heavy');
}

function checkAllDone() {
  const noUnanswered = answers.every(a => a !== null);
  const noSkipped    = !answers.some(a => a === 'skip');
  const btnNext   = document.getElementById('btn-next');
  const btnFinish = document.getElementById('btn-finish');
  if (noUnanswered && noSkipped) {
    if (btnNext)   btnNext.style.display   = 'none';
    if (btnFinish) btnFinish.style.display = 'inline-flex';
  } else {
    if (btnNext)   btnNext.style.display   = 'inline-flex';
    if (btnFinish) btnFinish.style.display = 'none';
  }
}

// ══════════════════════════════════════════════
// YOZMA JAVOB
// ══════════════════════════════════════════════
function checkKeywords(userText, keywordsStr) {
  if (!keywordsStr) return true;
  const kws = keywordsStr.split(',').map(k => k.trim().toLowerCase()).filter(Boolean);
  return !kws.length || kws.some(kw => userText.toLowerCase().includes(kw));
}

function submitWritten() {
  if (answered) return;
  const q      = questions[current];
  const parts  = q.parts || q.written_parts || 1;
  const ans1El = document.getElementById('written-ans-1');
  const ans1   = ans1El?.value.trim() || '';

  if (!ans1) {
    ans1El?.classList.add('shake');
    setTimeout(() => ans1El?.classList.remove('shake'), 500);
    return;
  }

  answered = true;
  if (ans1El) ans1El.disabled = true;
  let ans2 = '';
  const ans2El = document.getElementById('written-ans-2');
  if (ans2El) { ans2 = ans2El.value.trim(); ans2El.disabled = true; }
  const submitBtn = document.querySelector('.written-submit-btn');
  if (submitBtn) submitBtn.style.display = 'none';

  const kw1   = q.kw1 || q.keywords_1 || '';
  const kw2   = q.kw2 || q.keywords_2 || '';
  const ok1   = checkKeywords(ans1, kw1);
  const ok2   = parts < 2 ? true : checkKeywords(ans2, kw2);
  const allOk = ok1 && ok2;

  answers[current] = { w1: ans1, w2: ans2, ok1, ok2 };
  if (allOk) score++;
  const scoreEl = document.getElementById('score-badge') || document.getElementById('hdr-score');
  if (scoreEl) scoreEl.textContent = score + ' ball';

  const fb = document.getElementById('feedback') || document.getElementById('fb');
  if (fb) {
    fb.style.display = 'flex';
    if (parts === 1) {
      const hint   = (!ok1 && kw1) ? `<br>💡 Kalit so'z: <b>${kw1.split(',')[0].trim()}</b>` : '';
      fb.className = ok1 ? 'feedback correct-fb' : 'feedback wrong-fb';
      fb.innerHTML = ok1 ? `✅ <b>To'g'ri!</b>` : `❌ <b>Noto'g'ri.</b>${hint}`;
    } else {
      const hint1  = (!ok1 && kw1) ? ` (kalit: <b>${kw1.split(',')[0].trim()}</b>)` : '';
      const hint2  = (!ok2 && kw2) ? ` (kalit: <b>${kw2.split(',')[0].trim()}</b>)` : '';
      fb.className = allOk ? 'feedback correct-fb' : 'feedback wrong-fb';
      fb.innerHTML = `${ok1?'✅':'❌'} 1-qism${hint1}<br>${ok2?'✅':'❌'} 2-qism${hint2}`;
    }
  }

  const btnSkip = document.getElementById('btn-skip');
  if (btnSkip) btnSkip.style.display = 'none';
  checkAllDone();
  updateGrid();
  tg?.HapticFeedback?.notificationOccurred(allOk ? 'success' : 'error');
}

// ══════════════════════════════════════════════
// NAVIGATSIYA
// ══════════════════════════════════════════════
function skipQuestion() {
  answers[current] = 'skip';
  updateGrid();
  for (let i = current+1; i < questions.length; i++) { if (answers[i]===null)   { current=i; renderQuestion(i); return; } }
  for (let i = 0; i < current; i++)                  { if (answers[i]===null)   { current=i; renderQuestion(i); return; } }
  for (let i = current+1; i < questions.length; i++) { if (answers[i]==='skip') { current=i; renderQuestion(i); return; } }
  for (let i = 0; i < current; i++)                  { if (answers[i]==='skip') { current=i; renderQuestion(i); return; } }
  showResult();
}

function nextQuestion() {
  for (let i = current+1; i < questions.length; i++) { if (answers[i]===null)   { current=i; renderQuestion(i); return; } }
  for (let i = 0; i <= current; i++)                 { if (answers[i]===null)   { current=i; renderQuestion(i); return; } }
  for (let i = 0; i < questions.length; i++)         { if (answers[i]==='skip') { current=i; renderQuestion(i); return; } }
  showResult();
}

// ══════════════════════════════════════════════
// NATIJA
// style.css: .result-score, .stat-val, .result-grid-box, .grid-btn
// ══════════════════════════════════════════════
function showResult() {

  const total = questions.length;
  let correct = 0, wrong = 0, skip = 0;

  answers.forEach((a, i) => {
    if      (a === 'correct')             correct++;
    else if (a === 'wrong')              wrong++;
    else if (a === 'skip' || a === null) { skip++; wrong++; }
    else if (typeof a === 'object' && a) {
      const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
      allOk ? correct++ : wrong++;
    }
  });
  const wrongOnly = wrong - skip;
  const pct       = total > 0 ? Math.round(correct / total * 100) : 0;

  document.getElementById('test-screen').style.display   = 'none';
  document.getElementById('result-screen').style.display = 'flex';

  const [, emoji, grade] = [
    [90, '🏆', "A'lo (5)"],
    [70, '🎉', 'Yaxshi (4)'],
    [50, '📚', 'Qoniqarli (3)'],
    [0,  '😔', 'Qoniqarsiz (2)'],
  ].find(([min]) => pct >= min);

  // style.css elementlari
  const emojiEl = document.getElementById('result-emoji') || document.getElementById('r-emoji');
  const gradeEl = document.getElementById('result-grade') || document.getElementById('r-grade');
  const scoreEl = document.getElementById('result-score') || document.getElementById('r-score');
  const corrEl  = document.getElementById('stat-correct') || document.getElementById('r-correct');
  const wrongEl = document.getElementById('stat-wrong')   || document.getElementById('r-wrong');
  const skipEl  = document.getElementById('stat-skip')    || document.getElementById('r-skip');

  if (emojiEl) emojiEl.textContent = emoji;
  if (gradeEl) gradeEl.textContent = grade;
  if (scoreEl) scoreEl.textContent = pct + '%';
  if (corrEl)  corrEl.textContent  = correct;
  if (wrongEl) wrongEl.textContent = wrongOnly;
  if (skipEl)  skipEl.textContent  = skip;

  // Result grid — style.css: .grid-btn, .g-correct, .g-wrong, .g-skip
  const rg = document.getElementById('result-grid');
  if (rg) {
    rg.innerHTML = '';
    answers.forEach((a, i) => {
      const d = document.createElement('div');
      if      (a === 'correct')             d.className = 'grid-btn g-correct';
      else if (a === 'wrong')              d.className = 'grid-btn g-wrong';
      else if (a === 'skip' || a === null) {
        d.className    = 'grid-btn g-skip';
        d.onclick      = () => retrySkipped(i);
        d.style.cursor = 'pointer';
        d.title        = 'Bosing — qaytib ishlash';
      } else if (typeof a === 'object') {
        const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
        d.className = 'grid-btn written ' + (allOk ? 'g-correct' : 'g-wrong');
      }
      d.textContent = i + 1;
      rg.appendChild(d);
    });
  }

  // To'g'ri javoblar ro'yxati
  const answerList = document.getElementById('answer-list');
  if (answerList) {
    answerList.innerHTML = '';
    questions.forEach((q, i) => {
      if (isWritten(q)) return;
      const TEXTS      = { A:q.a, B:q.b, C:q.c, D:q.d };
      const correctKey = q.ok || q.correct_answer || '';
      const a          = answers[i];
      const icon       = a==='correct' ? '✅' : (a==='skip'||a===null) ? '⏭' : '❌';
      const div        = document.createElement('div');
      div.style.cssText = 'font-size:13px;padding:4px 0;border-bottom:0.5px solid rgba(255,255,255,0.08);';
      div.innerHTML = `${icon} <b>${i+1}.</b> ${q.t||''}<br><span style="opacity:0.7;font-size:12px;">✅ ${correctKey}) ${TEXTS[correctKey]||''}</span>`;
      answerList.appendChild(div);
    });
  }

  tg?.HapticFeedback?.notificationOccurred('success');

  if (!resultSent) {
    resultSent = true;
    sendResult({ correct, wrong: wrongOnly, skip, total, pct });
  }
}

function retrySkipped(idx) {
  document.getElementById('result-screen').style.display = 'none';
  document.getElementById('test-screen').style.display   = 'block';
  resultSent   = false;
  answers[idx] = null;
  current      = idx;
  renderQuestion(idx);
}

// ══════════════════════════════════════════════
// NATIJANI BOTGA YUBORISH — tg.sendData()
// ══════════════════════════════════════════════
function sendResult({ correct, wrong, skip, total, pct }) {
  alert('tg: ' + (tg ? 'bor' : 'YOQ') + ' | sendData: ' + (typeof tg?.sendData));
  const wrongIds   = [];
  const correctIds = [];
  answers.forEach((a, i) => {
    const qid = questions[i]?.id;
    if (!qid) return;
    if      (a==='wrong'||a==='skip'||a===null) wrongIds.push(qid);
    else if (a==='correct')                     correctIds.push(qid);
    else if (typeof a==='object' && a) {
      const allOk = a.ok1 && (questions[i]?.written_parts < 2 || a.ok2);
      allOk ? correctIds.push(qid) : wrongIds.push(qid);
    }
  });

  const payload = {
    correct, wrong, skip, total, score: pct,
    subject:        meta.subject        || 'onatili',
    category:       meta.category       || 'aralash',
    subcategory:    meta.subcategory    || null,
    difficulty:     meta.difficulty     || null,
    is_attestation: meta.is_attestation || false,
    wrong_ids:      wrongIds,
    correct_ids:    correctIds,
  };

  console.log('📤 sendData:', payload);

  if (tg && typeof tg.sendData === 'function') {
    try {
      tg.sendData(JSON.stringify(payload));
      setTimeout(() => tg.close(), 2500);
    } catch (e) {
      console.error('sendData xato:', e);
    }
  } else {
    console.warn('tg.sendData yo\'q — demo rejimi');
  }
}

// ══════════════════════════════════════════════
window.skipQuestion  = skipQuestion;
window.nextQuestion  = nextQuestion;
window.showResult    = showResult;
window.submitWritten = submitWritten;
window.retrySkipped  = retrySkipped;

loadQuestionsFromHash();
