// Afk token — интерфейс «Стекло» (1.6).
// Открыт просто в браузере — работает как демо. Запущен программой (pywebview) — управляет настоящим ботом.
(function () {
  const TG = 'kk4ose';
  const KEY_RE = /^AFK(-[A-Z0-9]{4}){4}$/;
  const STATE_TXT = { stopped: 'Остановлен', loading: 'Загрузка…', running: 'Бот работает', paused: 'На паузе' };
  const TIER_NAME = { free: 'Free', vip: 'VIP', premium: 'Premium', ultimate: 'Ultimate' };
  const LOCK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path></svg>';

  // функции бота: [ключ настройки, название, уровень, подсказка]
  const FEATS = {
    base: [
      ['auto_play', 'Авто-запуск матча', 'free', 'Сам запускает Королевскую битву и жмёт «Играть снова»'],
      ['auto_jump', 'Прыжок с автобуса', 'free', 'Ждёт подсказку «Прыгнуть» и прыгает'],
      ['auto_pause', 'Умная пауза', 'free', 'Встаёт на паузу, когда ты сел за ПК']
    ],
    // бывшие VIP-функции показываются как Premium (у владельцев VIP-ключей они остаются открыты)
    premium: [
      ['skip_rewards', 'Пропуск наград', 'vip', 'Забирает награды и закрывает окна'],
      ['auto_restart', 'Перезапуск при ошибке', 'vip', 'Перезапускает игру, если она вылетела или зависла'],
      ['anti_afk', 'Анти-AFK (жмёт W)', 'vip', 'Двигает персонажа, чтобы игра не выкинула'],
      ['explore', 'Бег', 'vip', 'После приземления бегает по карте, чтобы не выкинуло'],
      ['reward_shots', 'Скрин награды', 'vip', 'Сохраняет скрин награды в папку rewards и шлёт в Telegram'],
      ['monitor_off', 'Гасить монитор', 'vip', 'Выключает монитор, пока программа работает без тебя'],
      ['tg_enabled', 'Награды в Telegram', 'vip', 'Награды и отчёты приходят в Telegram (настрой во вкладке «Настройки»)'],
      ['tg_menu', 'Пульт в Telegram', 'premium', 'Кнопки управления и авто-скрины'],
      ['goal_on', 'Фарм под цель', 'premium', 'Работает до цели и сам останавливается'],
      ['sched_on', 'Расписание', 'premium', 'Сам включается и выключается по времени'],
      ['net_guard', 'Ждать при пропаже интернета', 'premium', 'Ничего не жмёт, пока нет сети'],
      ['human_afk', 'Анти-кик «как человек»', 'premium', 'Стрейфы, прыжки и повороты вместо одного W'],
      ['weekly_report', 'Недельный отчёт', 'premium', 'Картинка-отчёт в Telegram по воскресеньям']
    ],
    // с 1.6 все эти функции открыты только на Ultimate (доступ проверяет программа)
    ultimate: [
      ['obstacle_nav', 'Обход препятствий', 'ultimate', 'Не застревает: перепрыгивает, обходит, разворачивается'],
      ['smooth_mouse', 'Плавные движения мышкой', 'ultimate', 'Камера поворачивается как у живого игрока'],
      ['zone_nav', 'Уход от зоны', 'ultimate', 'Компас и миникарта: уходит от шторма и не лезет в воду'],
      ['team_check', 'Выход, если остался один', 'ultimate', 'Тиммейты выбыли — выходит и ищет новую катку'],
      ['auto_leave', 'Выход после смерти команды', 'vip', 'Выходит, когда команда погибла или матч закончился'],
      ['sprint', 'Спринт и живые движения', 'vip', 'Иногда зажимает Shift и стрейфит'],
      ['land_mode', 'Точка высадки', 'premium', 'Прыгает в начале, середине или конце маршрута'],
      ['low_gfx', 'Низкая графика на время фарма', 'premium', 'Потом возвращает как было']
    ]
  };
  // настройки: [заголовок группы, ключ-замок или null, [поля]]
  const SETTINGS = [
    ['Катка', null, [
      { k: 'team_size', t: 'sel', l: 'Режим в лобби', o: { solo: 'Соло', duos: 'Дуо', trios: 'Трио', squads: 'Отряды' } },
      { k: 'jump_delay', t: 'num', l: 'Прыгать через, сек', min: 0, max: 60 },
      { k: 'max_match_min', t: 'num', l: 'Выход через ESC после, мин', min: 10, max: 120 },
      { k: 'stuck_min', t: 'num', l: 'Перезапуск, если экран завис, мин', min: 5, max: 120 }]],
    ['Анти-AFK и сундуки', null, [
      { k: 'afk_hold', t: 'num', l: 'Держать W, сек', min: 1, max: 300 },
      { k: 'afk_pause', t: 'num', l: 'Пауза между зажатиями, сек', min: 5, max: 600 },
      { k: 'turn_speed', t: 'num', l: 'Чувствительность поворота', min: 100, max: 3000 },
      { k: 'explore_delay', t: 'num', l: 'Макс. ждать приземления, сек', min: 10, max: 180 }]],
    ['Человеческие повороты мышкой · Ultimate', 'smooth_mouse', [
      { k: 'scan_turns', t: 'num', l: 'Сколько поворотов мышкой за раз', min: 1, max: 6 },
      { k: 'scan_every', t: 'num', l: 'Как часто оглядываться, сек', min: 10, max: 180 }]],
    ['Высадка и цель', 'goal_on', [
      { k: 'land_spot', t: 'sel', l: 'Где прыгать', o: { start: 'Начало', mid: 'Середина', end: 'Конец', random: 'Рандом' } },
      { k: 'goal_type', t: 'sel', l: 'Цель', o: { matches: 'Каток', rewards: 'Наград', chests: 'Сундуков', token: 'Токен' } },
      { k: 'goal_value', t: 'num', l: 'Сколько', min: 1, max: 9999 },
      { k: 'goal_action', t: 'sel', l: 'Когда цель выполнена', o: { stop: 'Остановить', close: 'Закрыть игру', shutdown: 'Выключить ПК' } }]],
    ['Расписание · Premium', 'sched_on', [
      { k: 'sched_from', t: 'time', l: 'С' }, { k: 'sched_to', t: 'time', l: 'До' },
      { k: 'sched_days', t: 'text', l: 'Дни недели (1 = пн … 7 = вс)', w: 90 },
      { k: 'shot_every', t: 'num', l: 'Авто-скрин в Telegram раз в, мин (0 = выкл)', min: 0, max: 240 }]],
    ['Зона · Ultimate', 'zone_nav', [
      { k: 'storm_nav', t: 'bool', l: 'Уходить от шторма (по цвету миникарты)' }]],
    ['Программа', null, [
      { k: 'auto_update', t: 'bool', l: 'Обновляться автоматически' },
      { k: 'tg_reports', t: 'bool', l: 'Отчёты в Telegram' },
      { k: 'report_min', t: 'num', l: 'Отчёт раз в, мин', min: 5, max: 1440 },
      { k: 'tg_match', t: 'bool', l: 'Сообщать о каждой катке' },
      { k: 'tg_control', t: 'bool', l: 'Команды из Telegram (/status /start /stop)' },
      { k: 'token_alert', t: 'bool', l: 'Громкий сигнал, если выпал Пиратский токен' },
      { k: 'resume_min', t: 'num', l: 'Снять паузу, если тебя нет, мин', min: 1, max: 60 },
      { k: 'fps_limit', t: 'num', l: 'Ограничить FPS игры (0 = не трогать)', min: 0, max: 240 }]]
  ];
  const FAQ = [
    ['Как запустить?', 'Открой Fortnite в режиме «Оконный без рамок», дождись лобби, включи нужные функции и нажми СТАРТ. F9 — пауза, F10 — стоп.'],
    ['Ключ работает навсегда?', 'Да. Ключ покупается один раз, без подписки. Один ключ — один компьютер.'],
    ['Как активировать ключ?', 'Нажми плашку слева внизу и вставь ключ.'],
    ['Чем отличаются уровни?', 'Premium — фарм без остановки, Telegram, цель и расписание. Ultimate — всё из Premium плюс умный бег: сундуки, обход препятствий, плавная мышь, уход от зоны, точка высадки.'],
    ['Можно свернуть Fortnite?', 'Нет, окно игры должно оставаться открытым.'],
    ['Игра вылетела или зависла?', 'Включи «Перезапуск при ошибке» — программа сама перезапустит игру.'],
    ['Как приходят обновления?', 'Программа сама проверяет новую версию при запуске и предлагает обновиться.'],
    ['Как предложить идею или сообщить об ошибке?', 'Вкладка «Предложения» → «Создать тикет». Ответ создателя появится там же.'],
    ['Где чат и рефералы?', 'Пока в классическом окне: вкладка «Создатель» → «Открыть классическое окно».'],
    ['Это безопасно?', 'Правила Epic Games запрещают автоматизацию. Аккаунт могут ограничить или заблокировать. Используешь на свой риск.'],
    ['Есть проблема или вопрос?', 'Пиши в Telegram: @kk4ose и приложи файл logs/afk_token.log.']
  ];

  const st = {
    tab: 'func', ftab: 'base', state: 'stopped', real: false, checking: false, stats: null, version: '', rev: -1,
    hasKey: false, tier: 'free', admin: false, free: false, hasTg: false,
    settings: { auto_play: true, auto_jump: true, auto_pause: true, auto_leave: true, skip_rewards: true, auto_restart: true,
      anti_afk: false, explore: true, sprint: true, storm_nav: true, team_size: 'squads', jump_delay: 10, max_match_min: 35,
      stuck_min: 15, afk_hold: 30, afk_pause: 30, turn_speed: 800, explore_delay: 90, land_spot: 'mid', goal_type: 'matches',
      goal_value: 20, goal_action: 'stop', sched_from: '23:00', sched_to: '07:00', sched_days: '1234567', shot_every: 0,
      auto_update: true, report_min: 60, resume_min: 3, fps_limit: 0, tg_chat: '' },
    allowed: {}, shop: { price_vip: '79', price_premium: '159', price_upgrade: '99', price_ultimate: '249' },
    logs: [[new Date().toTimeString().slice(0, 8), 'Активируй ключ, чтобы запустить программу']],
    adm: { rows: [], sel: null, q: '', f: 'all', loaded: false }, updShown: false,
    sug: { mine: [], all: [], loaded: false, f: 'new', error: '' },
    chat: { msgs: [], lastId: 0, nick: null, muted: false, online: 0, busy: false, nickEditing: false, unread: 0, err: '' }
  };
  const $ = (q, r = document) => r.querySelector(q);
  const $$ = (q, r = document) => Array.from(r.querySelectorAll(q));
  const esc = (t) => String(t == null ? '' : t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const now = () => new Date().toTimeString().slice(0, 8);
  const py = () => (window.pywebview && window.pywebview.api) || null;
  const busy = () => st.state !== 'stopped';
  // под какой плашкой показывать функцию. Доступ решает программа (allowed), а не эта таблица.
  const SHOW_AS = { auto_leave: 'ultimate', low_gfx: 'ultimate', land_mode: 'ultimate', sprint: 'ultimate' };
  const shown = (tier, k) => SHOW_AS[k] || (tier === 'vip' ? 'premium' : tier);   // плашки VIP нет: показываем Premium
  const TIER_RANK = { free: 0, vip: 1, premium: 2, ultimate: 3 };
  const can = (k, tier) => (st.real ? !!st.allowed[k] : (tier === 'free' || (st.hasKey && TIER_RANK[st.tier] >= TIER_RANK[tier])));
  const tabs = () => [['home', 'Главная'], ['func', 'Функции'], ['set', 'Настройки'], ['shop', 'Магазин'], ['sug', 'Предложения'], ['faq', 'FAQ'], ['chat', 'Чат'],
    ['resell', 'Реселлерам'], ['about', 'Тех поддержка']].concat(st.admin ? [['admin', 'Админ']] : []);
  const TITLES = { home: 'Главная', func: 'Функции бота', set: 'Настройки', shop: 'Магазин', sug: 'Предложения', faq: 'FAQ', chat: 'Чат', resell: 'Реселлерам', about: 'Тех поддержка', admin: 'Админ' };

  // ---------- мелочи ----------
  function shake(el) { if (!el) return; el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake'); }
  function toast(text, ok) {
    const t = document.createElement('div');
    t.className = 'toast' + (ok === false ? ' bad' : '');
    t.textContent = text;
    $('#win').appendChild(t);
    setTimeout(() => t.remove(), 3600);
  }
  function closeModal() { $('#overlay').innerHTML = ''; }
  // ---------- донаты ----------
  const DONATE = {
    usdt: 'TEFSXkssi9s6JdmpHuqXtfMwHwJK3U8zPm',            // USDT, сеть TRON (TRC20)
    gram: 'UQAIeqdKrk9zbYPMpBpKPuLRoc1TuXh_0Sq_u2jz074H6AyR', // GRAM, сеть TON
    donatepay: 'https://new.donatepay.ru/donate/1543816',    // карта: RUB / USD / EUR / UAH
  };
  function donateModal() {
    const rows = [
      `<a class="dnrow" href="https://t.me/${TG}" target="_blank" rel="noopener"><span class="dni">⭐</span><span><b>Telegram Stars</b><small>Любое количество: от платного сообщения до подарка-мишки 🧸 — отправь @${TG}</small></span></a>`,
      `<a class="dnrow" href="${DONATE.donatepay}" target="_blank" rel="noopener"><span class="dni">💳</span><span><b>Картой · DonatePay</b><small>RUB, USD, EUR, UAH — любая сумма</small></span></a>`,
      `<button class="dnrow" data-copy="${esc(DONATE.usdt)}"><span class="dni">💵</span><span><b>USDT · сеть TRON (TRC20)</b><small class="dnaddr">${esc(DONATE.usdt)}</small><small class="dnhint">Нажми, чтобы скопировать адрес</small></span></button>`,
      `<button class="dnrow" data-copy="${esc(DONATE.gram)}"><span class="dni">💎</span><span><b>GRAM · сеть TON</b><small class="dnaddr">${esc(DONATE.gram)}</small><small class="dnhint">Нажми, чтобы скопировать адрес</small></span></button>`,
    ];
    modal(`<div class="dnhead"><span class="dnheart">💜</span><h2>Поддержать Afk token</h2>
      <p class="muted">Донаты идут на развитие: новые функции, быстрые обновы и сервер. Выбери, как удобно — любая сумма, спасибо!</p></div>
      <div class="dnlist">${rows.join('')}</div>
      <p class="dnwarn">Крипту отправляй только в указанной сети, иначе перевод потеряется.</p>
      <div class="mrow"><button class="mbtn ghost" data-close>Закрыть</button></div>`, (ov) => {
      ov.querySelectorAll('[data-copy]').forEach((b) => b.onclick = async () => {
        const r = await call('copy', b.dataset.copy);
        const bad = r === false || (r && r.ok === false);
        toast(bad ? 'Не удалось скопировать' : 'Адрес скопирован', !bad);
      });
    });
  }
  function modal(html, mount) {
    $('#overlay').innerHTML = `<div class="overlay" id="ov"><div class="modal" role="dialog" aria-modal="true">${html}</div></div>`;
    $('#ov').addEventListener('mousedown', (e) => { if (e.target.id === 'ov') closeModal(); });
    $$('#ov [data-close]').forEach((b) => b.onclick = closeModal);
    if (mount) mount($('#ov'));
  }
  function confirmBox(text, yes, onYes) {
    modal(`<h2>Точно?</h2><p class="muted">${esc(text)}</p><div class="mrow"><button class="mbtn" id="cy">${esc(yes)}</button><button class="mbtn ghost" data-close>Отмена</button></div>`,
      () => { $('#cy').onclick = () => { closeModal(); onYes(); }; });
  }
  async function call(name, ...args) {
    try { return await py()[name](...args); } catch (e) { return { ok: false, error: String(e) }; }
  }

  // ---------- меню ----------
  function renderNav() {
    const nav = $('#nav'), list = tabs();
    if (!list.some((t) => t[0] === st.tab)) st.tab = 'func';
    const idx = list.findIndex((t) => t[0] === st.tab);
    nav.innerHTML = '<span class="ind" id="ind"></span>' + list.map(([id, t]) => {
      const lbl = (id === 'chat' && st.chat.unread) ? `${t} (${Math.min(st.chat.unread, 99)})` : t;
      return `<button class="tab${id === st.tab ? ' active' : ''}" data-id="${id}">${lbl}</button>`;
    }).join('');
    $('#ind').style.top = idx * 48 + 'px';
    $$('.tab', nav).forEach((b) => b.onclick = () => setTab(b.dataset.id));
  }
  function setTab(id) {
    st.tab = id;
    const list = tabs();
    $$('.tab').forEach((b) => b.classList.toggle('active', b.dataset.id === id));
    $('#ind').style.top = list.findIndex((t) => t[0] === id) * 48 + 'px';
    $('#title').textContent = TITLES[id];
    renderPage();
    if (id === 'admin' && st.real && !st.adm.loaded) admLoad();
    if (id === 'sug') sugLoad();
    if (id === 'chat') { st.chat.unread = 0; renderNav(); chatTick(true); }
  }

  // ---------- журнал и состояние ----------
  function renderLogs() {
    const box = $('#logs');
    if (!box) return;
    box.innerHTML = st.logs.map((l, i) =>
      `<div class="log${i === st.logs.length - 1 && st.fresh ? ' new' : ''}"><span class="lt">${esc(l[0])}</span><span>${esc(l[1])}</span></div>`).join('');
    st.fresh = false;
    box.scrollTop = box.scrollHeight;
  }
  function addLog(m, t) {
    st.logs.push([t || now(), m]);
    st.logs = st.logs.slice(st.real ? -200 : -6);
    st.fresh = true;
    renderLogs();
  }
  function statsLine() {
    const s = st.stats;
    if (!s) return 'Королевская битва · Отряды';
    return `Каток: ${s.matches} · Сундуков: ${s.chests} · Наград: ${s.rewards} · Работает: ${s.time}`;
  }
  function setState(s) {
    if (s === st.state) return;
    st.state = s;
    $('#dot').className = 'dot' + (s === 'running' ? '' : ' off');
    $('#status').textContent = STATE_TXT[s];
    $('#win').classList.toggle('paused', s !== 'running');
    $$('.start').forEach((btn) => {
      btn.classList.toggle('idle', !busy());
      const want = busy() ? 'СТОП' : 'СТАРТ';
      if ($('.flip', btn).textContent !== want) $('.flip', btn).outerHTML = `<span class="flip">${want}</span>`;
    });
    const big = $('#bigst');
    if (big) big.textContent = STATE_TXT[s];
  }
  async function onStart(e) {
    const btn = e.currentTarget;
    if (!st.hasKey && !st.free) { shake(btn); openKey(); return; }
    const r = document.createElement('span'); r.className = 'ripple'; btn.appendChild(r); setTimeout(() => r.remove(), 600);
    if (!st.real) {
      const next = busy() ? 'stopped' : 'running';
      setState(next);
      addLog(next === 'running' ? 'Бот запущен' : 'Бот остановлен');
      return;
    }
    if (busy()) { py().stop_bot(); return; }
    setState('loading');
    addLog('Проверяю ключ на сервере…');
    const res = await call('start_bot');
    if (!res || !res.ok) {
      setState('stopped');
      addLog('Не запустился: ' + ((res && res.error) || 'ошибка'));
      if (res && res.need_key) openKey();
    }
  }
  const startBtn = () => `<button class="start${busy() ? '' : ' idle'}"><span class="flip">${busy() ? 'СТОП' : 'СТАРТ'}</span></button>`;

  // ---------- страницы ----------
  function pageFunc() {
    const seg = [['base', 'Основные'], ['premium', 'Premium'], ['ultimate', 'Ultimate']].map(([id, t]) =>
      `<button class="segb${st.ftab === id ? ' on' : ''}" data-f="${id}">${t}</button>`).join('');
    const cards = FEATS[st.ftab].map(([k, name, tier, hint], i) => {
      const ok = can(k, tier);
      return `<div class="feat${ok ? '' : ' locked'}" data-k="${k}" data-tier="${shown(tier, k)}" title="${esc(hint)}" style="animation-delay:${(0.05 + i * 0.04).toFixed(2)}s">
        <span class="glare"></span><span class="fname">${name}</span>
        <span class="tier t-${shown(tier, k)}">${TIER_NAME[shown(tier, k)]}</span>${ok ? '' : `<span class="lock">${LOCK}</span>`}
        <button class="sw${ok && st.settings[k] ? ' on' : ''}" aria-pressed="${!!(ok && st.settings[k])}" aria-label="${name}"><span class="knob"></span></button>
      </div>`;
    }).join('');
    const soon = st.ftab === 'ultimate'
      ? `<button class="ult" id="ult"><span class="glare"></span><span><b>Открытие сундуков через ИИ</b> <span class="soon">Скоро</span></span><span class="lock">${LOCK}</span></button>` : '';
    return `<div class="seg">${seg}</div>
      <div class="scroll"><div class="grid2">${cards}</div>${soon}</div>
      <div class="bottom"><div class="logs" id="logs"></div>${startBtn()}</div>`;
  }
  function pageHome() {
    return `<div class="scroll">
      <div class="card"><span class="muted">Статус</span><span class="big" id="bigst">${STATE_TXT[st.state]}</span><span class="muted" id="statline">${statsLine()}</span></div>
      <div class="card" style="animation-delay:.08s"><h2>${st.hasKey ? 'Твой уровень: ' + TIER_NAME[st.tier] : 'Ключ не активирован'}</h2>
        <p class="muted">${st.hasKey ? 'Горячие клавиши в игре: F9 — пауза, F10 — стоп.' : 'Нажми «Активировать ключ» слева внизу.'}</p></div>
      </div><div class="bottom"><div class="logs" id="logs"></div>${startBtn()}</div>`;
  }
  function field(f, locked) {
    const v = st.settings[f.k], dis = locked ? ' disabled' : '';
    let c;
    if (f.t === 'bool') c = `<button class="sw${v ? ' on' : ''}" data-k="${f.k}" data-t="bool" aria-pressed="${!!v}" aria-label="${esc(f.l)}"${dis}><span class="knob"></span></button>`;
    else if (f.t === 'sel') c = `<select class="inp" data-k="${f.k}" data-t="sel"${dis}>${Object.keys(f.o).map((o) => `<option value="${o}"${String(v) === o ? ' selected' : ''}>${f.o[o]}</option>`).join('')}</select>`;
    else if (f.t === 'num') c = `<input class="inp num" type="number" data-k="${f.k}" data-t="num" min="${f.min}" max="${f.max}" value="${esc(v == null ? f.min : v)}"${dis}>`;
    else if (f.t === 'time') c = `<input class="inp num" data-k="${f.k}" data-t="time" maxlength="5" placeholder="23:00" value="${esc(v || '00:00')}"${dis}>`;
    else c = `<input class="inp" style="width:${f.w || 160}px" data-k="${f.k}" data-t="text" value="${esc(v || '')}"${dis}>`;
    return `<label class="row"><span>${esc(f.l)}</span>${c}</label>`;
  }
  function pageSet() {
    const groups = SETTINGS.map(([title, lockKey, fields], i) => {
      const locked = lockKey ? !can(lockKey, (lockKey === 'zone_nav' || lockKey === 'smooth_mouse') ? 'ultimate' : 'premium') : false;
      return `<div class="card grp" style="animation-delay:${(i * 0.04).toFixed(2)}s"><h2>${title}${locked ? ` <span class="lock">${LOCK}</span>` : ''}</h2>${fields.map((f) => field(f, locked)).join('')}</div>`;
    }).join('');
    const tgLocked = !can('tg_enabled', 'vip');
    const tg = `<div class="card grp"><h2>Telegram${tgLocked ? ` <span class="lock">${LOCK}</span>` : ''}</h2>
      <p class="muted">@BotFather → /newbot → вставь токен → открой своего бота, нажми Start → «Найти Chat ID» → «Тест».</p>
      <label class="row"><span>Токен бота</span><input class="inp" id="tgtok" type="password" style="width:260px" placeholder="${st.hasTg ? 'сохранён — вставь новый, чтобы заменить' : '123456789:AA…'}"${tgLocked ? ' disabled' : ''}></label>
      <label class="row"><span>Chat ID</span><input class="inp" id="tgchat" style="width:160px" value="${esc(st.settings.tg_chat || '')}"${tgLocked ? ' disabled' : ''}></label>
      <div class="brow"><button class="btn" id="tgfind"${tgLocked ? ' disabled' : ''}>Найти Chat ID</button><button class="btn pri" id="tgtest"${tgLocked ? ' disabled' : ''}>Тест</button><span class="muted" id="tgmsg"></span></div></div>`;
    return `<div class="scroll two">${groups}${tg}</div>`;
  }
  function pageShop() {
    const s = st.shop, r = TIER_RANK[st.tier] * (st.hasKey ? 1 : 0);
    const card = (id, name, price, list, rank, extra) => `<div class="card shopc s-${id}">
      <span class="tier t-${id}">${name}</span><span class="price">${esc(price)} ₽</span><span class="muted">навсегда${extra || ''}</span>
      <ul>${list.map((t) => `<li${t[0] === '⏳' ? ' class="muted"' : ''}>${t}</li>`).join('')}</ul>
      ${r >= rank ? '<span class="have">У тебя уже есть</span>' : `<button class="mbtn buy" data-buy="${id}">Купить ${name}</button>`}</div>`;
    const up = st.hasKey && st.tier === 'vip' ? `<div class="card"><div class="brow"><span>У тебя VIP — апгрейд до Premium за <b>${esc(s.price_upgrade || '99')} ₽</b></span><button class="btn pri" data-buy="upgrade">Апгрейд</button></div></div>` : '';
    return `<div class="scroll"><div class="shop">
      ${card('premium', 'Premium', s.price_premium || '159', ['Новые катки без остановки', 'Скип наград, перезапуск, анти-AFK', 'Бег и сундуки', 'Награды и пульт в Telegram', 'Фарм под цель и расписание', 'Анти-кик «как человек»'], 2)}
      ${card('ultimate', 'Ultimate', s.price_ultimate || '249', ['Всё из Premium', 'Обход препятствий и плавная мышь', 'Уход от зоны', 'Выход после смерти и если остался один', 'Точка высадки, спринт, низкая графика', '⏳ Сундуки через ИИ — скоро'], 3)}
      </div>${up}
      <div class="card"><div class="brow"><span>Уже купил? Введи ключ, и функции откроются сразу.</span><button class="btn pri" id="shopkey">Ввести ключ</button></div></div></div>`;
  }
  function pageFaq() {
    return '<div class="scroll"><div class="faq">' + FAQ.map(([q, a], i) =>
      `<div class="card qa" style="animation-delay:${(i * 0.04).toFixed(2)}s"><h2>${q}</h2><p class="muted">${a}</p></div>`).join('') + '</div></div>';
  }
  function pageResell() {
    const shops = ['Playerok', 'FunPay', 'Starvell', 'ТГК-шопы'].map((m) => `<span class="rchip">${m}</span>`).join('');
    return `<div class="scroll"><div class="card rhero">
      <span class="rbadge">РЕСЕЛЛЕР</span>
      <h2>Ищем реселлеров нашего бота</h2>
      <p>Продавай ключи Afk token на всем известных маркетплейсах и в своих магазинах:</p>
      <div class="rchips">${shops}<span class="rchip ghost">и т. д.</span></div>
      <p>Покупка ключей — напрямую у создателя: <a href="https://t.me/${TG}" target="_blank" rel="noopener">@${TG}</a></p>
      <button class="rprice-btn${st.resellOpen ? ' open' : ''}" id="rprice" aria-expanded="${!!st.resellOpen}">💰 Цены для реселлеров <span class="rarrow">▾</span></button>
      <div class="rsheet${st.resellOpen ? ' open' : ''}" id="rsheet"><div class="rpaper">
        <div class="rtier"><b>от 5 шт.</b><span>Premium <i>120 ₽</i></span><span>Ultimate <i>220 ₽</i></span></div>
        <div class="rtier"><b>от 10 шт.</b><span>Premium <i>90 ₽</i></span><span>Ultimate <i>190 ₽</i></span></div>
        <p class="rnote">Минимальная цена продажи — от 170 ₽ на любой площадке.</p>
        <p class="rprofit">Чистая прибыль может достигать <b>до 5000 ₽ в день</b>.</p>
      </div></div>
      <p class="rcall">Не упусти возможность начать сотрудничать с нами и легко заработать, пока боты для получения токена на сверххайпе 🔥</p>
      <div class="rbest"><span>Лучшие площадки для продажи:</span><b>FUNPAY</b><b>PLAYEROK</b></div>
      <div class="brow"><a class="mbtn rgo" href="https://t.me/${TG}" target="_blank" rel="noopener">Стать реселлером → @${TG}</a></div>
    </div></div>`;
  }
  function pageAbout() {
    const topics = ['🐞 Ошибки', '⬆ Апгрейды', '💼 Реселл', '💡 Предложения'].map((m) => `<span class="rchip">${m}</span>`).join('');
    return `<div class="scroll"><div class="card rhero">
      <span class="rbadge sbadge">ТЕХ ПОДДЕРЖКА</span>
      <h2>Тех поддержка программы</h2>
      <p>По поводу ошибок, апгрейдов, реселла и любых предложений — писать строго
        <a href="https://t.me/${TG}" target="_blank" rel="noopener">@${TG}</a></p>
      <div class="rchips">${topics}</div>
      <button class="rprice-btn${st.supOpen ? ' open' : ''}" id="supbtn" aria-expanded="${!!st.supOpen}">⭐ Условия обращения <span class="rarrow">▾</span></button>
      <div class="rsheet${st.supOpen ? ' open' : ''}" id="supsheet"><div class="snote">
        <p><b>Первое сообщение — 5 ⭐ звёзд.</b></p>
        <p>Так мы отсеиваем ненужные вопросы. Если вы купили подписку, думаю, звёзды у вас есть 🙂</p>
      </div></div>
      <div class="brow"><a class="mbtn rgo" href="https://t.me/${TG}" target="_blank" rel="noopener">Написать в поддержку → @${TG}</a></div>
      <div class="sfoot">${st.version ? `Afk token ${esc(st.version)} · ` : ''}<button class="linkbtn" id="classic">Классическое окно</button></div>
    </div></div>`;
  }
  const SUG_KIND = { idea: '💡 Идея', bug: '🐞 Ошибка', question: '❓ Вопрос' };
  const SUG_ST = { new: ['Новое', 'st-new'], planned: ['В планах', 'st-plan'], done: ['Сделано', 'st-done'],
    rejected: ['Не будем', 'st-no'], answered: ['Ответили', 'st-ans'] };
  const fmtDate = (iso) => { try { return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; } };
  function sugItem(r, admin) {
    const [stName, stCls] = SUG_ST[r.status] || SUG_ST.new;
    return `<button class="card sugi" data-sid="${r.id}"${admin ? '' : ' tabindex="-1"'}>
      <div class="sugh"><span class="kind">${SUG_KIND[r.kind] || SUG_KIND.idea}</span><b>${esc(r.title)}</b><span class="stc ${stCls}">${stName}</span></div>
      ${r.body ? `<p class="muted">${esc(r.body)}</p>` : ''}
      ${r.reply ? `<div class="reply"><span>Ответ создателя:</span> ${esc(r.reply)}</div>` : ''}
      <span class="sdate">${fmtDate(r.at)}${admin ? ` · ${esc(r.tier || 'free')}${r.key ? ' · ' + esc(r.key) : ''}` : ''}</span></button>`;
  }
  // ---------- чат ----------
  function chatMsgHtml(m) {
    let t = '';
    try { t = new Date(m.at).toTimeString().slice(0, 5); } catch (e) { t = ''; }
    const cls = m.mine ? 'me' : (m.badge || 'free');
    const mark = { vip: '★ ', admin: '⚙ ', premium: '♛ ', ultimate: '⚡ ' }[m.badge] || '';
    return `<div class="cmsg"><span class="ctime">${t}</span><span class="cn ${cls}">${mark}${esc(m.nick)}</span> <span class="ctext">${esc(m.text)}</span></div>`;
  }
  function pageChat() {
    if (!st.real) return '<div class="card"><h2>Чат</h2><p class="muted">В программе тут общаются все, у кого стоит Afk token. Придумай ник и пиши.</p></div>';
    const muted = st.chat.muted, locked = !st.hasKey || muted;
    const body = st.chat.msgs.length ? st.chat.msgs.map(chatMsgHtml).join('') : '<div class="cempty">Тут пока пусто. Напиши первым 🌸</div>';
    const ph = !st.hasKey ? 'Активируй ключ, чтобы писать' : muted ? 'Тебя замутили' : !st.chat.nick ? 'Придумай ник и нажми «Отправить»' : 'Сообщение…';
    return `<div class="chatwrap">
      <div class="chathead"><span class="muted" id="conline">${st.chat.online ? '●  онлайн: ' + st.chat.online : ''}</span>
        ${st.chat.nick ? `<span class="clink" id="cnick">сменить ник (${esc(st.chat.nick)})</span>` : '<span></span>'}</div>
      <div class="chatlog scroll" id="clog">${body}</div>
      <div class="crow"><input class="inp cinp" id="cinp" maxlength="300" placeholder="${esc(ph)}"${locked ? ' disabled' : ''}>
        <button class="btn pri" id="csend"${locked ? ' disabled' : ''}>Отправить</button></div>
      <div class="cfoot muted" id="cerr">${esc(st.chat.err || 'Без ссылок, рекламы и оскорблений — за это мут.')}</div>
    </div>`;
  }
  function chatRender(scroll) {
    const log = $('#clog');
    if (!log) return;
    const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
    log.innerHTML = st.chat.msgs.length ? st.chat.msgs.map(chatMsgHtml).join('') : '<div class="cempty">Тут пока пусто. Напиши первым 🌸</div>';
    const o = $('#conline'); if (o) o.textContent = st.chat.online ? '●  онлайн: ' + st.chat.online : '';
    if (scroll || atBottom) log.scrollTop = log.scrollHeight;
  }
  async function chatTick(scroll) {
    if (!st.real || !st.hasKey || st.chat.busy) return;
    st.chat.busy = true;
    const r = await call('chat_fetch', st.chat.lastId);
    st.chat.busy = false;
    if (!r || r.error) return;
    if (typeof r.online === 'number') st.chat.online = r.online;
    if (r.nick && !st.chat.nickEditing) st.chat.nick = r.nick;
    if (typeof r.muted === 'boolean') st.chat.muted = r.muted;
    const dels = new Set(r.deleted || []);
    let changed = false;
    if (dels.size) { const b = st.chat.msgs.length; st.chat.msgs = st.chat.msgs.filter((m) => !dels.has(m.id)); if (st.chat.msgs.length !== b) changed = true; }
    const neu = (r.msgs || []).filter((m) => m.id > st.chat.lastId && !dels.has(m.id));
    if (neu.length) {
      st.chat.msgs = st.chat.msgs.concat(neu).slice(-200);
      st.chat.lastId = Math.max.apply(null, neu.map((m) => m.id));
      changed = true;
      if (st.tab !== 'chat') { st.chat.unread += neu.filter((m) => !m.mine).length; renderNav(); }
    }
    if (st.tab === 'chat') { if (changed) chatRender(scroll); else { const o = $('#conline'); if (o) o.textContent = st.chat.online ? '●  онлайн: ' + st.chat.online : ''; } }
  }
  async function chatSend() {
    const inp = $('#cinp'); if (!inp) return;
    const text = inp.value.trim(); if (!text) return;
    const cerr = $('#cerr'), btn = $('#csend');
    const setErr = (t, bad) => { if (cerr) { cerr.textContent = t; cerr.style.color = bad ? '#FCA5A5' : ''; } st.chat.err = t; };
    if (btn) btn.disabled = true;
    if (!st.chat.nick) {
      const r = await call('chat_nick', text);
      if (btn) btn.disabled = false;
      if (r && r.ok && r.nick) { st.chat.nick = r.nick; st.chat.nickEditing = false; st.chat.err = ''; renderPage(); setErr('Готово, твой ник: ' + r.nick); }
      else setErr((r && r.error) || 'Не получилось поставить ник', true);
      return;
    }
    const r = await call('chat_send', text);
    if (btn) btn.disabled = false;
    if (r && r.ok) { inp.value = ''; setErr(''); chatTick(true); }
    else {
      const e = (r && r.error) || 'Ошибка';
      setErr(e, true);
      if (/мут/i.test(e)) { st.chat.muted = true; renderPage(); }
      else if (/ник/i.test(e)) { st.chat.nick = null; renderPage(); }
    }
  }

  function pageSug() {
    const g = st.sug;
    if (st.admin) {
      const cnt = (f) => g.all.filter((r) => f === 'all' || r.status === f).length;
      const tabsH = [['new', 'Новые'], ['planned', 'В планах'], ['answered', 'Ответили'], ['done', 'Сделано'], ['rejected', 'Не будем'], ['all', 'Все']]
        .map(([id, t]) => `<button class="segb${g.f === id ? ' on' : ''}" data-sf="${id}">${t} ${cnt(id)}</button>`).join('');
      const list = g.all.filter((r) => g.f === 'all' || r.status === g.f);
      return `<div class="brow"><div class="seg">${tabsH}</div><button class="btn" id="sref" title="Обновить">⟳</button></div>
        <div class="scroll">${g.error ? `<div class="card"><p class="muted">${esc(g.error)}</p></div>` :
          (list.length ? list.map((r) => sugItem(r, true)).join('') : `<div class="card"><p class="muted">${g.loaded ? 'Тут пусто' : 'Загрузка…'}</p></div>`)}</div>`;
    }
    const mine = g.mine.length ? g.mine.map((r) => sugItem(r, false)).join('')
      : `<div class="card"><p class="muted">${g.error ? esc(g.error) : (g.loaded || !st.real ? 'Ты ещё ничего не отправлял.' : 'Загрузка…')}</p></div>`;
    return `<div class="scroll">
      <div class="card guide"><h2>Как это работает</h2>
        <ol><li><b>Придумал, что улучшить, или нашёл ошибку?</b> Нажми «Создать тикет».</li>
        <li><b>Выбери тип:</b> 💡 идея — новая функция, 🐞 ошибка — что-то сломалось, ❓ вопрос — что-то непонятно.</li>
        <li><b>Опиши коротко и по делу.</b> Хороший пример: <i>«Добавьте счётчик, сколько сундуков открыл бот за катку и за всё время»</i>.
          Для ошибки напиши, что делал и что пошло не так, и приложи файл logs/afk_token.log в Telegram @${TG}.</li>
        <li><b>Создатель читает все тикеты</b> и ставит статус: «В планах», «Сделано», «Ответили» или «Не будем». Ответ появится прямо здесь.</li></ol>
        <p class="muted">Лучшие идеи попадают в обновления. Не больше 5 тикетов в сутки.</p>
        <div class="brow"><button class="mbtn" id="snew" style="flex:none;padding:0 22px;height:44px">+ Создать тикет</button></div></div>
      <h2 class="subh">Мои тикеты</h2>${mine}</div>`;
  }
  async function sugLoad() {
    if (!st.real) { st.sug.loaded = true; return; }
    const r = await call(st.admin ? 'admin_sug_list' : 'sug_mine');
    st.sug.loaded = true;
    st.sug.error = r.ok ? '' : r.error;
    if (r.ok) st.sug[st.admin ? 'all' : 'mine'] = r.rows || [];
    if (st.tab === 'sug') renderPage();
  }
  function openTicket() {
    modal(`<h2>Новый тикет</h2>
      <label for="tk">Тип</label><select class="inp" id="tk"><option value="idea">💡 Идея — новая функция</option><option value="bug">🐞 Ошибка — что-то сломалось</option><option value="question">❓ Вопрос</option></select>
      <label for="tt">Коротко, о чём</label><input class="inp" id="tt" maxlength="80" placeholder="Например: счётчик открытых сундуков">
      <label for="tb">Подробнее</label><textarea class="inp" id="tb" rows="5" maxlength="1500" placeholder="Что добавить или что пошло не так. Чем подробнее — тем быстрее сделаем."></textarea>
      <div class="kerr" id="merr"></div><div class="mrow"><button class="mbtn" id="mok">Отправить</button><button class="mbtn ghost" data-close>Отмена</button></div>`, () => {
      $('#tt').focus();
      $('#mok').onclick = async () => {
        const t = $('#tt').value.trim(), b = $('#tb').value.trim();
        if (t.length < 4) { $('#merr').textContent = 'Напиши заголовок (хотя бы 4 символа)'; shake($('#tt')); return; }
        $('#mok').disabled = true;
        const r = st.real ? await call('sug_send', $('#tk').value, t, b) : { ok: true };
        $('#mok').disabled = false;
        if (!r.ok) { $('#merr').textContent = r.error; return; }
        if (!st.real) st.sug.mine.unshift({ id: Date.now(), at: new Date().toISOString(), kind: $('#tk').value, title: t, body: b, status: 'new' });
        closeModal(); toast('Тикет отправлен, спасибо!'); if (st.real) sugLoad(); else renderPage();
      };
    });
  }
  function openSugAdmin(r) {
    const opts = Object.keys(SUG_ST).map((k) => `<option value="${k}"${r.status === k ? ' selected' : ''}>${SUG_ST[k][0]}</option>`).join('');
    modal(`<h2>${SUG_KIND[r.kind] || ''} · ${esc(r.title)}</h2><div class="notes">${esc(r.body || '(без текста)')}</div>
      <p class="muted">${fmtDate(r.at)} · ${esc(r.tier || 'free')}${r.key ? ' · ' + esc(r.key) : ''}</p>
      <label for="ss">Статус</label><select class="inp" id="ss">${opts}</select>
      <label for="sr">Ответ (увидит автор)</label><textarea class="inp" id="sr" rows="3" maxlength="500">${esc(r.reply || '')}</textarea>
      <div class="kerr" id="merr"></div><div class="mrow"><button class="mbtn" id="mok">Сохранить</button><button class="mbtn ghost" id="sdel">Удалить</button></div>`, () => {
      $('#mok').onclick = async () => {
        const x = await call('admin_sug_update', r.id, $('#ss').value, $('#sr').value.trim());
        if (!x.ok) { $('#merr').textContent = x.error; return; }
        closeModal(); toast('Сохранено'); sugLoad();
      };
      $('#sdel').onclick = () => confirmBox('Удалить этот тикет навсегда?', 'Удалить', async () => {
        const x = await call('admin_sug_update', r.id, 'delete', null);
        if (!x.ok) return toast(x.error, false);
        toast('Удалено'); sugLoad();
      });
    });
  }

  function admRows() {
    const a = st.adm, q = a.q.toLowerCase();
    return a.rows.filter((r) => {
      if (a.f === 'active' && !r.hwid) return false;
      if (a.f === 'online' && r.tag !== 'online') return false;
      if (a.f === 'free' && (r.hwid || r.banned)) return false;
      if (a.f === 'ban' && !r.banned) return false;
      return !q || (r.key + ' ' + r.pc + ' ' + r.note + ' ' + r.hwid).toLowerCase().includes(q);
    });
  }
  function admTable() {
    const rows = admRows();
    if (!rows.length) return `<div class="muted" style="padding:14px">${st.adm.loaded ? 'Ничего не найдено' : 'Загрузка…'}</div>`;
    return rows.map((r) => `<button class="tr r-${esc(r.tag)}${st.adm.sel === r.key ? ' sel' : ''}" data-key="${esc(r.key)}">
      <span class="c1">${esc(r.key)}</span><span class="c2">${esc(r.status)}</span><span class="c3">${esc(r.pc || '—')}</span><span class="c4">${esc(r.note)}</span></button>`).join('');
  }
  function pageAdmin() {
    const a = st.adm, R = a.rows;
    const n = (f) => R.filter(f).length;
    const f = [['all', 'Все'], ['active', 'Активные'], ['online', 'Онлайн'], ['free', 'Свободные'], ['ban', 'Бан']].map(([id, t]) =>
      `<option value="${id}"${a.f === id ? ' selected' : ''}>${t}</option>`).join('');
    return `<div class="astats"><span>Всего <b>${R.length}</b></span><span>Активировано <b>${n((r) => r.hwid)}</b></span><span>Онлайн <b>${n((r) => r.tag === 'online')}</b></span><span>Свободных <b>${n((r) => !r.hwid && !r.banned)}</b></span><span>Бан <b>${n((r) => r.banned)}</b></span></div>
      <div class="brow"><input class="inp" id="aq" style="flex:1" placeholder="Поиск: ключ, ПК, заметка, HWID" value="${esc(a.q)}"><select class="inp" id="af">${f}</select>
        <button class="btn" id="arel" title="Обновить список">⟳</button><button class="btn pri" id="anew">Создать ключи</button><button class="btn" id="ashop">Магазин</button><button class="btn" id="aupd">Выпустить обновление</button></div>
      <div class="tbl" id="atbl">${admTable()}</div>
      <div class="brow"><button class="btn" data-a="copy">Копировать</button><button class="btn" data-a="note">Заметка</button><button class="btn" data-a="reset_hwid">Сбросить ПК</button><button class="btn pri" data-a="msg">Написать</button>
        <button class="btn warn" data-a="ban">Бан / разбан</button><button class="btn warn" data-a="delete">Удалить</button></div>`;
  }

  function renderPage() {
    const p = $('#page');
    const html = { func: pageFunc, home: pageHome, set: pageSet, shop: pageShop, sug: pageSug, faq: pageFaq, chat: pageChat, resell: pageResell, about: pageAbout, admin: pageAdmin }[st.tab]();
    p.innerHTML = '<div class="page">' + html + '</div>';
    bindPage();
    renderLogs();
  }

  function setSetting(k, v) {
    st.settings[k] = v;
    if (st.real) py().set_setting(k, v);
  }
  function bindPage() {
    $$('.feat, .ult').forEach((c) => c.addEventListener('mousemove', (e) => {
      const r = c.getBoundingClientRect();
      c.style.setProperty('--mx', e.clientX - r.left + 'px');
      c.style.setProperty('--my', e.clientY - r.top + 'px');
    }));
    $$('.segb').forEach((b) => b.onclick = () => { st.ftab = b.dataset.f; renderPage(); });
    const sb = $('#supbtn');
    if (sb) sb.onclick = () => {
      st.supOpen = !st.supOpen;
      sb.classList.toggle('open', st.supOpen);
      sb.setAttribute('aria-expanded', st.supOpen);
      $('#supsheet').classList.toggle('open', st.supOpen);
    };
    const rp = $('#rprice');
    if (rp) rp.onclick = () => {
      st.resellOpen = !st.resellOpen;
      rp.classList.toggle('open', st.resellOpen);
      rp.setAttribute('aria-expanded', st.resellOpen);
      $('#rsheet').classList.toggle('open', st.resellOpen);
    };
    $$('.feat').forEach((c) => {
      const k = c.dataset.k, sw = $('.sw', c);
      sw.onclick = () => {
        if (c.classList.contains('locked')) {
          shake(c);
          toast(st.hasKey ? `Эта функция открывается на уровне ${TIER_NAME[c.dataset.tier]}` : 'Сначала активируй ключ', false);
          return;
        }
        const v = !st.settings[k];
        setSetting(k, v);
        sw.classList.toggle('on', v);
        sw.setAttribute('aria-pressed', v);
        if (v) { const w = document.createElement('span'); w.className = 'wave'; c.appendChild(w); setTimeout(() => w.remove(), 700); }
        addLog((v ? 'Включено: ' : 'Выключено: ') + $('.fname', c).textContent);
      };
    });
    const ult = $('#ult');
    if (ult) ult.onclick = () => { shake(ult); toast('Сундуки через ИИ пока недоступны — скоро', false); };
    $$('.start').forEach((b) => b.onclick = onStart);

    // настройки
    $$('.grp [data-k]').forEach((el) => {
      const k = el.dataset.k, t = el.dataset.t;
      if (t === 'bool') el.onclick = () => { const v = !st.settings[k]; setSetting(k, v); el.classList.toggle('on', v); el.setAttribute('aria-pressed', v); };
      else el.onchange = () => {
        let v = el.value;
        if (t === 'num') { v = Math.max(+el.min, Math.min(+el.max, Math.round(+v || 0))); el.value = v; }
        if (t === 'time') {
          const m = /^([01]?\d|2[0-3])[:.]([0-5]\d)$/.exec(v.trim());
          if (!m) { el.value = st.settings[k]; shake(el); return; }
          v = m[1].padStart(2, '0') + ':' + m[2]; el.value = v;
        }
        setSetting(k, v);
      };
    });
    const tgSave = async () => { if (st.real) await call('tg_save', $('#tgtok').value.trim(), $('#tgchat').value.trim()); if ($('#tgtok').value.trim()) st.hasTg = true; st.settings.tg_chat = $('#tgchat').value.trim(); };
    if ($('#tgfind')) {
      const msg = (t, ok) => { const m = $('#tgmsg'); if (m) { m.textContent = t; m.style.color = ok ? '#86EFAC' : '#FCA5A5'; } };
      $('#tgtok').onchange = tgSave; $('#tgchat').onchange = tgSave;
      $('#tgfind').onclick = async () => {
        await tgSave(); msg('Ищу…', true);
        const r = st.real ? await call('tg_find_chat') : { ok: false, error: 'В демо недоступно' };
        if (r.ok) { $('#tgchat').value = r.chat; st.settings.tg_chat = r.chat; msg(`Нашёл: ${r.name}. Нажми «Тест».`, true); } else msg(r.error, false);
      };
      $('#tgtest').onclick = async () => {
        await tgSave(); msg('Отправляю…', true);
        const r = st.real ? await call('tg_test') : { ok: false, error: 'В демо недоступно' };
        msg(r.ok ? 'Готово, проверь Telegram' : r.error, r.ok);
      };
    }
    // магазин / создатель
    $$('[data-buy]').forEach((b) => b.onclick = () => { if (st.real) py().open_shop(b.dataset.buy); else toast('В программе откроется страница покупки'); });
    if ($('#shopkey')) $('#shopkey').onclick = openKey;
    if ($('#classic')) $('#classic').onclick = () => confirmBox('Это окно закроется, бот остановится, откроется классическое окно.', 'Открыть', async () => {
      if (!st.real) return toast('В демо недоступно', false);
      const r = await call('open_classic'); if (r && r.ok === false) toast(r.error, false);
    });
    // чат
    if ($('#csend')) {
      $('#csend').onclick = chatSend;
      $('#cinp').onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); chatSend(); } };
      if ($('#cnick')) $('#cnick').onclick = () => { st.chat.nickEditing = true; st.chat.nick = null; renderPage(); const i = $('#cinp'); if (i) { i.placeholder = 'Новый ник…'; i.focus(); } };
      chatRender(true);
    }
    // админ
    if ($('#atbl')) bindAdmin();
    // предложения
    if ($('#snew')) $('#snew').onclick = openTicket;
    if ($('#sref')) $('#sref').onclick = () => { st.sug.loaded = false; renderPage(); sugLoad(); };
    $$('[data-sf]').forEach((b) => b.onclick = () => { st.sug.f = b.dataset.sf; renderPage(); });
    if (st.admin) $$('.sugi').forEach((b) => b.onclick = () => { const r = st.sug.all.find((x) => String(x.id) === b.dataset.sid); if (r) openSugAdmin(r); });
  }

  // ---------- админ ----------
  async function admLoad() {
    const r = await call('admin_list');
    st.adm.loaded = true;
    if (!r.ok) { toast('Админка: ' + r.error, false); return; }
    st.adm.rows = r.rows;
    if (st.tab === 'admin') renderPage();
  }
  function bindAdmin() {
    const a = st.adm;
    const refill = () => { $('#atbl').innerHTML = admTable(); bindRows(); };
    const bindRows = () => $$('#atbl .tr').forEach((b) => b.onclick = () => { a.sel = b.dataset.key; $$('#atbl .tr').forEach((x) => x.classList.toggle('sel', x === b)); });
    bindRows();
    $('#aq').oninput = (e) => { a.q = e.target.value; refill(); };
    $('#af').onchange = (e) => { a.f = e.target.value; refill(); };
    $('#arel').onclick = () => { a.loaded = false; refill(); admLoad(); };
    $('#anew').onclick = () => modal(`<h2>Создать ключи</h2>
      <label for="ct">Уровень</label><select class="inp" id="ct"><option value="vip">VIP</option><option value="premium">Premium</option><option value="upgrade">Апгрейд VIP→Premium</option><option value="ultimate">Ultimate</option></select>
      <label for="cn">Сколько</label><input class="inp" id="cn" type="number" min="1" max="500" value="10">
      <div class="kerr" id="merr"></div><div class="mrow"><button class="mbtn" id="mok">Создать</button><button class="mbtn ghost" data-close>Отмена</button></div>`, () => {
      $('#mok').onclick = async () => {
        $('#mok').disabled = true;
        const r = await call('admin_create', +$('#cn').value || 1, $('#ct').value);
        if (!r.ok) { $('#mok').disabled = false; $('#merr').textContent = r.error; return; }
        closeModal(); toast(`Создано: ${r.created}. Ключи скопированы${r.file ? ' и сохранены в ' + r.file : ''}`); admLoad();
      };
    });
    $('#ashop').onclick = () => {
      const F = [['price_vip', 'Цена VIP, ₽'], ['price_premium', 'Цена Premium, ₽'], ['price_upgrade', 'Цена апгрейда, ₽'], ['price_ultimate', 'Цена Ultimate, ₽'],
        ['url_vip', 'Ссылка на лот VIP'], ['url_premium', 'Ссылка на лот Premium'], ['url_upgrade', 'Ссылка на лот апгрейда'], ['url_ultimate', 'Ссылка на лот Ultimate']];
      modal(`<h2>Магазин: цены и ссылки</h2><div class="mgrid">${F.map(([k, l]) => `<label>${l}<input class="inp" data-s="${k}" value="${esc(st.shop[k] || '')}"></label>`).join('')}</div>
        <div class="kerr" id="merr"></div><div class="mrow"><button class="mbtn" id="mok">Сохранить</button><button class="mbtn ghost" data-close>Отмена</button></div>`, () => {
        $('#mok').onclick = async () => {
          const vals = {}; $$('[data-s]').forEach((i) => vals[i.dataset.s] = i.value.trim());
          $('#mok').disabled = true;
          const r = await call('admin_shop_save', vals);
          $('#mok').disabled = false;
          if (!r.ok) { $('#merr').textContent = r.error; return; }
          closeModal(); toast(r.changed ? 'Магазин сохранён' : 'Ничего не поменялось');
        };
      });
    };
    $('#aupd').onclick = () => modal(`<h2>Выпустить обновление</h2><p class="muted">Сначала загрузи zip в Supabase → Storage → releases. Обновление получат ВСЕ пользователи.</p>
      <label for="rv">Версия</label><input class="inp" id="rv" placeholder="1.6.1">
      <label for="rf">Имя файла в Storage или полная ссылка</label><input class="inp" id="rf" placeholder="AfkToken_1.6.1.zip">
      <label for="rn">Что нового</label><textarea class="inp" id="rn" rows="5"></textarea>
      <div class="kerr" id="merr"></div><div class="mrow"><button class="mbtn" id="mok">Опубликовать</button><button class="mbtn ghost" data-close>Отмена</button></div>`, () => {
      $('#mok').onclick = async () => {
        $('#mok').disabled = true; $('#merr').textContent = '';
        const r = await call('admin_release', $('#rv').value, $('#rf').value, $('#rn').value);
        $('#mok').disabled = false;
        if (!r.ok) { $('#merr').textContent = r.error; return; }
        closeModal(); toast('Версия опубликована');
      };
    });
    $$('[data-a]').forEach((b) => b.onclick = async () => {
      const row = a.rows.find((r) => r.key === a.sel);
      if (!row) return toast('Выбери строку в таблице', false);
      const act = b.dataset.a;
      const run = async (action, note, okText) => {
        const r = await call('admin_action', row.key, action, note == null ? null : note);
        if (!r.ok) return toast(r.error, false);
        toast(okText); admLoad();
      };
      if (act === 'msg') return openMsgAdmin(row);
      if (act === 'copy') { const ok = await call('copy', row.key); toast(ok === false || (ok && ok.ok === false) ? 'Не удалось скопировать' : 'Скопирован ' + row.key, ok !== false); }
      else if (act === 'note') modal(`<h2>Заметка</h2><label for="nt">${esc(row.key)}</label><input class="inp" id="nt" value="${esc(row.note)}">
        <div class="mrow"><button class="mbtn" id="mok">Сохранить</button><button class="mbtn ghost" data-close>Отмена</button></div>`, () => {
        $('#nt').focus(); $('#mok').onclick = () => { const v = $('#nt').value.trim(); closeModal(); run('note', v, 'Заметка сохранена'); };
      });
      else if (act === 'reset_hwid') confirmBox(`Отвязать ${row.key} от компьютера? Его можно будет активировать на другом ПК.`, 'Отвязать', () => run('reset_hwid', null, 'Привязка сброшена'));
      else if (act === 'ban') { if (row.banned) run('unban', null, 'Разблокирован'); else confirmBox(`Заблокировать ${row.key}?`, 'Заблокировать', () => run('ban', null, 'Заблокирован')); }
      else if (act === 'delete') confirmBox(`Удалить ключ ${row.key} навсегда? Вернуть его будет нельзя.`, 'Удалить', () => run('delete', null, 'Удалён'));
    });
  }

  // ---------- ключ ----------
  function renderKey() {
    const b = $('#keybox');
    b.classList.toggle('need', !st.hasKey && !st.checking);
    $('#keysub').textContent = st.checking || st.hasKey ? 'Ключ' : 'Нет доступа';
    $('#keytxt').textContent = st.checking ? 'Проверяю…' : (st.hasKey ? TIER_NAME[st.tier] + ' · навсегда' : 'Активировать ключ');
  }
  function openKey() {
    modal(`<h2>Активировать ключ</h2>
      <label for="kin">Вставь ключ, который пришёл после покупки</label>
      <input class="kin" id="kin" placeholder="AFK-XXXX-XXXX-XXXX-XXXX" maxlength="23" autocomplete="off" spellcheck="false">
      <div class="kerr" id="kerr"></div>
      <div class="mrow"><button class="mbtn" id="kgo">Активировать</button><button class="mbtn ghost" data-close>Отмена</button></div>
      <div class="nokey"><span>Нет ключа?</span><a href="https://t.me/${TG}" target="_blank" rel="noopener">Написать @${TG}</a></div>`, () => {
      const inp = $('#kin'), err = $('#kerr'), go = $('#kgo');
      inp.focus();
      inp.oninput = () => { inp.classList.remove('bad'); err.textContent = ''; };
      inp.onkeydown = (e) => { if (e.key === 'Enter') go.click(); if (e.key === 'Escape') closeModal(); };
      go.onclick = async () => {
        const key = inp.value.trim().toUpperCase();
        const fail = (m) => { err.className = 'kerr'; err.textContent = m; inp.classList.add('bad'); shake(inp); };
        if (!KEY_RE.test(key)) return fail('Ключ выглядит так: AFK-XXXX-XXXX-XXXX-XXXX');
        go.disabled = true; go.textContent = 'Проверяю…';
        const res = st.real ? await call('activate', key) : { ok: true, tier: 'ultimate', demo: true };
        go.disabled = false; go.textContent = 'Активировать';
        if (!res || !res.ok) return fail((res && res.error) || 'Ключ не подходит');
        st.hasKey = true; st.tier = res.tier || 'vip';
        err.className = 'kerr kok'; err.textContent = 'Ключ активирован';
        addLog('Ключ подтверждён · ' + TIER_NAME[st.tier] + (res.demo ? ' (демо)' : ''));
        if (st.real) await loadMeta(); else renderKey();
        setTimeout(() => { closeModal(); renderNav(); renderPage(); }, 700);
      };
    });
  }

  // ссылки открываем в обычном браузере, а не внутри окна программы
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href^="http"]');
    if (a && st.real) { e.preventDefault(); py().open_url(a.href); }
  });

  // ---------- личные сообщения (1.6.1) ----------
  function msgHist(rows) {
    if (!rows.length) return '<p class="muted">Этому ключу ещё ничего не писали.</p>';
    return rows.map((m) => `<div class="pmh"><div class="pmt">${esc(m.body)}</div>
      <div class="pmm"><span>${fmtDate(m.at)} · ${m.read_at ? 'прочитано ' + fmtDate(m.read_at) : 'ещё не видел'}</span>
      ${m.read_at ? '' : `<a href="#" data-del="${m.id}">удалить</a>`}</div></div>`).join('');
  }
  async function openMsgAdmin(row) {
    modal(`<h2>Сообщение ключу</h2><p class="muted">${esc(row.key)}${row.pc ? ' · ' + esc(row.pc) : ''}${row.note ? ' · ' + esc(row.note) : ''}</p>
      <label for="pm">Текст — покажется у него при следующем запуске программы</label>
      <textarea class="inp" id="pm" rows="4" maxlength="1000" placeholder="Привет! …"></textarea>
      <div class="kerr" id="merr"></div><div class="mrow"><button class="mbtn" id="mok">Отправить</button><button class="mbtn ghost" data-close>Закрыть</button></div>
      <label>История</label><div class="pmlist" id="pml"><p class="muted">Загрузка…</p></div>`, () => {
      $('#pm').focus();
      const load = async () => {
        const r = await call('admin_msg_list', row.key);
        if (!$('#pml')) return;
        if (!r.ok) { $('#pml').innerHTML = `<p class="muted">${esc(r.error)}</p>`; return; }
        $('#pml').innerHTML = msgHist(r.rows || []);
        $$('#pml [data-del]').forEach((a) => a.onclick = async (e) => {
          e.preventDefault();
          const x = await call('admin_msg_delete', a.dataset.del);
          if (!x.ok) return toast(x.error, false);
          toast('Сообщение удалено'); load();
        });
      };
      load();
      $('#mok').onclick = async () => {
        const t = $('#pm').value.trim();
        if (!t) { $('#merr').textContent = 'Напиши текст'; shake($('#pm')); return; }
        $('#mok').disabled = true; $('#merr').textContent = '';
        const r = await call('admin_msg_send', row.key, t);
        $('#mok').disabled = false;
        if (!r.ok) { $('#merr').textContent = r.error; return; }
        $('#pm').value = ''; toast('Отправлено — увидит при запуске'); load();
      };
    });
  }
  // при запуске: показываем непрочитанные по одному
  async function checkMessages() {
    const r = await call('msg_fetch');
    if (!r || !r.ok || !r.rows || !r.rows.length) return;
    const queue = r.rows.slice();
    const next = () => {
      const m = queue.shift();
      if (!m) return;
      st.msgOpen = true;
      modal(`<h2>Сообщение от создателя</h2><div class="notes pmsg">${esc(m.body)}</div>
        <p class="muted">${fmtDate(m.at)}${queue.length ? ` · ещё ${queue.length}` : ''}</p>
        <div class="mrow"><button class="mbtn" id="mok">Понятно</button></div>`, () => {
        const ov = $('#ov'); ov.replaceWith(ov.cloneNode(true));   // не закрывать кликом мимо — только кнопкой
        $('#mok').onclick = async () => {
          $('#mok').disabled = true;
          await call('msg_read', m.id);
          closeModal(); st.msgOpen = false;
          next();
        };
      });
    };
    next();
  }

  // ---------- обновление ----------
  function showUpdate(u) {
    st.updShown = true;
    modal(`<h2>Доступно обновление ${esc(u.version)}</h2><div class="notes">${esc(u.notes || 'Исправления и улучшения.')}</div>
      <div class="kerr kok" id="ust">${u.can_auto ? 'Ключ и настройки сохранятся.' : 'Скачай архив и замени файлы программы.'}</div>
      <div class="mrow"><button class="mbtn" id="ugo">${u.can_auto ? 'Обновить сейчас' : 'Скачать'}</button><button class="mbtn ghost" data-close>Позже</button></div>
      <div class="nokey"><span></span><a href="#" id="uskip">Пропустить эту версию</a></div>`, () => {
      const go = () => { $('#ugo').disabled = true; py().update_start(); };
      $('#ugo').onclick = go;
      $('#uskip').onclick = (e) => { e.preventDefault(); py().update_skip(); closeModal(); };
      if (u.auto) { $('#ust').textContent = 'Автообновление начнётся через 3 секунды…'; setTimeout(() => { if ($('#ugo') && !$('#ugo').disabled) go(); }, 3000); }
    });
  }

  // ---------- связь с программой ----------
  async function loadMeta() {
    const m = await call('meta');
    if (!m || m.ok === false) return;
    applyMeta(m);
  }
  function applyMeta(m) {
    st.rev = m.rev; st.version = m.version || ''; st.hasKey = !!m.has_key; st.tier = m.tier || 'free'; st.admin = !!m.admin;
    st.free = !!m.free_edition; st.hasTg = !!m.has_tg_token;
    st.settings = Object.assign({}, st.settings, m.settings || {}); st.allowed = m.allowed || {}; st.shop = Object.assign({}, st.shop, m.shop || {});
    renderKey();
  }
  async function connect() {
    st.real = true; st.logs = []; st.checking = true;
    renderKey();
    addLog('Проверка ключа…');
    let info = await call('init');
    if (!info || info.ok === false) info = { license: { ok: false, error: (info && info.error) || 'нет связи с программой' }, state: 'stopped' };
    st.checking = false;
    applyMeta(info);
    const l = info.license || {};
    addLog(l.ok ? 'Ключ подтверждён · ' + TIER_NAME[st.tier] + (l.offline ? ' (офлайн)' : '') : (l.error ? 'Ключ: ' + l.error : 'Активируй ключ, чтобы запустить программу'));
    renderNav(); renderPage();
    setState(info.state || 'stopped');
    setInterval(poll, 700);
    let _ct = 0;
    setInterval(() => { if (st.hasKey && (st.tab === 'chat' || _ct % 10 === 0)) chatTick(); _ct++; }, 3000);
    if (st.hasKey) setTimeout(checkMessages, 600);
  }
  async function poll() {
    let r;
    try { r = await py().poll(); } catch (e) { return; }
    if (!r) return;
    (r.logs || []).forEach((l) => addLog(l[1], l[0]));
    st.stats = r.stats || st.stats;
    if (r.rev !== st.rev) {
      await loadMeta();
      const typing = document.activeElement && /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
      renderNav();
      if (!typing) renderPage();
    }
    setState(r.state || 'stopped');
    const sl = $('#statline');
    if (sl) sl.textContent = statsLine();
    const u = r.update;
    if (u) {
      if (!st.updShown && !$('#ov') && (u.auto || !u.skipped)) showUpdate(u);
      const us = $('#ust'), p = u.progress || {};
      if (us && (p.status || p.error)) { us.textContent = p.error || p.status; us.className = 'kerr' + (p.error ? '' : ' kok'); if (p.error && $('#ugo')) $('#ugo').disabled = false; }
    }
  }

  $('#keybox').onclick = openKey;
  $('#donate').onclick = donateModal;
  renderNav();
  renderKey();
  renderPage();
  let connected = false;
  const tryConnect = () => { if (!connected && py()) { connected = true; connect(); } };
  window.addEventListener('pywebviewready', tryConnect);
  tryConnect();

  // демо-журнал, пока интерфейс открыт просто в браузере
  const demo = ['Поиск матча: Отряды', 'Матч найден', 'Прыжок с автобуса', 'Анти-AFK: нажата W', 'Команда выбыла → выход в лобби', 'Награды пропущены'];
  let di = 0;
  setInterval(() => { if (!st.real && st.state === 'running') addLog(demo[di++ % demo.length]); }, 2600);
})();
