(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const voltage = $('voltage');
  const resistance = $('resistance');
  const currentOut = $('currentOut');
  const powerOut = $('powerOut');
  const svgCurrent = $('svgCurrent');
  const svgPower = $('svgPower');
  const sourceLabel = $('sourceLabel');
  const loadLabel = $('loadLabel');
  const loadBody = $('loadBody');
  const heatBlur = $('heatBlur');
  const heatFlood = $('heatFlood');
  const heatWaves = $('heatWaves');
  const currentPath = $('currentPath');
  const particlesGroup = $('particles');
  const powerState = $('powerState');
  const equationSymbolic = $('equationSymbolic');
  const equationNumeric = $('equationNumeric');
  const powerPill = $('powerPill');
  const observation = $('observation');
  const application = $('application');
  const applicationNote = $('applicationNote');
  const material = $('material');
  const materialNote = $('materialNote');
  const timeOut = $('timeOut');
  const energyOut = $('energyOut');
  const energyMiniOut = $('energyMiniOut');
  const thermalFill = $('thermalFill');
  const energize = $('energize');
  const turnOff = $('turnOff');
  const resetEnergy = $('resetEnergy');
  const quadraticInsight = $('quadraticInsight');
  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeNote = $('challengeNote');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  const numberFields = [voltage.closest('.number-field'), resistance.closest('.number-field')];

  const applicationInfo = {
    resistor: ['ELEMENTO RESISTIVO', 'Elemento resistivo genérico: a energia elétrica fornecida é dissipada no elemento.'],
    wire: ['FIO RESISTIVO', 'O fio é tratado como uma resistência concentrada para destacar a dissipação elétrica.'],
    heater: ['ELEMENTO DE AQUECIMENTO', 'Contexto didático de conversão resistiva de energia elétrica em calor.'],
    shower: ['CHUVEIRO · CONTEXTO DIDÁTICO', 'Exemplo conceitual de uma carga que utiliza aquecimento resistivo; sem dimensionamento de aparelho real.'],
    oven: ['FORNO ELÉTRICO · CONTEXTO DIDÁTICO', 'Exemplo conceitual de aquecimento resistivo; os valores elétricos continuam definidos por V e R.'],
  };

  const materialInfo = {
    generic: 'O valor de R é definido diretamente abaixo; nenhuma propriedade de material é aplicada automaticamente.',
    copper: 'Boylestad: cobre = 100% de condutividade relativa. R continua sendo definida diretamente para não introduzir geometria externa.',
    iron: 'Boylestad: ferro = 14% de condutividade relativa. R continua sendo definida diretamente para não introduzir geometria externa.',
    nichrome: 'Boylestad: nicromo = 1,73% de condutividade relativa. R continua sendo definida diretamente para não introduzir geometria externa.',
  };

  let state = {
    voltage: 12,
    resistance: 10,
    powered: true,
    elapsed: 0,
    energy: 0,
    equation: 'vi',
  };
  let challenge = null;
  let lastFrame = performance.now();
  let lastStable = { voltage: 12, resistance: 10, current: 1.2, power: 14.4 };

  const fmt = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  function compactEnergy(value) {
    if (value >= 1000) return `${fmt(value / 1000, value >= 10000 ? 1 : 2)} kJ`;
    return `${fmt(value, value >= 100 ? 0 : 1)} J`;
  }

  function configuredValues() {
    const V = Math.max(0, Math.min(120, Number(voltage.value) || 0));
    const R = Math.max(0.1, Math.min(10000, Number(resistance.value) || 0.1));
    const I = V / R;
    const P = V * I;
    return { V, R, I, P };
  }

  function activeValues() {
    const c = configuredValues();
    return state.powered ? c : { ...c, I: 0, P: 0 };
  }

  function heatLevel(power) {
    return Math.min(1, Math.log10(power + 1) / Math.log10(3601));
  }

  function updateHeat(power) {
    const normalized = heatLevel(power);
    heatBlur.setAttribute('stdDeviation', (normalized * 9).toFixed(2));
    heatFlood.setAttribute('flood-opacity', (normalized * 0.52).toFixed(3));
    const r = Math.round(50 + normalized * 188);
    const g = Math.round(43 - normalized * 12);
    const b = Math.round(53 - normalized * 23);
    loadBody.style.stroke = `rgb(${r}, ${Math.max(28, g)}, ${Math.max(24, b)})`;
    heatWaves.style.opacity = String(Math.max(0, (normalized - 0.18) / 0.82) * 0.9);
  }

  function updateThermalVisual() {
    // Escala exclusivamente visual: não representa temperatura real.
    const level = 1 - Math.exp(-state.energy / 650);
    thermalFill.style.height = `${Math.min(100, level * 100).toFixed(1)}%`;
    energyOut.textContent = compactEnergy(state.energy);
    energyMiniOut.textContent = compactEnergy(state.energy);
    timeOut.textContent = `${fmt(state.elapsed, 1)} s`;
  }

  function updateEquation() {
    const { V, R, I, P } = configuredValues();
    document.querySelectorAll('.equation-tab').forEach((button) => {
      button.classList.toggle('active', button.dataset.eq === state.equation);
    });
    if (state.equation === 'i2r') {
      equationSymbolic.textContent = 'P = I²R';
      equationNumeric.textContent = `P = (${fmt(I, 2)})² × ${fmt(R, R < 10 ? 1 : 0)} = ${fmt(P, 1)} W`;
      powerPill.textContent = 'P = I²R';
    } else if (state.equation === 'v2r') {
      equationSymbolic.textContent = 'P = V²/R';
      equationNumeric.textContent = `P = (${fmt(V, 1)})² / ${fmt(R, R < 10 ? 1 : 0)} = ${fmt(P, 1)} W`;
      powerPill.textContent = 'P = V²/R';
    } else {
      equationSymbolic.textContent = 'P = VI';
      equationNumeric.textContent = `P = ${fmt(V, 1)} × ${fmt(I, 2)} = ${fmt(P, 1)} W`;
      powerPill.textContent = 'P = VI';
    }
  }

  function updateObservation(source = 'general', previous = null) {
    const c = configuredValues();
    if (!state.powered) {
      observation.textContent = 'Circuito desligado: sem corrente, não há potência elétrica sendo dissipada no elemento.';
      return;
    }
    if (source === 'voltage' && previous) {
      observation.textContent = c.V > previous.voltage
        ? 'Aumentar a tensão elevou a corrente e a potência dissipada.'
        : 'Reduzir a tensão diminuiu a corrente e a potência dissipada.';
      return;
    }
    if (source === 'resistance' && previous) {
      observation.textContent = c.R > previous.resistance
        ? 'Com tensão constante, aumentar R reduziu a corrente e a potência dissipada.'
        : 'Com tensão constante, reduzir R elevou a corrente e a potência dissipada.';
      return;
    }
    observation.textContent = 'Com o circuito energizado, a corrente atravessa a resistência e há dissipação de potência.';
  }

  function showQuadraticInsight(previous) {
    const c = configuredValues();
    if (!previous || Math.abs(c.R - previous.resistance) > Math.max(0.01, c.R * 0.002) || previous.current <= 0) {
      quadraticInsight.hidden = true;
      return;
    }
    const ratioI = c.I / previous.current;
    const ratioP = c.P / previous.power;
    const doubled = Math.abs(ratioI - 2) < 0.07 && Math.abs(ratioP - 4) < 0.2;
    const halved = Math.abs(ratioI - 0.5) < 0.035 && Math.abs(ratioP - 0.25) < 0.025;
    if (doubled) {
      quadraticInsight.innerHTML = '<strong>Corrente ×2</strong><span>Potência ×4</span>';
      quadraticInsight.hidden = false;
      observation.textContent = 'A corrente dobrou; com R constante, a potência quadruplicou por causa da relação P = I²R.';
    } else if (halved) {
      quadraticInsight.innerHTML = '<strong>Corrente ÷2</strong><span>Potência ÷4</span>';
      quadraticInsight.hidden = false;
    } else {
      quadraticInsight.hidden = true;
    }
  }

  function clearChallengeResult() {
    if (!challengePanel.hidden) {
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
  }

  function render(source = 'general', previous = null) {
    const configured = configuredValues();
    state.voltage = configured.V;
    state.resistance = configured.R;
    const active = activeValues();

    currentOut.textContent = `${fmt(active.I, 2)} A`;
    powerOut.textContent = `${fmt(active.P, 1)} W`;
    svgCurrent.textContent = `I = ${fmt(active.I, 2)} A`;
    svgPower.textContent = `P = ${fmt(active.P, 1)} W`;
    sourceLabel.textContent = `V = ${fmt(configured.V, 1)} V`;
    loadLabel.textContent = `${applicationInfo[application.value][0]} · ${fmt(configured.R, configured.R < 10 ? 1 : 0)} Ω`;
    powerState.textContent = state.powered ? 'energizado' : 'desligado';
    powerState.classList.toggle('on', state.powered);
    energize.disabled = state.powered;
    turnOff.disabled = !state.powered;
    updateHeat(active.P);
    updateEquation();
    updateObservation(source, previous);
    if (source === 'voltage' || source === 'resistance') showQuadraticInsight(previous);
    else quadraticInsight.hidden = true;
    updateThermalVisual();
    clearChallengeResult();
  }

  function stabilizeInput(input, min, max) {
    const val = Math.max(min, Math.min(max, Number(input.value) || min));
    input.value = String(val);
  }

  voltage.addEventListener('change', () => {
    const previous = { ...lastStable };
    stabilizeInput(voltage, 0, 120);
    render('voltage', previous);
    const c = configuredValues();
    lastStable = { voltage: c.V, resistance: c.R, current: c.I, power: c.P };
  });
  resistance.addEventListener('change', () => {
    const previous = { ...lastStable };
    stabilizeInput(resistance, 0.1, 10000);
    render('resistance', previous);
    const c = configuredValues();
    lastStable = { voltage: c.V, resistance: c.R, current: c.I, power: c.P };
  });
  voltage.addEventListener('input', () => render('general'));
  resistance.addEventListener('input', () => render('general'));

  application.addEventListener('change', () => {
    applicationNote.textContent = applicationInfo[application.value][1];
    render('general');
  });
  material.addEventListener('change', () => {
    materialNote.textContent = materialInfo[material.value];
  });

  document.querySelectorAll('.equation-tab').forEach((button) => {
    button.addEventListener('click', () => {
      state.equation = button.dataset.eq;
      updateEquation();
    });
  });

  energize.addEventListener('click', () => {
    state.powered = true;
    render('general');
  });
  turnOff.addEventListener('click', () => {
    state.powered = false;
    render('general');
  });
  resetEnergy.addEventListener('click', () => {
    state.elapsed = 0;
    state.energy = 0;
    state.powered = false;
    render('general');
  });

  // ---------------------------------------------------------------------
  // Corrente convencional: mesma linguagem visual dos experimentos prévios.
  // ---------------------------------------------------------------------
  const MAX_PARTICLES = 13;
  const particles = [];
  for (let i = 0; i < MAX_PARTICLES; i += 1) {
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('r', '5');
    dot.setAttribute('class', 'current-particle');
    particlesGroup.appendChild(dot);
    particles.push(dot);
  }
  const pathLength = currentPath.getTotalLength();
  let travel = 0;

  function animate(now) {
    const dt = Math.min(0.05, Math.max(0, (now - lastFrame) / 1000));
    lastFrame = now;
    const active = activeValues();

    if (state.powered) {
      state.elapsed += dt;
      state.energy += active.P * dt;
      updateThermalVisual();
    }

    if (active.I <= 0.0001) {
      particles.forEach((dot) => { dot.style.opacity = '0'; });
      requestAnimationFrame(animate);
      return;
    }

    const intensity = active.I / (active.I + 4.5);
    const visible = Math.max(2, Math.round(2 + intensity * (MAX_PARTICLES - 2)));
    const speed = 45 + intensity * 175;
    travel = (travel + speed * dt) % pathLength;

    particles.forEach((dot, index) => {
      if (index >= visible) {
        dot.style.opacity = '0';
        return;
      }
      const spacing = pathLength / visible;
      const distance = (travel + index * spacing) % pathLength;
      const point = currentPath.getPointAtLength(distance);
      dot.setAttribute('cx', point.x.toFixed(2));
      dot.setAttribute('cy', point.y.toFixed(2));
      dot.style.opacity = String(0.48 + intensity * 0.48);
    });
    requestAnimationFrame(animate);
  }

  // ---------------------------------------------------------------------
  // Desafios: objetivos possíveis dentro dos limites do experimento.
  // ---------------------------------------------------------------------
  const challenges = [
    {
      id: 'p40',
      text: 'Com R = 10 Ω, obtenha uma potência de 40 W.',
      note: 'A resistência está bloqueada. Ajuste apenas a tensão.',
      setup: { V: 12, R: 10, lockV: false, lockR: true },
      check: ({ P }) => Math.abs(P - 40) <= 0.4,
      success: ({ P }) => `${fmt(P, 1)} W ✓`,
    },
    {
      id: 'quad',
      text: 'Quadruplicate a potência inicial de 3,6 W sem alterar R = 10 Ω.',
      note: 'O alvo é 14,4 W. Observe o comportamento quadrático com a corrente.',
      setup: { V: 6, R: 10, lockV: false, lockR: true },
      check: ({ P }) => Math.abs(P - 14.4) <= 0.18,
      success: ({ P }) => `${fmt(P, 1)} W ✓ Potência quadruplicada`,
    },
    {
      id: 'p20',
      text: 'Obtenha 20 W de potência dissipada.',
      note: 'Qualquer combinação de V e R dentro dos limites é válida.',
      setup: { V: 12, R: 10, lockV: false, lockR: false },
      check: ({ P }) => Math.abs(P - 20) <= 0.25,
      success: ({ P }) => `${fmt(P, 1)} W ✓`,
    },
    {
      id: 'e200',
      text: 'Entregue 200 J de energia ao elemento.',
      note: 'Ajuste V e R, clique em Energizar e acompanhe E = Pt.',
      setup: { V: 20, R: 10, lockV: false, lockR: false, resetEnergy: true },
      check: () => Math.abs(state.energy - 200) <= 12 || state.energy >= 200,
      success: () => `${compactEnergy(state.energy)} ✓ Energia atingida`,
    },
  ];

  function setLocks(lockV, lockR) {
    voltage.disabled = !!lockV;
    resistance.disabled = !!lockR;
    numberFields[0].classList.toggle('locked', !!lockV);
    numberFields[1].classList.toggle('locked', !!lockR);
  }

  function applyChallenge(next) {
    challenge = next;
    voltage.value = String(next.setup.V);
    resistance.value = String(next.setup.R);
    setLocks(next.setup.lockV, next.setup.lockR);
    if (next.setup.resetEnergy) {
      state.elapsed = 0;
      state.energy = 0;
      state.powered = false;
    }
    challengePrompt.textContent = next.text;
    challengeNote.textContent = next.note;
    challengeResult.textContent = '';
    challengeResult.className = 'challenge-result';
    const c = configuredValues();
    lastStable = { voltage: c.V, resistance: c.R, current: c.I, power: c.P };
    render('general');
  }

  function pickChallenge() {
    const pool = challenges.filter((item) => !challenge || item.id !== challenge.id);
    applyChallenge(pool[Math.floor(Math.random() * pool.length)] || challenges[0]);
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) pickChallenge();
    else {
      challenge = null;
      setLocks(false, false);
      render('general');
    }
  });
  newChallenge.addEventListener('click', pickChallenge);
  checkChallenge.addEventListener('click', () => {
    if (!challenge) return;
    const c = configuredValues();
    if (challenge.check(c)) {
      challengeResult.textContent = challenge.success(c);
      challengeResult.className = 'challenge-result success';
    } else if (challenge.id === 'e200') {
      challengeResult.textContent = `Energia atual: ${compactEnergy(state.energy)}. Continue energizando ou ajuste a potência.`;
      challengeResult.className = 'challenge-result';
    } else {
      challengeResult.textContent = `Potência atual: ${fmt(c.P, 1)} W. Observe como V, I e R participam da dissipação.`;
      challengeResult.className = 'challenge-result';
    }
  });

  applicationNote.textContent = applicationInfo[application.value][1];
  materialNote.textContent = materialInfo[material.value];
  render('general');
  requestAnimationFrame(animate);
})();
