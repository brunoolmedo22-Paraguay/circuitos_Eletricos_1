(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const voltage = $('voltage');
  const resistance = $('resistance');
  const volumeFlow = $('volumeFlow');
  const currentOut = $('currentOut');
  const powerOut = $('powerOut');
  const thermalPowerOut = $('thermalPowerOut');
  const deltaTOut = $('deltaTOut');
  const thermalNumeric = $('thermalNumeric');
  const flowConversion = $('flowConversion');
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
  const energize = $('energize');
  const turnOff = $('turnOff');
  const quadraticInsight = $('quadraticInsight');
  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeNote = $('challengeNote');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  const numberFields = [voltage.closest('.number-field'), resistance.closest('.number-field')];
  const volumeFlowField = volumeFlow.closest('label');
  const CP_WATER = 4180; // J/(kg·°C), parâmetro térmico do modelo complementar.
  const RHO_WATER = 1000; // kg/m³, hipótese solicitada para a água.
  const LITER_TO_M3 = 1e-3;

  const presets = {
    resistor: {
      label: 'RESISTOR DIDÁTICO',
      V: 12,
      R: 10,
      note: 'Preset didático: 12 V e 10 Ω. Você pode editar ambos livremente.',
    },
    heater: {
      label: 'AQUECEDOR ELÉTRICO',
      V: 120,
      R: 120 / 9.5,
      note: 'Boylestad propõe um aquecedor que drena 9,5 A em 120 V; R é calculada por V/I ≈ 12,63 Ω.',
    },
    shower: {
      label: 'CHUVEIRO DIDÁTICO',
      V: 220,
      R: (220 * 220) / 5000,
      note: 'Preset solicitado: 5,0 kW em 220 V; R = V²/P ≈ 9,68 Ω.',
    },
    boiler: {
      label: 'AQUECEDOR DE ÁGUA',
      V: 240,
      R: (240 * 240) / 4500,
      note: 'Boylestad lista aquecedor de água de 4,5 kW; usando o nível residencial de 240 V do capítulo, R ≈ 12,80 Ω.',
    },
    oven: {
      label: 'FORNO ELÉTRICO',
      V: 240,
      R: (240 * 240) / 12200,
      note: 'Boylestad lista forno/fogão autolimpante de 12,2 kW; usando 240 V, R ≈ 4,72 Ω.',
    },
  };

  let state = {
    powered: true,
    equation: 'vi',
  };
  let challenge = null;
  let lastFrame = performance.now();
  let lastStable = { voltage: 12, resistance: 10, current: 1.2, power: 14.4 };

  const fmt = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  function compactPower(value) {
    if (value >= 1000) return `${fmt(value / 1000, value >= 10000 ? 1 : 2)} kW`;
    return `${fmt(value, value >= 100 ? 0 : 1)} W`;
  }

  function configuredValues() {
    const V = Math.max(0, Math.min(260, Number(voltage.value) || 0));
    const R = Math.max(0.1, Math.min(10000, Number(resistance.value) || 0.1));
    const I = V / R;
    const P = V * I;
    return { V, R, I, P };
  }

  function activeValues() {
    const c = configuredValues();
    return state.powered ? c : { ...c, I: 0, P: 0 };
  }

  function thermalValues() {
    const active = activeValues();
    const qLps = Math.max(0.005, Math.min(1, Number(volumeFlow.value) || 0.05));
    const qM3s = qLps * LITER_TO_M3;
    const mDot = RHO_WATER * qM3s;
    const deltaT = active.P / (mDot * CP_WATER);
    return { qDot: active.P, qLps, qM3s, mDot, deltaT };
  }

  function heatLevel(power) {
    return Math.min(1, Math.log10(power + 1) / Math.log10(15001));
  }

  function updateHeat(power) {
    const normalized = heatLevel(power);
    heatBlur.setAttribute('stdDeviation', (normalized * 10).toFixed(2));
    heatFlood.setAttribute('flood-opacity', (normalized * 0.56).toFixed(3));
    const r = Math.round(50 + normalized * 190);
    const g = Math.round(43 - normalized * 14);
    const b = Math.round(53 - normalized * 26);
    loadBody.style.stroke = `rgb(${r}, ${Math.max(24, g)}, ${Math.max(22, b)})`;
    heatWaves.style.opacity = String(Math.max(0, (normalized - 0.14) / 0.86) * 0.92);
  }

  function updateThermalModel() {
    const { qDot, qLps, mDot, deltaT } = thermalValues();
    thermalPowerOut.textContent = `Q̇ = ${compactPower(qDot)}`;
    deltaTOut.textContent = `ΔT = ${fmt(deltaT, deltaT >= 10 ? 1 : 2)} °C`;
    flowConversion.textContent = `ṁ = ρV̇ = 1000 × (${fmt(qLps, 3)} × 10⁻³) = ${fmt(mDot, 3)} kg/s`;
    thermalNumeric.textContent = `ΔT = ${fmt(qDot, qDot >= 1000 ? 0 : 1)} / (${fmt(mDot, 3)} × 4180) = ${fmt(deltaT, deltaT >= 10 ? 1 : 2)} °C`;
  }

  function updateEquation() {
    const { V, R, I, P } = configuredValues();
    document.querySelectorAll('.equation-tab').forEach((button) => {
      button.classList.toggle('active', button.dataset.eq === state.equation);
    });
    if (state.equation === 'i2r') {
      equationSymbolic.textContent = 'P = I²R';
      equationNumeric.textContent = `P = (${fmt(I, 2)})² × ${fmt(R, R < 10 ? 2 : 1)} = ${compactPower(P)}`;
      powerPill.textContent = 'P = I²R';
    } else if (state.equation === 'v2r') {
      equationSymbolic.textContent = 'P = V²/R';
      equationNumeric.textContent = `P = (${fmt(V, 1)})² / ${fmt(R, R < 10 ? 2 : 1)} = ${compactPower(P)}`;
      powerPill.textContent = 'P = V²/R';
    } else {
      equationSymbolic.textContent = 'P = VI';
      equationNumeric.textContent = `P = ${fmt(V, 1)} × ${fmt(I, 2)} = ${compactPower(P)}`;
      powerPill.textContent = 'P = VI';
    }
  }

  function updateObservation(source = 'general', previous = null) {
    const c = configuredValues();
    if (!state.powered) {
      observation.textContent = 'Circuito desligado: sem corrente, a potência elétrica e a potência térmica ideal caem a zero.';
      return;
    }
    if (source === 'application') {
      observation.textContent = 'A aplicação carregou um conjunto de V e R; a potência resulta desses valores e pode ser alterada manualmente.';
      return;
    }
    if (source === 'flow') {
      observation.textContent = 'A potência elétrica não mudou: aumentar a vazão volumétrica reduz a elevação de temperatura. Com ρ = 1000 kg/m³, o sistema converte L/s em kg/s automaticamente.';
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
    observation.textContent = 'A potência dissipada em W representa a taxa de conversão de energia elétrica; no modelo ideal, Q̇ = P.';
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
    const halved = Math.abs(ratioI - 0.5) < 0.035 && Math.abs(ratioP - 0.25) < 0.03;
    if (doubled) {
      quadraticInsight.innerHTML = '<strong>Corrente ×2</strong><span>Potência ×4</span>';
      quadraticInsight.hidden = false;
      observation.textContent = 'A corrente dobrou; com R constante, a potência quadruplicou por causa de P = I²R.';
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
    const active = activeValues();
    const preset = presets[application.value] || presets.resistor;

    currentOut.textContent = `${fmt(active.I, 2)} A`;
    powerOut.textContent = compactPower(active.P);
    svgCurrent.textContent = `I = ${fmt(active.I, 2)} A`;
    svgPower.textContent = `P = ${compactPower(active.P)}`;
    sourceLabel.textContent = `V = ${fmt(configured.V, 1)} V`;
    loadLabel.textContent = `${preset.label} · ${fmt(configured.R, configured.R < 10 ? 2 : 1)} Ω`;
    powerState.textContent = state.powered ? 'ligado' : 'desligado';
    powerState.classList.toggle('on', state.powered);
    energize.disabled = state.powered;
    turnOff.disabled = !state.powered;

    updateHeat(active.P);
    updateEquation();
    updateThermalModel();
    updateObservation(source, previous);
    if (source === 'voltage' || source === 'resistance') showQuadraticInsight(previous);
    else quadraticInsight.hidden = true;
    clearChallengeResult();
  }

  function stabilizeInput(input, min, max) {
    const val = Math.max(min, Math.min(max, Number(input.value) || min));
    input.value = String(val);
  }

  function updateStable() {
    const c = configuredValues();
    lastStable = { voltage: c.V, resistance: c.R, current: c.I, power: c.P };
  }

  function applyPreset(key) {
    const preset = presets[key] || presets.resistor;
    voltage.value = String(Number(preset.V.toFixed(3)));
    resistance.value = String(Number(preset.R.toFixed(3)));
    applicationNote.textContent = preset.note;
    state.powered = true;
    updateStable();
    render('application');
  }

  voltage.addEventListener('change', () => {
    const previous = { ...lastStable };
    stabilizeInput(voltage, 0, 260);
    render('voltage', previous);
    updateStable();
  });
  resistance.addEventListener('change', () => {
    const previous = { ...lastStable };
    stabilizeInput(resistance, 0.1, 10000);
    render('resistance', previous);
    updateStable();
  });
  voltage.addEventListener('input', () => render('general'));
  resistance.addEventListener('input', () => render('general'));
  volumeFlow.addEventListener('input', () => {
    updateThermalModel();
    updateObservation('flow');
    clearChallengeResult();
  });
  volumeFlow.addEventListener('change', () => {
    stabilizeInput(volumeFlow, 0.005, 1);
    updateThermalModel();
  });

  application.addEventListener('change', () => applyPreset(application.value));

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

  // Corrente convencional animada.
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

    if (active.I <= 0.0001) {
      particles.forEach((dot) => { dot.style.opacity = '0'; });
      requestAnimationFrame(animate);
      return;
    }

    const intensity = active.I / (active.I + 8);
    const visible = Math.max(2, Math.round(2 + intensity * (MAX_PARTICLES - 2)));
    const speed = 45 + intensity * 180;
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

  const challenges = [
    {
      id: 'p40',
      text: 'Com R = 10 Ω, obtenha uma potência de 40 W.',
      note: 'A resistência está bloqueada. Ajuste apenas a tensão.',
      setup: { V: 12, R: 10, qLps: 0.05, lockV: false, lockR: true, lockFlow: false },
      check: ({ P }) => Math.abs(P - 40) <= 0.4,
      success: ({ P }) => `${fmt(P, 1)} W ✓`,
    },
    {
      id: 'quad',
      text: 'Quadruplicate a potência inicial de 3,6 W sem alterar R = 10 Ω.',
      note: 'O alvo é 14,4 W. Observe P = I²R.',
      setup: { V: 6, R: 10, qLps: 0.05, lockV: false, lockR: true, lockFlow: false },
      check: ({ P }) => Math.abs(P - 14.4) <= 0.18,
      success: ({ P }) => `${fmt(P, 1)} W ✓ Potência quadruplicada`,
    },
    {
      id: 'p20',
      text: 'Obtenha 20 W de potência dissipada.',
      note: 'Qualquer combinação de V e R dentro dos limites é válida.',
      setup: { V: 12, R: 10, qLps: 0.05, lockV: false, lockR: false, lockFlow: false },
      check: ({ P }) => Math.abs(P - 20) <= 0.25,
      success: ({ P }) => `${fmt(P, 1)} W ✓`,
    },
    {
      id: 'water25',
      text: 'Com um elemento de 5,0 kW, ajuste a vazão para obter ΔT ≈ 25 °C.',
      note: 'V = 220 V e R ≈ 9,68 Ω estão bloqueados. Ajuste somente a vazão em L/s.',
      setup: { V: 220, R: (220 * 220) / 5000, qLps: 0.05, lockV: true, lockR: true, lockFlow: false },
      check: () => Math.abs(thermalValues().deltaT - 25) <= 0.5,
      success: () => `ΔT = ${fmt(thermalValues().deltaT, 1)} °C ✓`,
    },
  ];

  function setLocks(lockV, lockR, lockFlow) {
    voltage.disabled = !!lockV;
    resistance.disabled = !!lockR;
    volumeFlow.disabled = !!lockFlow;
    numberFields[0].classList.toggle('locked', !!lockV);
    numberFields[1].classList.toggle('locked', !!lockR);
    volumeFlowField.classList.toggle('locked', !!lockFlow);
  }

  function applyChallenge(next) {
    challenge = next;
    application.value = 'resistor';
    voltage.value = String(next.setup.V);
    resistance.value = String(Number(next.setup.R.toFixed(3)));
    volumeFlow.value = String(next.setup.qLps);
    setLocks(next.setup.lockV, next.setup.lockR, next.setup.lockFlow);
    state.powered = true;
    challengePrompt.textContent = next.text;
    challengeNote.textContent = next.note;
    challengeResult.textContent = '';
    challengeResult.className = 'challenge-result';
    updateStable();
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
      setLocks(false, false, false);
      applyPreset(application.value);
    }
  });
  newChallenge.addEventListener('click', pickChallenge);
  checkChallenge.addEventListener('click', () => {
    if (!challenge) return;
    const c = configuredValues();
    if (challenge.check(c)) {
      challengeResult.textContent = challenge.success(c);
      challengeResult.className = 'challenge-result success';
    } else if (challenge.id === 'water25') {
      challengeResult.textContent = `ΔT atual: ${fmt(thermalValues().deltaT, 1)} °C. Ajuste a vazão volumétrica em L/s.`;
      challengeResult.className = 'challenge-result';
    } else {
      challengeResult.textContent = `Potência atual: ${compactPower(c.P)}. Observe como V, I e R participam da dissipação.`;
      challengeResult.className = 'challenge-result';
    }
  });

  applicationNote.textContent = presets.resistor.note;
  render('general');
  requestAnimationFrame(animate);
})();
