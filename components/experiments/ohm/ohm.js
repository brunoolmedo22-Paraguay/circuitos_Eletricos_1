(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);

  const voltage = $('voltage');
  const resistance = $('resistance');
  const voltageOut = $('voltageOut');
  const resistanceOut = $('resistanceOut');
  const currentOut = $('currentOut');
  const powerOut = $('powerOut');
  const svgCurrent = $('svgCurrent');
  const sourceLabel = $('sourceLabel');
  const resistorLabel = $('resistorLabel');
  const equationValues = $('equationValues');
  const observation = $('observation');
  const resistorBody = $('resistorBody');
  const heatBlur = $('heatBlur');
  const heatFlood = $('heatFlood');
  const currentPath = $('currentPath');
  const particlesGroup = $('particles');

  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const targetCurrent = $('targetCurrent');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');

  const challengeTargets = [0.5, 1, 1.5, 2.5, 3, 4, 5, 6, 7.5, 10];
  let activeTarget = 2.5;
  let lastVoltage = Number(voltage.value);
  let lastResistance = Number(resistance.value);
  let currentState = { voltage: 10, resistance: 5, current: 2, power: 20 };

  const fmt = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  function setRangeProgress(input) {
    const min = Number(input.min);
    const max = Number(input.max);
    const value = Number(input.value);
    const pct = ((value - min) / (max - min)) * 100;
    input.style.setProperty('--pct', `${pct}%`);
  }

  function updateObservation(source, oldValue, newValue) {
    if (source === 'voltage') {
      observation.textContent = newValue > oldValue
        ? 'Com a resistência constante, aumentar a tensão aumenta a corrente.'
        : 'Com a resistência constante, reduzir a tensão reduz a corrente.';
    } else if (source === 'resistance') {
      observation.textContent = newValue > oldValue
        ? 'Com a tensão constante, aumentar a resistência reduz a corrente.'
        : 'Com a tensão constante, reduzir a resistência aumenta a corrente.';
    }
  }

  function updateHeat(power) {
    // Compressão logarítmica para que o efeito permaneça discreto mesmo em P alto.
    const normalized = Math.min(1, Math.log10(power + 1) / Math.log10(901));
    heatBlur.setAttribute('stdDeviation', (normalized * 8).toFixed(2));
    heatFlood.setAttribute('flood-opacity', (normalized * 0.46).toFixed(3));

    // Aquece visualmente do grafite para um vermelho quente.
    const r = Math.round(50 + normalized * 175);
    const g = Math.round(43 + normalized * 28);
    const b = Math.round(53 - normalized * 28);
    const glowR = Math.round(180 + normalized * 55);
    const glowG = Math.round(92 - normalized * 18);
    const glowB = Math.round(92 - normalized * 38);

    resistorBody.style.stroke = `rgb(${r}, ${g}, ${b})`;
    heatFlood.setAttribute('flood-color', `rgb(${glowR}, ${glowG}, ${glowB})`);
  }

  function update(source = null) {
    const V = Number(voltage.value);
    const R = Math.max(1, Number(resistance.value));
    const I = V / R;
    const P = V * I;

    if (source === 'voltage') updateObservation(source, lastVoltage, V);
    if (source === 'resistance') updateObservation(source, lastResistance, R);

    lastVoltage = V;
    lastResistance = R;
    currentState = { voltage: V, resistance: R, current: I, power: P };

    voltageOut.textContent = `${fmt(V, 1)} V`;
    resistanceOut.textContent = `${fmt(R, 0)} Ω`;
    currentOut.textContent = `${fmt(I, 2)} A`;
    powerOut.textContent = `${fmt(P, 1)} W`;
    svgCurrent.textContent = `I = ${fmt(I, 2)} A`;
    sourceLabel.textContent = `V = ${fmt(V, 1)} V`;
    resistorLabel.textContent = `R = ${fmt(R, 0)} Ω`;
    equationValues.textContent = `I = ${fmt(V, 1)} / ${fmt(R, 0)} = ${fmt(I, 2)} A`;

    setRangeProgress(voltage);
    setRangeProgress(resistance);
    updateHeat(P);

    if (!challengePanel.hidden) {
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
  }

  voltage.addEventListener('input', () => update('voltage'));
  resistance.addEventListener('input', () => update('resistance'));

  // -----------------------------------------------------------------------
  // Corrente convencional animada sobre o caminho SVG.
  // -----------------------------------------------------------------------
  const MAX_PARTICLES = 12;
  const particles = [];
  for (let i = 0; i < MAX_PARTICLES; i += 1) {
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('r', '5');
    dot.setAttribute('class', 'current-particle');
    particlesGroup.appendChild(dot);
    particles.push(dot);
  }

  const pathLength = currentPath.getTotalLength();
  let lastFrame = performance.now();
  let travel = 0;

  function animate(now) {
    const dt = Math.min(0.05, (now - lastFrame) / 1000);
    lastFrame = now;

    const I = currentState.current;
    if (I <= 0.0001) {
      particles.forEach((dot) => { dot.style.opacity = '0'; });
      requestAnimationFrame(animate);
      return;
    }

    // Escala didática: satura suavemente para não criar velocidades absurdas.
    const intensity = I / (I + 4.5);
    const visible = Math.max(2, Math.round(2 + intensity * (MAX_PARTICLES - 2)));
    const speed = 45 + intensity * 165; // unidades SVG por segundo
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

  // -----------------------------------------------------------------------
  // Desafio simples, sem pontuação ou gamificação excessiva.
  // -----------------------------------------------------------------------
  function pickTarget() {
    const available = challengeTargets.filter((x) => Math.abs(x - currentState.current) > 0.12 && x !== activeTarget);
    const pool = available.length ? available : challengeTargets;
    activeTarget = pool[Math.floor(Math.random() * pool.length)];
    targetCurrent.textContent = `${fmt(activeTarget, 2)} A`;
    challengeResult.textContent = '';
    challengeResult.className = 'challenge-result';
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) pickTarget();
  });

  newChallenge.addEventListener('click', pickTarget);

  checkChallenge.addEventListener('click', () => {
    const actual = currentState.current;
    const tolerance = Math.max(0.03, activeTarget * 0.01);
    const error = Math.abs(actual - activeTarget);

    if (error <= tolerance) {
      challengeResult.textContent = `${fmt(actual, 2)} A ✓ Desafio concluído`;
      challengeResult.className = 'challenge-result success';
    } else {
      challengeResult.innerHTML = `Ainda não. Corrente atual: <strong>${fmt(actual, 2)} A</strong><br>Observe o que acontece com I quando V aumenta ou R diminui.`;
      challengeResult.className = 'challenge-result';
    }
  });

  update();
  requestAnimationFrame(animate);
})();
