(() => {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const $ = (id) => document.getElementById(id);

  const circuitSvg = $('circuitSvg');
  const equivalentSvg = $('equivalentSvg');
  const modePill = $('modePill');
  const modeBadge = $('modeBadge');
  const countBadge = $('countBadge');
  const countText = $('countText');
  const countValue = $('countValue');
  const seriesMode = $('seriesMode');
  const parallelMode = $('parallelMode');
  const addResistor = $('addResistor');
  const removeResistor = $('removeResistor');
  const resistorFields = $('resistorFields');
  const eqResistance = $('eqResistance');
  const eqModeNote = $('eqModeNote');
  const symbolicRelation = $('symbolicRelation');
  const numericRelation = $('numericRelation');
  const observation = $('observation');
  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeNote = $('challengeNote');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  const state = {
    mode: 'series',
    count: 2,
    values: [10, 20, 30, 40, 50, 60],
  };

  let previousCount = state.count;
  let challenge = null;

  const challenges = [
    {
      id: 'series60',
      text: 'R₁ = 10 Ω e R₂ = 20 Ω. Adicione um terceiro resistor e obtenha Req = 60 Ω em série.',
      note: 'Os dois resistores fornecidos ficam fixos; determine o valor de R₃.',
      startMode: 'parallel', startCount: 2, values: [10, 20, 30], locked: [true, true, false],
      targetMode: 'series', targetCount: 3, targetReq: 60,
    },
    {
      id: 'parallel50',
      text: 'Usando dois resistores de 100 Ω, obtenha Req = 50 Ω.',
      note: 'Os valores são fixos. Escolha a associação correta.',
      startMode: 'series', startCount: 2, values: [100, 100], locked: [true, true],
      targetMode: 'parallel', targetCount: 2, targetReq: 50,
    },
    {
      id: 'series90',
      text: 'Usando três resistores de 30 Ω, obtenha Req = 90 Ω.',
      note: 'Os valores são fixos. Escolha a associação correta.',
      startMode: 'parallel', startCount: 3, values: [30, 30, 30], locked: [true, true, true],
      targetMode: 'series', targetCount: 3, targetReq: 90,
    },
    {
      id: 'parallel10',
      text: 'Usando três resistores de 30 Ω, obtenha Req = 10 Ω.',
      note: 'Os valores são fixos. Escolha a associação correta.',
      startMode: 'series', startCount: 3, values: [30, 30, 30], locked: [true, true, true],
      targetMode: 'parallel', targetCount: 3, targetReq: 10,
    },
  ];

  const fmtNumber = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });

  function formatOhms(value) {
    const v = Number(value);
    if (!Number.isFinite(v)) return '—';
    if (Math.abs(v) >= 1000) return `${fmtNumber(v / 1000, 2)} kΩ`;
    return `${fmtNumber(v, v < 10 ? 2 : 1)} Ω`;
  }

  function plainOhms(value) {
    const v = Number(value);
    if (!Number.isFinite(v)) return '—';
    return fmtNumber(v, v < 10 ? 2 : 1);
  }

  function svgEl(name, attrs = {}) {
    const el = document.createElementNS(SVG_NS, name);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  }

  function addLine(parent, x1, y1, x2, y2, cls = 'svg-wire') {
    parent.appendChild(svgEl('line', { x1, y1, x2, y2, class: cls }));
  }

  function addText(parent, x, y, text, cls, anchor = 'middle') {
    const node = svgEl('text', { x, y, class: cls, 'text-anchor': anchor });
    node.textContent = text;
    parent.appendChild(node);
    return node;
  }

  function resistorPath(x1, x2, y) {
    const lead = Math.min(20, (x2 - x1) * .16);
    const start = x1 + lead;
    const end = x2 - lead;
    const width = end - start;
    const sections = 8;
    const dx = width / sections;
    let d = `M ${x1} ${y} L ${start} ${y}`;
    for (let i = 0; i <= sections; i += 1) {
      const x = start + dx * i;
      const yy = i === 0 || i === sections ? y : y + (i % 2 ? -14 : 14);
      d += ` L ${x} ${yy}`;
    }
    d += ` L ${x2} ${y}`;
    return d;
  }

  function drawResistor(parent, x1, x2, y, index, entering = false) {
    const group = svgEl('g', { class: `resistor-unit${entering ? ' entering' : ''}` });
    group.appendChild(svgEl('path', { d: resistorPath(x1, x2, y), class: 'svg-resistor' }));
    const center = (x1 + x2) / 2;
    addText(group, center, y - 28, `R${index + 1}`, 'resistor-label');
    addText(group, center, y + 34, formatOhms(state.values[index]), 'resistor-value');
    parent.appendChild(group);
  }


  function drawParallelResistor(parent, x1, x2, y, index, entering = false) {
    const group = svgEl('g', { class: `resistor-unit${entering ? ' entering' : ''}` });
    group.appendChild(svgEl('path', { d: resistorPath(x1, x2, y), class: 'svg-resistor' }));
    // Em paralelo, os rótulos ficam no trecho reto à esquerda do resistor.
    // Isso mantém seis ramos perfeitamente legíveis sem sobrepor os vizinhos.
    addText(group, 166, y - 6, `R${index + 1}`, 'resistor-label');
    addText(group, 166, y + 12, formatOhms(state.values[index]), 'resistor-value');
    parent.appendChild(group);
  }

  function drawTerminal(parent, x, y, label, anchor = 'middle') {
    parent.appendChild(svgEl('circle', { cx: x, cy: y, r: 7, class: 'svg-terminal' }));
    addText(parent, x, y - 18, label, 'svg-terminal-label', anchor);
  }

  function renderSeries(animateNew) {
    const n = state.count;
    const y = 172;
    const left = 58;
    const right = 762;
    const totalWidth = right - left;
    const slot = totalWidth / n;

    drawTerminal(circuitSvg, 40, y, 'A');
    drawTerminal(circuitSvg, 780, y, 'B');
    addLine(circuitSvg, 47, y, left, y, 'svg-wire svg-bus');
    addLine(circuitSvg, right, y, 773, y, 'svg-wire svg-bus');

    for (let i = 0; i < n; i += 1) {
      const x1 = left + i * slot + 6;
      const x2 = left + (i + 1) * slot - 6;
      drawResistor(circuitSvg, x1, x2, y, i, animateNew && i === n - 1 && n > previousCount);
      if (i < n - 1) addLine(circuitSvg, x2, y, x2 + 12, y);
    }

    addText(circuitSvg, 410, 282, 'um único caminho entre A e B', 'resistor-value');
  }

  function renderParallel(animateNew) {
    const n = state.count;
    const leftBus = 122;
    const rightBus = 698;
    const top = 62;
    const bottom = 288;
    const gap = n === 1 ? 0 : (bottom - top) / (n - 1);

    addLine(circuitSvg, leftBus, top - 18, leftBus, bottom + 18, 'svg-wire svg-bus');
    addLine(circuitSvg, rightBus, top - 18, rightBus, bottom + 18, 'svg-wire svg-bus');
    addLine(circuitSvg, 46, 175, leftBus, 175, 'svg-wire svg-bus');
    addLine(circuitSvg, rightBus, 175, 774, 175, 'svg-wire svg-bus');
    drawTerminal(circuitSvg, 39, 175, 'A');
    drawTerminal(circuitSvg, 781, 175, 'B');

    circuitSvg.appendChild(svgEl('circle', { cx: leftBus, cy: 175, r: 6, class: 'branch-node' }));
    circuitSvg.appendChild(svgEl('circle', { cx: rightBus, cy: 175, r: 6, class: 'branch-node' }));

    for (let i = 0; i < n; i += 1) {
      const y = n === 1 ? 175 : top + gap * i;
      addLine(circuitSvg, leftBus, y, 220, y);
      addLine(circuitSvg, 600, y, rightBus, y);
      drawParallelResistor(circuitSvg, 220, 600, y, i, animateNew && i === n - 1 && n > previousCount);
    }

    addText(circuitSvg, 410, 326, 'cada resistor cria um caminho adicional entre os mesmos nós A e B', 'resistor-value');
  }

  function calculateReq() {
    const values = state.values.slice(0, state.count).map((v) => Math.max(1, Math.min(10000, Number(v) || 1)));
    if (state.mode === 'series') return values.reduce((sum, value) => sum + value, 0);
    const conductance = values.reduce((sum, value) => sum + 1 / value, 0);
    return conductance > 0 ? 1 / conductance : 0;
  }

  function renderEquivalent(req) {
    equivalentSvg.replaceChildren();
    const y = 62;
    addLine(equivalentSvg, 18, y, 54, y);
    addLine(equivalentSvg, 246, y, 282, y);
    equivalentSvg.appendChild(svgEl('circle', { cx: 18, cy: y, r: 6, class: 'svg-terminal' }));
    equivalentSvg.appendChild(svgEl('circle', { cx: 282, cy: y, r: 6, class: 'svg-terminal' }));
    equivalentSvg.appendChild(svgEl('path', { d: resistorPath(54, 246, y), class: 'svg-resistor' }));
    addText(equivalentSvg, 150, 27, 'Req', 'eq-label');
    addText(equivalentSvg, 150, 110, formatOhms(req), 'resistor-value');
  }

  function updateRelations(req) {
    const values = state.values.slice(0, state.count);
    if (state.mode === 'series') {
      symbolicRelation.textContent = `Req = ${values.map((_, i) => `R${toSubscript(i + 1)}`).join(' + ')}`;
      numericRelation.textContent = `Req = ${values.map((v) => plainOhms(v)).join(' + ')} = ${formatOhms(req)}`;
      eqModeNote.textContent = 'soma das resistências';
    } else {
      symbolicRelation.textContent = `1/Req = ${values.map((_, i) => `1/R${toSubscript(i + 1)}`).join(' + ')}`;
      numericRelation.textContent = `1/Req = ${values.map((v) => `1/${plainOhms(v)}`).join(' + ')}  →  Req = ${formatOhms(req)}`;
      eqModeNote.textContent = 'combinação dos caminhos em paralelo';
    }
  }

  function toSubscript(value) {
    const map = { '0':'₀', '1':'₁', '2':'₂', '3':'₃', '4':'₄', '5':'₅', '6':'₆', '7':'₇', '8':'₈', '9':'₉' };
    return String(value).split('').map((c) => map[c] || c).join('');
  }

  function setObservation(action = 'mode') {
    if (state.mode === 'series') {
      observation.textContent = action === 'add'
        ? 'Adicionar resistência em série aumenta a resistência equivalente.'
        : action === 'remove'
          ? 'Remover resistência em série reduz a resistência equivalente.'
          : 'Em série, as resistências se somam porque há um único caminho entre os terminais.';
    } else {
      observation.textContent = action === 'add'
        ? 'Mesmo adicionando um resistor, Req diminuiu porque surgiu outro caminho para a corrente.'
        : action === 'remove'
          ? 'Ao retirar um ramo em paralelo, há menos caminhos disponíveis e Req aumenta.'
          : 'Em paralelo, adicionar um novo ramo reduz a resistência equivalente.';
    }
  }

  function lockedFor(index) {
    return !!(challenge && challenge.locked && challenge.locked[index]);
  }

  function renderFields() {
    resistorFields.replaceChildren();
    for (let i = 0; i < state.count; i += 1) {
      const label = document.createElement('label');
      label.className = `resistor-field${lockedFor(i) ? ' locked' : ''}`;
      label.innerHTML = `<span>R${i + 1}</span><input type="number" min="1" max="10000" step="1" value="${state.values[i]}" aria-label="R${i + 1} em ohms" ${lockedFor(i) ? 'disabled' : ''}><b>Ω</b>`;
      const input = label.querySelector('input');
      input.addEventListener('input', () => {
        const raw = Number(input.value);
        if (Number.isFinite(raw)) state.values[i] = Math.max(1, Math.min(10000, raw));
        renderCircuit({ action: 'value' });
      });
      input.addEventListener('blur', () => {
        state.values[i] = Math.max(1, Math.min(10000, Number(input.value) || 1));
        input.value = String(state.values[i]);
        renderCircuit({ action: 'value' });
      });
      resistorFields.appendChild(label);
    }
  }

  function renderCircuit({ animate = false, action = 'mode', fields = true } = {}) {
    const req = calculateReq();
    circuitSvg.replaceChildren();
    if (state.mode === 'series') renderSeries(animate);
    else renderParallel(animate);

    if (animate) {
      circuitSvg.classList.remove('redrawing');
      void circuitSvg.getBoundingClientRect();
      circuitSvg.classList.add('redrawing');
      window.setTimeout(() => circuitSvg.classList.remove('redrawing'), 540);
    }

    renderEquivalent(req);
    updateRelations(req);
    if (fields) renderFields();

    const countLabel = `${state.count} ${state.count === 1 ? 'resistor' : 'resistores'}`;
    countText.textContent = countLabel;
    countValue.textContent = String(state.count);
    countBadge.textContent = countLabel;
    modeBadge.textContent = state.mode === 'series' ? 'Série' : 'Paralelo';
    modePill.textContent = state.mode === 'series' ? 'Série' : 'Paralelo';
    eqResistance.textContent = formatOhms(req);

    removeResistor.disabled = state.count <= 2 || !!(challenge && state.count <= challenge.startCount);
    addResistor.disabled = state.count >= 6;
    seriesMode.classList.toggle('active', state.mode === 'series');
    parallelMode.classList.toggle('active', state.mode === 'parallel');
    seriesMode.setAttribute('aria-pressed', String(state.mode === 'series'));
    parallelMode.setAttribute('aria-pressed', String(state.mode === 'parallel'));

    setObservation(action);
    if (challengePanel.hidden === false) {
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
    previousCount = state.count;
  }

  function setMode(mode) {
    if (state.mode === mode) return;
    state.mode = mode;
    renderCircuit({ animate: true, action: 'mode' });
  }

  seriesMode.addEventListener('click', () => setMode('series'));
  parallelMode.addEventListener('click', () => setMode('parallel'));

  addResistor.addEventListener('click', () => {
    if (state.count >= 6) return;
    previousCount = state.count;
    state.count += 1;
    if (!Number.isFinite(state.values[state.count - 1])) state.values[state.count - 1] = 10;
    renderCircuit({ animate: true, action: 'add' });
  });

  removeResistor.addEventListener('click', () => {
    if (state.count <= 2) return;
    if (challenge && state.count <= challenge.startCount) return;
    previousCount = state.count;
    state.count -= 1;
    renderCircuit({ animate: true, action: 'remove' });
  });

  function applyChallenge(next) {
    challenge = next;
    state.mode = next.startMode;
    state.count = next.startCount;
    for (let i = 0; i < next.values.length; i += 1) state.values[i] = next.values[i];
    challengePrompt.textContent = next.text;
    challengeNote.textContent = next.note;
    renderCircuit({ animate: true, action: 'mode' });
  }

  function pickChallenge() {
    const pool = challenges.filter((item) => !challenge || item.id !== challenge.id);
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
      state.mode = 'series';
      state.count = 2;
      state.values = [10, 20, 30, 40, 50, 60];
      challengeResult.textContent = '';
      renderCircuit({ animate: true, action: 'mode' });
    }
  });

  newChallenge.addEventListener('click', pickChallenge);

  checkChallenge.addEventListener('click', () => {
    if (!challenge) return;
    const req = calculateReq();
    const tolerance = Math.max(.05, challenge.targetReq * .003);
    const reqOk = Math.abs(req - challenge.targetReq) <= tolerance;
    const modeOk = state.mode === challenge.targetMode;
    const countOk = state.count === challenge.targetCount;

    if (reqOk && modeOk && countOk) {
      challengeResult.textContent = `${formatOhms(req)} ✓ Associação correta`;
      challengeResult.className = 'challenge-result success';
    } else {
      challengeResult.innerHTML = `Ainda não. Req atual: <strong>${formatOhms(req)}</strong>. Observe como Req se comporta em série e em paralelo.`;
      challengeResult.className = 'challenge-result';
    }
  });

  renderCircuit();
})();
