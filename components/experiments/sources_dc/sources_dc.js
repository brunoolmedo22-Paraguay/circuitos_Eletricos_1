(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const bankSvg = $('bankSvg');
  const equivalentSvg = $('equivalentSvg');
  const bankStage = $('bankStage');
  const sourceVoltage = $('sourceVoltage');
  const sourceCapacity = $('sourceCapacity');
  const seriesMode = $('seriesMode');
  const parallelMode = $('parallelMode');
  const removeSource = $('removeSource');
  const addSource = $('addSource');
  const countText = $('countText');
  const countValue = $('countValue');
  const bankCountBadge = $('bankCountBadge');
  const bankModeBadge = $('bankModeBadge');
  const modePill = $('modePill');
  const eqVoltage = $('eqVoltage');
  const eqCapacity = $('eqCapacity');
  const voltageRelation = $('voltageRelation');
  const capacityRelation = $('capacityRelation');
  const observation = $('observation');

  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeSourceNote = $('challengeSourceNote');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  let state = { mode: 'series', count: 1, voltage: 1.5, capacity: 2.0 };
  let previousCount = 1;
  let challenge = null;

  const challenges = [
    { voltage: 1.5, capacity: 2.0, count: 4, mode: 'series', targetV: 6.0, targetC: null,
      text: 'Monte um banco de 6 V usando fontes de 1,5 V.' },
    { voltage: 12.0, capacity: 2.0, count: 3, mode: 'parallel', targetV: 12.0, targetC: 6.0,
      text: 'Usando fontes de 12 V / 2 Ah, monte um banco de 12 V / 6 Ah.' },
    { voltage: 3.0, capacity: 1.5, count: 3, mode: 'series', targetV: 9.0, targetC: null,
      text: 'Você possui fontes de 3 V / 1,5 Ah. Obtenha 9 V.' },
    { voltage: 6.0, capacity: 2.5, count: 4, mode: 'parallel', targetV: 6.0, targetC: 10.0,
      text: 'Monte um banco de 6 V / 10 Ah usando fontes de 6 V / 2,5 Ah.' },
    { voltage: 2.0, capacity: 3.0, count: 5, mode: 'series', targetV: 10.0, targetC: null,
      text: 'Obtenha 10 V usando fontes idênticas de 2 V / 3 Ah.' },
    { voltage: 9.0, capacity: 1.2, count: 4, mode: 'parallel', targetV: 9.0, targetC: 4.8,
      text: 'Usando fontes de 9 V / 1,2 Ah, monte um banco de 9 V / 4,8 Ah.' },
  ];

  const svgNS = 'http://www.w3.org/2000/svg';
  const fmt = (value, digits = 1) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  function safeNumber(input, fallback, min, max) {
    const parsed = Number(String(input.value).replace(',', '.'));
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(max, Math.max(min, parsed));
  }

  function svgEl(tag, attrs = {}, text = null) {
    const el = document.createElementNS(svgNS, tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    if (text !== null) el.textContent = text;
    return el;
  }

  function addLine(parent, x1, y1, x2, y2, cls = 'svg-wire') {
    parent.appendChild(svgEl('line', { x1, y1, x2, y2, class: cls }));
  }

  function addText(parent, x, y, text, cls, anchor = 'middle') {
    parent.appendChild(svgEl('text', { x, y, class: cls, 'text-anchor': anchor }, text));
  }

  function drawHorizontalSource(parent, centerX, y, slot, index, entering) {
    const compact = slot < 112;
    const plateGap = compact ? 20 : 24;
    const longH = compact ? 47 : 54;
    const shortH = compact ? 31 : 36;
    const leftPlate = centerX - plateGap / 2;
    const rightPlate = centerX + plateGap / 2;
    const group = svgEl('g', { class: `source-unit${entering ? ' entering' : ''}` });

    addLine(group, centerX - slot / 2 + 5, y, leftPlate, y);
    addLine(group, rightPlate, y, centerX + slot / 2 - 5, y);
    addLine(group, leftPlate, y - longH / 2, leftPlate, y + longH / 2, 'source-plate long');
    addLine(group, rightPlate, y - shortH / 2, rightPlate, y + shortH / 2, 'source-plate short');
    addText(group, leftPlate - 15, y - 25, '+', 'source-polarity');
    addText(group, rightPlate + 15, y - 25, '−', 'source-polarity');
    addText(group, centerX, y + 47, `${fmt(state.voltage)} V`, 'source-value');
    addText(group, centerX, y + 64, `${fmt(state.capacity)} Ah`, 'source-capacity');
    addText(group, centerX, y - 53, `F${index + 1}`, 'source-index');
    parent.appendChild(group);
  }

  function drawVerticalSource(parent, x, topY, bottomY, index, entering) {
    const centerY = (topY + bottomY) / 2;
    const longY = centerY - 15;
    const shortY = centerY + 17;
    const group = svgEl('g', { class: `source-unit${entering ? ' entering' : ''}` });

    addLine(group, x, topY, x, longY);
    addLine(group, x - 24, longY, x + 24, longY, 'source-plate long');
    addLine(group, x - 16, shortY, x + 16, shortY, 'source-plate short');
    addLine(group, x, shortY, x, bottomY);
    addText(group, x + 36, longY + 5, '+', 'source-polarity', 'start');
    addText(group, x + 36, shortY + 6, '−', 'source-polarity', 'start');
    addText(group, x, centerY + 60, `${fmt(state.voltage)} V`, 'source-value');
    addText(group, x, centerY + 76, `${fmt(state.capacity)} Ah`, 'source-capacity');
    addText(group, x, centerY - 56, `F${index + 1}`, 'source-index');
    parent.appendChild(group);
  }

  function drawTerminal(parent, x, y, sign, labelX, anchor = 'middle') {
    const group = svgEl('g', { class: 'bank-terminal' });
    group.appendChild(svgEl('circle', { cx: x, cy: y, r: 8 }));
    addText(group, labelX, y + 6, sign, 'source-polarity', anchor);
    parent.appendChild(group);
  }

  function renderSeries(animateNew) {
    const n = state.count;
    const left = 74;
    const right = 746;
    const y = 165;
    const available = right - left;
    const slot = Math.min(126, available / n);
    const total = slot * n;
    const start = 410 - total / 2;

    // External terminal extensions.
    const firstLeft = start + 5;
    const lastRight = start + total - 5;
    addLine(bankSvg, 45, y, firstLeft, y, 'svg-wire svg-bus');
    addLine(bankSvg, lastRight, y, 775, y, 'svg-wire svg-bus');
    drawTerminal(bankSvg, 45, y, '+', 45, 'middle');
    drawTerminal(bankSvg, 775, y, '−', 775, 'middle');

    for (let i = 0; i < n; i += 1) {
      const centerX = start + slot * (i + .5);
      drawHorizontalSource(bankSvg, centerX, y, slot, i, animateNew && i === n - 1 && n > previousCount);
      if (i < n - 1) {
        addLine(bankSvg, start + slot * (i + 1) - 5, y, start + slot * (i + 1) + 5, y);
      }
    }

    addText(bankSvg, 45, y - 32, 'terminal +', 'source-index', 'start');
    addText(bankSvg, 775, y - 32, 'terminal −', 'source-index', 'end');
    addText(bankSvg, 410, 286, n === 1 ? 'uma única fonte: o banco equivale à própria fonte' : 'positivo de uma fonte conectado ao negativo da próxima', 'source-capacity');
  }

  function renderParallel(animateNew) {
    const n = state.count;
    const left = 110;
    const right = 710;
    const topY = 82;
    const bottomY = 264;

    addLine(bankSvg, 66, topY, 754, topY, 'svg-wire svg-bus');
    addLine(bankSvg, 66, bottomY, 754, bottomY, 'svg-wire svg-bus');
    drawTerminal(bankSvg, 66, topY, '+', 41, 'end');
    drawTerminal(bankSvg, 66, bottomY, '−', 41, 'end');

    const spacing = n === 1 ? 0 : (right - left) / (n - 1);
    for (let i = 0; i < n; i += 1) {
      const x = n === 1 ? 410 : left + spacing * i;
      drawVerticalSource(bankSvg, x, topY, bottomY, i, animateNew && i === n - 1 && n > previousCount);
    }

    addText(bankSvg, 410, 322, n === 1 ? 'uma única fonte: tensão e capacidade permanecem inalteradas' : 'todas as fontes compartilham os mesmos barramentos + e −', 'source-capacity');
  }

  function renderEquivalent(Veq, Ceq) {
    equivalentSvg.replaceChildren();
    const y = 62;
    addLine(equivalentSvg, 18, y, 83, y, 'svg-wire');
    addLine(equivalentSvg, 147, y, 212, y, 'svg-wire');
    addLine(equivalentSvg, 94, 31, 94, 93, 'source-plate long');
    addLine(equivalentSvg, 133, 41, 133, 83, 'source-plate short');
    addText(equivalentSvg, 72, 31, '+', 'eq-terminal-text');
    addText(equivalentSvg, 155, 31, '−', 'eq-terminal-text');
    equivalentSvg.appendChild(svgEl('circle', { cx: 18, cy: y, r: 7, class: 'eq-terminal' }));
    equivalentSvg.appendChild(svgEl('circle', { cx: 212, cy: y, r: 7, class: 'eq-terminal' }));
    addText(equivalentSvg, 114, 111, `${fmt(Veq)} V · ${fmt(Ceq)} Ah`, 'eq-source-value');
  }

  function calculate() {
    const n = state.count;
    return state.mode === 'series'
      ? { voltage: n * state.voltage, capacity: state.capacity }
      : { voltage: state.voltage, capacity: n * state.capacity };
  }

  function setObservation(action = 'mode') {
    if (state.mode === 'series') {
      observation.textContent = action === 'add'
        ? 'Ao adicionar outra fonte em série, a tensão total aumenta.'
        : action === 'remove'
          ? 'Ao remover uma fonte em série, a tensão total diminui.'
          : 'Em série, as tensões das fontes se somam.';
    } else {
      observation.textContent = action === 'add'
        ? 'Ao adicionar outra fonte em paralelo, a capacidade disponível aumenta.'
        : action === 'remove'
          ? 'Ao remover uma fonte em paralelo, a capacidade disponível diminui.'
          : 'Em paralelo, a tensão permanece igual à de uma fonte individual.';
    }
  }

  function renderBank({ animate = false, action = 'mode' } = {}) {
    state.voltage = safeNumber(sourceVoltage, state.voltage, .1, 60);
    state.capacity = safeNumber(sourceCapacity, state.capacity, .1, 100);
    sourceVoltage.value = state.voltage;
    sourceCapacity.value = state.capacity;

    const result = calculate();
    bankSvg.replaceChildren();
    if (state.mode === 'series') renderSeries(animate);
    else renderParallel(animate);

    if (animate) {
      bankSvg.classList.remove('redrawing');
      void bankSvg.getBoundingClientRect();
      bankSvg.classList.add('redrawing');
      window.setTimeout(() => bankSvg.classList.remove('redrawing'), 520);
    }

    renderEquivalent(result.voltage, result.capacity);

    const countLabel = `${state.count} ${state.count === 1 ? 'fonte' : 'fontes'}`;
    countText.textContent = countLabel;
    countValue.textContent = String(state.count);
    bankCountBadge.textContent = countLabel;
    bankModeBadge.textContent = state.mode === 'series' ? 'Série' : 'Paralelo';
    modePill.textContent = state.mode === 'series' ? 'Série' : 'Paralelo';
    eqVoltage.textContent = `${fmt(result.voltage)} V`;
    eqCapacity.textContent = `${fmt(result.capacity)} Ah`;

    if (state.mode === 'series') {
      voltageRelation.textContent = `Veq = ${state.count} × ${fmt(state.voltage)} = ${fmt(result.voltage)} V`;
      capacityRelation.textContent = `Ceq = ${fmt(state.capacity)} Ah`;
    } else {
      voltageRelation.textContent = `Veq = ${fmt(state.voltage)} V`;
      capacityRelation.textContent = `Ceq = ${state.count} × ${fmt(state.capacity)} = ${fmt(result.capacity)} Ah`;
    }

    removeSource.disabled = state.count <= 1;
    addSource.disabled = state.count >= 6;
    seriesMode.classList.toggle('active', state.mode === 'series');
    parallelMode.classList.toggle('active', state.mode === 'parallel');
    seriesMode.setAttribute('aria-pressed', String(state.mode === 'series'));
    parallelMode.setAttribute('aria-pressed', String(state.mode === 'parallel'));

    setObservation(action);
    challengeResult.textContent = '';
    challengeResult.className = 'challenge-result';
    previousCount = state.count;
  }

  function setMode(mode) {
    if (state.mode === mode) return;
    state.mode = mode;
    renderBank({ animate: true, action: 'mode' });
  }

  seriesMode.addEventListener('click', () => setMode('series'));
  parallelMode.addEventListener('click', () => setMode('parallel'));

  addSource.addEventListener('click', () => {
    if (state.count >= 6) return;
    previousCount = state.count;
    state.count += 1;
    renderBank({ animate: true, action: 'add' });
  });

  removeSource.addEventListener('click', () => {
    if (state.count <= 1) return;
    previousCount = state.count;
    state.count -= 1;
    renderBank({ animate: true, action: 'remove' });
  });

  sourceVoltage.addEventListener('input', () => renderBank({ action: 'value' }));
  sourceCapacity.addEventListener('input', () => renderBank({ action: 'value' }));
  sourceVoltage.addEventListener('blur', () => renderBank({ action: 'value' }));
  sourceCapacity.addEventListener('blur', () => renderBank({ action: 'value' }));

  function applyChallenge(next) {
    challenge = next;
    state.voltage = next.voltage;
    state.capacity = next.capacity;
    state.count = 1;
    state.mode = next.mode === 'series' ? 'parallel' : 'series';
    sourceVoltage.value = next.voltage;
    sourceCapacity.value = next.capacity;
    sourceVoltage.disabled = true;
    sourceCapacity.disabled = true;
    challengePrompt.textContent = next.text;
    challengeSourceNote.textContent = `Fontes disponíveis: ${fmt(next.voltage)} V · ${fmt(next.capacity)} Ah`;
    renderBank({ animate: true, action: 'mode' });
  }

  function pickChallenge() {
    const pool = challenges.filter((item) => item !== challenge);
    applyChallenge(pool[Math.floor(Math.random() * pool.length)] || challenges[0]);
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) {
      pickChallenge();
    } else {
      challenge = null;
      sourceVoltage.disabled = false;
      sourceCapacity.disabled = false;
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
  });

  newChallenge.addEventListener('click', pickChallenge);

  checkChallenge.addEventListener('click', () => {
    if (!challenge) return;
    const result = calculate();
    const voltageOk = Math.abs(result.voltage - challenge.targetV) < 0.051;
    const capacityOk = challenge.targetC === null || Math.abs(result.capacity - challenge.targetC) < 0.051;
    const modeOk = state.mode === challenge.mode;
    const countOk = state.count === challenge.count;

    if (voltageOk && capacityOk && modeOk && countOk) {
      challengeResult.textContent = challenge.targetC === null
        ? `${fmt(result.voltage)} V ✓ Banco montado corretamente`
        : `${fmt(result.voltage)} V · ${fmt(result.capacity)} Ah ✓ Desafio concluído`;
      challengeResult.className = 'challenge-result success';
    } else {
      challengeResult.innerHTML = 'Ainda não. Observe o que muda quando as fontes são associadas em <strong>série</strong> ou em <strong>paralelo</strong>.';
      challengeResult.className = 'challenge-result';
    }
  });

  renderBank();
})();
