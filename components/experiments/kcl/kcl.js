(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';

  const kclSvg = $('kclSvg');
  const voltage = $('voltage');
  const voltageField = $('voltageField');
  const addBranch = $('addBranch');
  const removeBranch = $('removeBranch');
  const branchCountText = $('branchCountText');
  const branchCountValue = $('branchCountValue');
  const branchBadge = $('branchBadge');
  const resistorFields = $('resistorFields');
  const totalCurrentResult = $('totalCurrentResult');
  const totalConductanceNote = $('totalConductanceNote');
  const kclSymbolic = $('kclSymbolic');
  const kclNumeric = $('kclNumeric');
  const dividerFormula = $('dividerFormula');
  const dividerNote = $('dividerNote');
  const observation = $('observation');

  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeNote = $('challengeNote');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  const state = {
    voltage: 12,
    count: 2,
    resistances: [10, 20, 30],
    currents: [1.2, .6],
    total: 1.8,
  };

  let lastChanged = null;
  let lastDirection = null;
  let activeChallenge = null;
  let animationPaths = [];
  let lastFrame = performance.now();
  let phase = 0;

  const challenges = [
    {
      id: 'split-4-2', voltage: 12, count: 2, values: [6, 6],
      text: 'Com V = 12 V, faça I₁ = 4 A e I₂ = 2 A.',
      note: 'Ajuste R₁ e R₂. A fonte permanece fixa.',
      test: (s) => near(s.currents[0], 4, .03) && near(s.currents[1], 2, .03),
      success: (s) => `I₁ = ${formatCurrent(s.currents[0])} · I₂ = ${formatCurrent(s.currents[1])} ✓`,
    },
    {
      id: 'equal', voltage: 12, count: 2, values: [10, 20],
      text: 'Divida igualmente a corrente entre os dois ramos.',
      note: 'Descubra qual relação entre R₁ e R₂ produz I₁ = I₂.',
      test: (s) => relativeNear(s.currents[0], s.currents[1], .01),
      success: (s) => `I₁ = I₂ = ${formatCurrent(s.currents[0])} ✓ Divisão igual`,
    },
    {
      id: 'double', voltage: 12, count: 2, values: [10, 10],
      text: 'Faça o ramo superior conduzir o dobro da corrente do ramo inferior.',
      note: 'O objetivo é I₁ = 2 × I₂. Mais de uma combinação é válida.',
      test: (s) => relativeNear(s.currents[0], 2 * s.currents[1], .015),
      success: (s) => `I₁ = 2 × I₂ ✓ (${formatCurrent(s.currents[0])} e ${formatCurrent(s.currents[1])})`,
    },
    {
      id: 'total-3', voltage: 9, count: 2, values: [9, 9],
      text: 'Com V = 9 V, ajuste os ramos para obter Itotal = 3 A.',
      note: 'Qualquer combinação de R₁ e R₂ que produza 3 A no total é aceita.',
      test: (s) => near(s.total, 3, .025),
      success: (s) => `Itotal = ${formatCurrent(s.total)} ✓`,
    },
  ];

  const fmt = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  function formatResistance(value) {
    const v = Number(value);
    if (v >= 1e6) return `${fmt(v / 1e6, v % 1e6 === 0 ? 0 : 2)} MΩ`;
    if (v >= 1e3) return `${fmt(v / 1e3, v % 1e3 === 0 ? 0 : 2)} kΩ`;
    return `${fmt(v, v < 10 && !Number.isInteger(v) ? 1 : 0)} Ω`;
  }

  function formatCurrent(amps) {
    const a = Math.abs(amps);
    if (a >= 1) return `${fmt(amps, 2)} A`;
    if (a >= 1e-3) return `${fmt(amps * 1e3, 2)} mA`;
    return `${fmt(amps * 1e6, 2)} µA`;
  }

  function near(a, b, tolerance) { return Math.abs(a - b) <= tolerance; }
  function relativeNear(a, b, tolerance) {
    return Math.abs(a - b) <= Math.max(1e-6, Math.max(Math.abs(a), Math.abs(b)) * tolerance);
  }

  function clamp(value, min, max, fallback) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.max(min, Math.min(max, n));
  }

  function subscript(value) {
    const map = { '0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉' };
    return String(value).split('').map((c) => map[c] || c).join('');
  }

  function svgEl(tag, attrs = {}) {
    const el = document.createElementNS(svgNS, tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, String(value)));
    return el;
  }

  function addText(parent, x, y, text, cls, anchor = 'middle') {
    const el = svgEl('text', { x, y, class: cls, 'text-anchor': anchor });
    el.textContent = text;
    parent.appendChild(el);
    return el;
  }

  function addLine(parent, x1, y1, x2, y2, cls = 'svg-wire') {
    const el = svgEl('line', { x1, y1, x2, y2, class: cls });
    parent.appendChild(el);
    return el;
  }

  function resistorPath(x1, x2, y) {
    const lead = 24;
    const start = x1 + lead;
    const end = x2 - lead;
    const steps = 8;
    const dx = (end - start) / steps;
    let d = `M ${x1} ${y} H ${start}`;
    for (let i = 0; i < steps; i += 1) {
      const x = start + dx * (i + 1);
      const yy = i % 2 === 0 ? y - 15 : y + 15;
      d += ` L ${x} ${yy}`;
    }
    d += ` L ${end} ${y} H ${x2}`;
    return d;
  }

  function compute() {
    const V = clamp(voltage.value, .1, 240, state.voltage);
    const values = state.resistances.slice(0, state.count).map((r) => clamp(r, 1, 100000, 10));
    const currents = values.map((r) => V / r);
    const total = currents.reduce((sum, current) => sum + current, 0);
    return { voltage: V, count: state.count, resistances: [...state.resistances], currents, total };
  }

  function renderFields() {
    resistorFields.replaceChildren();
    for (let i = 0; i < state.count; i += 1) {
      const label = document.createElement('label');
      label.className = `resistor-field${activeChallenge ? '' : ''}`;
      label.innerHTML = `<span>R${i + 1}</span><input type="number" min="1" max="100000" step="1" value="${state.resistances[i]}" inputmode="decimal" aria-label="R${i + 1} em ohms"><b>Ω</b><em>${formatCurrent(state.currents[i] || 0)}</em>`;
      const input = label.querySelector('input');
      input.addEventListener('input', () => {
        const raw = Number(input.value);
        if (Number.isFinite(raw)) {
          const oldValue = state.resistances[i];
          const nextValue = clamp(raw, 1, 100000, oldValue);
          lastDirection = nextValue > oldValue ? 'up' : nextValue < oldValue ? 'down' : null;
          state.resistances[i] = nextValue;
        }
        lastChanged = `r${i}`;
        render({ fields: false });
        const currentLabel = label.querySelector('em');
        if (currentLabel) currentLabel.textContent = formatCurrent(state.currents[i] || 0);
      });
      input.addEventListener('blur', () => {
        const oldValue = state.resistances[i];
        state.resistances[i] = clamp(input.value, 1, 100000, oldValue);
        lastDirection = state.resistances[i] > oldValue ? 'up' : state.resistances[i] < oldValue ? 'down' : lastDirection;
        input.value = String(state.resistances[i]);
        lastChanged = `r${i}`;
        render();
      });
      resistorFields.appendChild(label);
    }
  }

  function drawCurrentBadge(parent, x, y, width, text, branch = false) {
    const group = svgEl('g');
    group.appendChild(svgEl('rect', { x, y, width, height: branch ? 30 : 36, rx: branch ? 10 : 12, class: branch ? 'branch-current-bg' : 'current-label-bg' }));
    addText(group, x + width / 2, y + (branch ? 20 : 24), text, branch ? 'branch-current-text' : 'current-label-text');
    parent.appendChild(group);
  }

  function createParticleLayer(path, current, maxDots, speedBase, groupClass) {
    const group = svgEl('g', { class: groupClass });
    kclSvg.appendChild(group);
    const dots = [];
    for (let i = 0; i < maxDots; i += 1) {
      const dot = svgEl('circle', { r: 4.5, class: 'current-particle' });
      group.appendChild(dot);
      dots.push(dot);
    }
    animationPaths.push({ path, current, dots, speedBase });
  }

  function renderCircuit() {
    kclSvg.replaceChildren();
    animationPaths = [];

    const defs = svgEl('defs');
    kclSvg.appendChild(defs);

    const leftX = 230;
    const rightX = 625;
    const nodeY = 200;
    const sourceLeftX = 95;
    const sourceRightX = 710;
    const bottomY = 350;
    const plate1 = 330;
    const plate2 = 385;

    // External loop and source.
    addLine(kclSvg, sourceLeftX, nodeY, leftX, nodeY, 'svg-wire svg-bus');
    addLine(kclSvg, rightX, nodeY, sourceRightX, nodeY, 'svg-wire svg-bus');
    addLine(kclSvg, sourceLeftX, nodeY, sourceLeftX, bottomY, 'svg-wire');
    addLine(kclSvg, sourceLeftX, bottomY, plate1 - 14, bottomY, 'svg-wire');
    addLine(kclSvg, plate2 + 14, bottomY, sourceRightX, bottomY, 'svg-wire');
    addLine(kclSvg, sourceRightX, bottomY, sourceRightX, nodeY, 'svg-wire');
    addLine(kclSvg, plate1, bottomY - 32, plate1, bottomY + 32, 'battery-plate battery-long');
    addLine(kclSvg, plate2, bottomY - 22, plate2, bottomY + 22, 'battery-plate battery-short');
    addText(kclSvg, plate1 - 31, bottomY - 18, '+', 'polarity');
    addText(kclSvg, plate2 + 31, bottomY - 18, '−', 'polarity');
    addText(kclSvg, (plate1 + plate2) / 2, 406, `V = ${fmt(state.voltage, 1)} V`, 'source-label');

    const branchYs = state.count === 2 ? [135, 265] : [115, 200, 285];
    const topY = Math.min(...branchYs);
    const bottomBranchY = Math.max(...branchYs);
    addLine(kclSvg, leftX, topY, leftX, bottomBranchY, 'svg-wire svg-bus');
    addLine(kclSvg, rightX, topY, rightX, bottomBranchY, 'svg-wire svg-bus');

    const leftNode = svgEl('circle', { id: 'leftNode', cx: leftX, cy: nodeY, r: 8, class: `node${activeChallenge ? ' challenge-active' : ''}` });
    const rightNode = svgEl('circle', { id: 'rightNode', cx: rightX, cy: nodeY, r: 8, class: `node${activeChallenge ? ' challenge-active' : ''}` });
    kclSvg.appendChild(leftNode);
    kclSvg.appendChild(rightNode);
    addText(kclSvg, leftX, nodeY - 22, 'NÓ DE DIVISÃO', 'node-label');
    addText(kclSvg, rightX, nodeY - 22, 'RECOMBINAÇÃO', 'node-label');

    for (let i = 0; i < state.count; i += 1) {
      const y = branchYs[i];
      const x1 = 278;
      const x2 = 576;
      addLine(kclSvg, leftX, y, x1, y, 'svg-wire');
      kclSvg.appendChild(svgEl('path', { d: resistorPath(x1, x2, y), class: 'svg-resistor' }));
      addLine(kclSvg, x2, y, rightX, y, 'svg-wire');
      addText(kclSvg, 427, y - 30, `R${i + 1} = ${formatResistance(state.resistances[i])}`, 'component-label');
      drawCurrentBadge(kclSvg, 375, y + 20, 104, `I${subscript(i + 1)} = ${formatCurrent(state.currents[i])}`, true);

      const branchPath = svgEl('path', {
        d: `M ${leftX} ${nodeY} V ${y} H ${x1} ${resistorPath(x1, x2, y).replace(/^M\s*[^H]+H\s*/, '')} H ${rightX} V ${nodeY}`,
        fill: 'none', stroke: 'transparent', 'stroke-width': 1,
      });
      // The compact string above can be hard to read; replace it with a clean path used only for particles.
      branchPath.setAttribute('d', `M ${leftX} ${nodeY} V ${y} H ${rightX} V ${nodeY}`);
      kclSvg.appendChild(branchPath);
      createParticleLayer(branchPath, state.currents[i], 9, 72, `branch-particles branch-${i + 1}`);
    }

    drawCurrentBadge(kclSvg, 104, 153, 118, `Itotal = ${formatCurrent(state.total)}`);
    drawCurrentBadge(kclSvg, 636, 153, 118, `Itotal = ${formatCurrent(state.total)}`);
    addText(kclSvg, 162, 126, 'ENTRA', 'flow-caption');
    addText(kclSvg, 695, 126, 'SAI', 'flow-caption');

    const entryPath = svgEl('path', { d: `M ${plate1} ${bottomY} H ${sourceLeftX} V ${nodeY} H ${leftX}`, fill: 'none', stroke: 'transparent' });
    const exitPath = svgEl('path', { d: `M ${rightX} ${nodeY} H ${sourceRightX} V ${bottomY} H ${plate2}`, fill: 'none', stroke: 'transparent' });
    kclSvg.appendChild(entryPath);
    kclSvg.appendChild(exitPath);
    createParticleLayer(entryPath, state.total, 12, 84, 'total-particles entry');
    createParticleLayer(exitPath, state.total, 12, 84, 'total-particles exit');
  }

  function setObservation(previous, next) {
    observation.classList.remove('special');

    if (state.count >= 2) {
      const allEqualR = state.resistances.slice(0, state.count).every((r) => Math.abs(r - state.resistances[0]) < 1e-9);
      if (allEqualR) {
        observation.textContent = `Resistências iguais dividem igualmente a corrente: ${state.currents.slice(0, state.count).map((i) => formatCurrent(i)).join(' em cada ramo · ')}.`;
        observation.classList.add('special');
        return;
      }
    }

    if (lastChanged && lastChanged.startsWith('r')) {
      const idx = Number(lastChanged.slice(1));
      if (Number.isInteger(idx) && idx < state.count) {
        observation.textContent = lastDirection === 'down'
          ? `R${idx + 1} diminuiu: esse caminho oferece menos oposição e sua corrente aumentou.`
          : lastDirection === 'up'
            ? `R${idx + 1} aumentou: esse caminho conduz menos corrente.`
            : 'A corrente se distribui de forma inversamente relacionada às resistências dos ramos.';
        return;
      }
    }

    if (lastChanged === 'voltage') {
      observation.textContent = next.voltage > previous.voltage
        ? 'Aumentar a tensão eleva todas as correntes dos ramos, mantendo a divisão definida pelas resistências.'
        : 'Reduzir a tensão reduz todas as correntes dos ramos, mantendo a proporção entre elas.';
      return;
    }

    observation.textContent = 'Menor resistência → maior corrente no ramo correspondente. No nó, a corrente total se conserva.';
  }

  function updateMath() {
    const labels = state.currents.map((_, i) => `I${subscript(i + 1)}`);
    kclSymbolic.textContent = `Itotal = ${labels.join(' + ')}`;
    kclNumeric.textContent = `${formatCurrent(state.total)} = ${state.currents.map(formatCurrent).join(' + ')}`;

    if (state.count === 2) {
      dividerFormula.textContent = 'I₁ = Itotal · R₂/(R₁ + R₂)   ·   I₂ = Itotal · R₁/(R₁ + R₂)';
      dividerNote.textContent = 'Em dois ramos, a corrente de cada caminho depende da resistência do outro ramo na regra do divisor.';
    } else {
      dividerFormula.textContent = 'Para três ramos: I₁ = V/R₁ · I₂ = V/R₂ · I₃ = V/R₃';
      dividerNote.textContent = 'A KCL continua válida: a soma das três correntes é exatamente Itotal.';
    }
  }

  function render({ fields = true } = {}) {
    const previous = {
      voltage: state.voltage,
      resistances: [...state.resistances],
      currents: [...state.currents],
      total: state.total,
    };
    const next = compute();
    setObservation(previous, next);
    state.voltage = next.voltage;
    state.currents = next.currents;
    state.total = next.total;

    const countLabel = `${state.count} ${state.count === 1 ? 'ramo' : 'ramos'}`;
    branchCountText.textContent = countLabel;
    branchCountValue.textContent = String(state.count);
    branchBadge.textContent = countLabel;
    totalCurrentResult.textContent = formatCurrent(state.total);
    totalConductanceNote.textContent = `Soma das correntes dos ${state.count} caminhos.`;
    removeBranch.disabled = state.count <= 2 || !!activeChallenge;
    addBranch.disabled = state.count >= 3 || !!activeChallenge;

    if (fields) renderFields();
    updateMath();
    renderCircuit();

    if (!challengePanel.hidden) {
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
  }

  voltage.addEventListener('input', () => {
    const nextV = clamp(voltage.value, .1, 240, state.voltage);
    lastDirection = nextV > state.voltage ? 'up' : nextV < state.voltage ? 'down' : null;
    lastChanged = 'voltage';
    render({ fields: false });
  });
  voltage.addEventListener('blur', () => {
    state.voltage = clamp(voltage.value, .1, 240, state.voltage);
    voltage.value = String(state.voltage);
    lastChanged = 'voltage';
    render();
  });

  addBranch.addEventListener('click', () => {
    if (state.count >= 3 || activeChallenge) return;
    state.count += 1;
    if (!Number.isFinite(state.resistances[state.count - 1])) state.resistances[state.count - 1] = 30;
    lastChanged = null;
    render();
  });

  removeBranch.addEventListener('click', () => {
    if (state.count <= 2 || activeChallenge) return;
    state.count -= 1;
    lastChanged = null;
    render();
  });

  function applyChallenge(challenge) {
    activeChallenge = challenge;
    state.count = challenge.count;
    state.voltage = challenge.voltage;
    voltage.value = String(challenge.voltage);
    challenge.values.forEach((value, index) => { state.resistances[index] = value; });
    voltage.disabled = true;
    voltageField.classList.add('locked');
    challengePrompt.textContent = challenge.text;
    challengeNote.textContent = challenge.note;
    lastChanged = null;
    render();
  }

  function pickChallenge() {
    const pool = challenges.filter((c) => !activeChallenge || c.id !== activeChallenge.id);
    applyChallenge(pool[Math.floor(Math.random() * pool.length)] || challenges[0]);
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) {
      pickChallenge();
    } else {
      activeChallenge = null;
      voltage.disabled = false;
      voltageField.classList.remove('locked');
      challengeResult.textContent = '';
      render();
    }
  });

  newChallenge.addEventListener('click', pickChallenge);

  checkChallenge.addEventListener('click', () => {
    if (!activeChallenge) return;
    if (activeChallenge.test(state)) {
      challengeResult.textContent = activeChallenge.success(state);
      challengeResult.className = 'challenge-result success';
    } else {
      challengeResult.textContent = 'Ainda não. Compare as resistências dos caminhos e observe como a corrente se divide.';
      challengeResult.className = 'challenge-result';
    }
  });

  function animate(now) {
    const dt = Math.min(.05, (now - lastFrame) / 1000);
    lastFrame = now;
    phase += dt;

    const total = Math.max(state.total, 1e-12);
    animationPaths.forEach((layer, layerIndex) => {
      const current = Math.max(0, layer.current);
      if (!layer.path || typeof layer.path.getTotalLength !== 'function') return;
      const length = layer.path.getTotalLength();
      const ratio = current / total;
      const normalized = current / (current + 1.5);
      const isTotalLayer = layerIndex >= state.count;
      const visible = current <= 1e-12
        ? 0
        : isTotalLayer
          ? Math.max(4, Math.round(5 + normalized * (layer.dots.length - 5)))
          : Math.max(1, Math.round(1 + ratio * (layer.dots.length - 1)));
      const speed = layer.speedBase + normalized * 115;
      const travel = (phase * speed) % length;

      layer.dots.forEach((dot, index) => {
        if (index >= visible) {
          dot.style.opacity = '0';
          return;
        }
        const spacing = length / visible;
        const distance = (travel + index * spacing) % length;
        const point = layer.path.getPointAtLength(distance);
        dot.setAttribute('cx', point.x.toFixed(2));
        dot.setAttribute('cy', point.y.toFixed(2));
        dot.style.opacity = String(.42 + normalized * .5);
      });
    });

    requestAnimationFrame(animate);
  }

  render();
  requestAnimationFrame(animate);
})();
