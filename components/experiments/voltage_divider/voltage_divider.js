(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const vin = $('vin');
  const r1 = $('r1');
  const r2 = $('r2');
  const vinField = $('vinField');

  const vinLabel = $('vinLabel');
  const r1Label = $('r1Label');
  const r2Label = $('r2Label');
  const vr1Label = $('vr1Label');
  const vr2Label = $('vr2Label');
  const voutSvg = $('voutSvg');
  const currentSvg = $('currentSvg');
  const sumValues = $('sumValues');
  const equationValues = $('equationValues');
  const voutResult = $('voutResult');
  const ratioResult = $('ratioResult');
  const currentResult = $('currentResult');
  const observation = $('observation');

  const currentPath = $('currentPath');
  const particlesGroup = $('particles');

  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  const state = {
    vin: 12,
    r1: 1000,
    r2: 2000,
    current: 0.004,
    vout: 8,
    vr1: 4,
    ratio: 2 / 3,
  };

  const ratioHistory = [{ ratio: state.ratio, total: state.r1 + state.r2 }];
  let activeChallenge = null;
  let lastChanged = null;

  const challenges = [
    { vin: 12, target: 5, r1: 1000, r2: 1000, text: 'Com Vin = 12 V, obtenha Vout = 5 V.' },
    { vin: 10, target: 5, r1: 1000, r2: 2000, text: 'Com Vin = 10 V, obtenha exatamente metade da tensão na saída.' },
    { vin: 9, target: 3, r1: 1000, r2: 1000, text: 'Faça Vout = 3 V usando Vin = 9 V.' },
    { vin: 15, target: 10, r1: 2200, r2: 2200, text: 'Com Vin = 15 V, obtenha Vout = 10 V.' },
    { vin: 24, target: 6, r1: 1000, r2: 1000, text: 'Com Vin = 24 V, obtenha Vout = 6 V.' },
  ];

  const fmt = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  function formatResistance(value) {
    const v = Number(value);
    if (v >= 1e6) return `${fmt(v / 1e6, v % 1e6 === 0 ? 0 : 2)} MΩ`;
    if (v >= 1e3) return `${fmt(v / 1e3, v % 1e3 === 0 ? 0 : 2)} kΩ`;
    return `${fmt(v, 0)} Ω`;
  }

  function formatCurrent(amps) {
    const a = Math.abs(amps);
    if (a >= 1) return `${fmt(amps, 2)} A`;
    if (a >= 1e-3) return `${fmt(amps * 1e3, 2)} mA`;
    return `${fmt(amps * 1e6, 2)} µA`;
  }

  function clampInput(input, min, max, fallback) {
    const raw = Number(input.value);
    if (!Number.isFinite(raw)) return fallback;
    return Math.max(min, Math.min(max, raw));
  }

  function compute() {
    const V = clampInput(vin, 0.1, 1000, state.vin);
    const R1 = clampInput(r1, 1, 1e6, state.r1);
    const R2 = clampInput(r2, 1, 1e6, state.r2);
    const total = R1 + R2;
    const I = V / total;
    const VR1 = I * R1;
    const Vout = I * R2;
    const ratio = R2 / total;
    return { vin: V, r1: R1, r2: R2, current: I, vr1: VR1, vout: Vout, ratio, total };
  }

  function detectRatioInsight(next) {
    const sameScaleEarlier = ratioHistory.find((entry) =>
      Math.abs(entry.ratio - next.ratio) < 1e-6 &&
      Math.max(entry.total, next.total) / Math.min(entry.total, next.total) >= 1.8
    );
    if (sameScaleEarlier) return true;
    ratioHistory.push({ ratio: next.ratio, total: next.total });
    if (ratioHistory.length > 30) ratioHistory.shift();
    return false;
  }

  function setObservation(next, ratioInsight) {
    observation.classList.remove('special');

    if (ratioInsight) {
      observation.textContent = 'Embora os valores tenham mudado, a proporção entre R₁ e R₂ permaneceu igual; por isso Vout não mudou.';
      observation.classList.add('special');
      return;
    }

    if (Math.abs(next.r1 - next.r2) / Math.max(next.r1, next.r2) < 1e-9) {
      observation.textContent = 'Com resistores iguais, Vout corresponde exatamente à metade de Vin.';
      observation.classList.add('special');
      return;
    }

    if (lastChanged === 'r2') {
      observation.textContent = next.r2 > state.r2
        ? 'Aumentar R₂ faz uma parcela maior da tensão aparecer em Vout.'
        : 'Reduzir R₂ faz uma parcela menor da tensão aparecer em Vout.';
      return;
    }

    if (lastChanged === 'r1') {
      observation.textContent = next.r1 > state.r1
        ? 'Aumentar R₁ reduz a tensão disponível em Vout.'
        : 'Reduzir R₁ aumenta a tensão disponível em Vout.';
      return;
    }

    if (lastChanged === 'vin') {
      observation.textContent = next.vin > state.vin
        ? 'Mantendo a razão R₁/R₂, aumentar Vin eleva Vout na mesma proporção.'
        : 'Mantendo a razão R₁/R₂, reduzir Vin reduz Vout na mesma proporção.';
      return;
    }

    observation.textContent = 'R₂ recebe uma parcela da tensão proporcional à sua participação na resistência total.';
  }

  function render() {
    const next = compute();
    const ratioInsight = detectRatioInsight(next);
    setObservation(next, ratioInsight);
    Object.assign(state, next);

    vinLabel.textContent = `Vin = ${fmt(state.vin, 1)} V`;
    r1Label.textContent = `R₁ = ${formatResistance(state.r1)}`;
    r2Label.textContent = `R₂ = ${formatResistance(state.r2)}`;
    vr1Label.textContent = `VR₁ = ${fmt(state.vr1, 2)} V`;
    vr2Label.textContent = `VR₂ = ${fmt(state.vout, 2)} V`;
    voutSvg.textContent = `Vout = ${fmt(state.vout, 2)} V`;
    currentSvg.textContent = `I = ${formatCurrent(state.current)}`;
    voutResult.textContent = `${fmt(state.vout, 2)} V`;
    ratioResult.textContent = `R₂ representa ${fmt(state.ratio * 100, 1)}% da resistência total`;
    currentResult.textContent = formatCurrent(state.current);
    sumValues.textContent = `${fmt(state.vin, 2)} V = ${fmt(state.vr1, 2)} V + ${fmt(state.vout, 2)} V`;
    equationValues.textContent = `Vout = ${fmt(state.vin, 1)} × ${fmt(state.r2, 0)} / (${fmt(state.r1, 0)} + ${fmt(state.r2, 0)}) = ${fmt(state.vout, 2)} V`;

    if (!challengePanel.hidden) {
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
  }

  [vin, r1, r2].forEach((input) => {
    input.addEventListener('input', () => {
      lastChanged = input.id;
      render();
    });
    input.addEventListener('blur', () => {
      if (input === vin) input.value = String(clampInput(input, 0.1, 1000, state.vin));
      else input.value = String(clampInput(input, 1, 1e6, input === r1 ? state.r1 : state.r2));
      render();
    });
  });

  // Corrente convencional: a mesma intensidade percorre R1 e R2.
  const MAX_PARTICLES = 11;
  const particles = [];
  for (let i = 0; i < MAX_PARTICLES; i += 1) {
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('r', '4.6');
    dot.setAttribute('class', 'current-particle');
    particlesGroup.appendChild(dot);
    particles.push(dot);
  }
  const pathLength = currentPath.getTotalLength();
  let lastFrame = performance.now();
  let travel = 0;

  function animate(now) {
    const dt = Math.min(.05, (now - lastFrame) / 1000);
    lastFrame = now;
    const I = Math.abs(state.current);
    const intensity = I <= 0 ? 0 : I / (I + .008);
    const visible = I <= 1e-12 ? 0 : Math.max(2, Math.round(2 + intensity * (MAX_PARTICLES - 2)));
    const speed = 34 + intensity * 125;
    travel = (travel + speed * dt) % pathLength;

    particles.forEach((dot, index) => {
      if (index >= visible) {
        dot.style.opacity = '0';
        return;
      }
      const distance = (travel + index * (pathLength / visible)) % pathLength;
      const point = currentPath.getPointAtLength(distance);
      dot.setAttribute('cx', point.x.toFixed(2));
      dot.setAttribute('cy', point.y.toFixed(2));
      dot.style.opacity = String(.44 + intensity * .48);
    });
    requestAnimationFrame(animate);
  }

  function setChallengeLock(locked) {
    vin.disabled = locked;
    vinField.classList.toggle('locked', locked);
  }

  function applyChallenge(next) {
    activeChallenge = next;
    vin.value = String(next.vin);
    r1.value = String(next.r1);
    r2.value = String(next.r2);
    challengePrompt.textContent = next.text;
    setChallengeLock(true);
    lastChanged = null;
    render();
  }

  function pickChallenge() {
    const pool = challenges.filter((c) => !activeChallenge || c.text !== activeChallenge.text);
    applyChallenge(pool[Math.floor(Math.random() * pool.length)] || challenges[0]);
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) pickChallenge();
    else {
      setChallengeLock(false);
      activeChallenge = null;
      challengeResult.textContent = '';
    }
  });

  newChallenge.addEventListener('click', pickChallenge);

  checkChallenge.addEventListener('click', () => {
    if (!activeChallenge) return;
    const actual = state.vout;
    const target = activeChallenge.target;
    const tolerance = Math.max(.02, target * .005);
    if (Math.abs(actual - target) <= tolerance) {
      challengeResult.textContent = `Vout = ${fmt(actual, 2)} V ✓ Desafio concluído`;
      challengeResult.className = 'challenge-result success';
    } else {
      challengeResult.innerHTML = `Vout atual: <strong>${fmt(actual, 2)} V</strong>. Ajuste a relação entre R₁ e R₂.`;
      challengeResult.className = 'challenge-result';
    }
  });

  render();
  requestAnimationFrame(animate);
})();
