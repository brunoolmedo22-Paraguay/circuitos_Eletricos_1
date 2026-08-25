(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  // Tabela de quatro faixas organizada por função. Mantemos todas as regras
  // num único ponto para facilitar manutenção e futuros experimentos.
  const COLORS = {
    black:  { name: 'Preto',    css: '#1d1d1f', digit: 0, multiplier: 1 },
    brown:  { name: 'Marrom',   css: '#6f3b25', digit: 1, multiplier: 10, tolerance: 1 },
    red:    { name: 'Vermelho', css: '#c63838', digit: 2, multiplier: 100, tolerance: 2 },
    orange: { name: 'Laranja',  css: '#e68122', digit: 3, multiplier: 1e3 },
    yellow: { name: 'Amarelo',  css: '#e7c735', digit: 4, multiplier: 1e4 },
    green:  { name: 'Verde',    css: '#3c8a58', digit: 5, multiplier: 1e5, tolerance: 0.5 },
    blue:   { name: 'Azul',     css: '#326db2', digit: 6, multiplier: 1e6, tolerance: 0.25 },
    violet: { name: 'Violeta',  css: '#7d4aa1', digit: 7, multiplier: 1e7, tolerance: 0.1 },
    gray:   { name: 'Cinza',    css: '#929397', digit: 8, multiplier: 1e8, tolerance: 0.05 },
    white:  { name: 'Branco',   css: '#f4f3ef', digit: 9, multiplier: 1e9 },
    gold:   { name: 'Dourado',  css: '#c9a33b', multiplier: 0.1, tolerance: 5 },
    silver: { name: 'Prateado', css: '#b7b8ba', multiplier: 0.01, tolerance: 10 },
  };

  const DIGIT_KEYS = ['black','brown','red','orange','yellow','green','blue','violet','gray','white'];
  const MULTIPLIER_KEYS = [...DIGIT_KEYS, 'gold', 'silver'];
  const TOLERANCE_KEYS = ['brown','red','green','blue','violet','gray','gold','silver'];
  const BAND_FUNCTIONS = [
    { title: '1ª faixa', text: 'Primeiro algarismo significativo.' },
    { title: '2ª faixa', text: 'Segundo algarismo significativo.' },
    { title: 'Multiplicador', text: 'Multiplica os dois algarismos significativos.' },
    { title: 'Tolerância', text: 'Indica a variação esperada em torno do valor nominal.' },
  ];

  const PRESET_VALUES = [100, 220, 330, 470, 1000, 2200, 4700, 10000, 47000, 100000, 1000000];
  const PRESET_TOLERANCES = [1, 2, 5, 10];

  const state = {
    mode: 'colors',
    bands: ['brown', 'black', 'red', 'gold'],
    selectedBand: 0,
    inverseValue: 1000,
    inverseTolerance: 5,
  };

  let challenge = null;
  let savedBeforeChallenge = null;

  const modeBadge = $('modeBadge');
  const colorsMode = $('colorsMode');
  const valueMode = $('valueMode');
  const colorsControls = $('colorsControls');
  const valueControls = $('valueControls');
  const palette = $('palette');
  const selectedBandTitle = $('selectedBandTitle');
  const selectedBandFunction = $('selectedBandFunction');
  const selectedColorPreview = $('selectedColorPreview');
  const calculationText = $('calculationText');
  const compactResult = $('compactResult');
  const nominalValue = $('nominalValue');
  const toleranceValue = $('toleranceValue');
  const nominalOhms = $('nominalOhms');
  const expectedRange = $('expectedRange');
  const observation = $('observation');
  const resultPanel = $('resultPanel');
  const calculationCard = $('calculationCard');

  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');
  const readAnswerArea = $('readAnswerArea');
  const readAnswer = $('readAnswer');

  const bandEls = [0,1,2,3].map((i) => $(`band${i}`));
  const bandValueEls = [0,1,2,3].map((i) => $(`bandValue${i}`));
  const interpretItems = $$('.interpret-item');

  const fmtNumber = (value, maxDigits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDigits,
  });

  function formatOhms(value, compact = true) {
    const abs = Math.abs(value);
    if (!compact) return `${fmtNumber(value, abs < 10 ? 2 : 0)} Ω`;
    if (abs >= 1e9) return `${fmtNumber(value / 1e9, 2)} GΩ`;
    if (abs >= 1e6) return `${fmtNumber(value / 1e6, 2)} MΩ`;
    if (abs >= 1e3) return `${fmtNumber(value / 1e3, 2)} kΩ`;
    if (abs >= 1) return `${fmtNumber(value, abs < 10 ? 2 : 0)} Ω`;
    if (abs >= 1e-3) return `${fmtNumber(value * 1e3, 2)} mΩ`;
    return `${fmtNumber(value, 3)} Ω`;
  }

  function formatMultiplier(value) {
    if (value >= 1e9) return `×${fmtNumber(value / 1e9)}G`;
    if (value >= 1e6) return `×${fmtNumber(value / 1e6)}M`;
    if (value >= 1e3) return `×${fmtNumber(value / 1e3)}k`;
    return `×${fmtNumber(value, 2)}`;
  }

  function currentValues() {
    const d1 = COLORS[state.bands[0]].digit;
    const d2 = COLORS[state.bands[1]].digit;
    const multiplier = COLORS[state.bands[2]].multiplier;
    const tolerance = COLORS[state.bands[3]].tolerance;
    const nominal = (d1 * 10 + d2) * multiplier;
    return { d1, d2, multiplier, tolerance, nominal };
  }

  function allowedColorsForBand(index) {
    if (index === 0 || index === 1) return DIGIT_KEYS;
    if (index === 2) return MULTIPLIER_KEYS;
    return TOLERANCE_KEYS;
  }

  function setObservationForBand(index) {
    observation.textContent = BAND_FUNCTIONS[index].text;
  }

  function renderBands() {
    bandEls.forEach((el, i) => {
      const color = COLORS[state.bands[i]];
      el.setAttribute('fill', color.css);
      el.classList.toggle('selected', i === state.selectedBand && state.mode === 'colors' && !(challenge && challenge.type === 'read'));
      el.classList.toggle('locked', !!(challenge && challenge.type === 'read'));
      el.setAttribute('aria-label', `${BAND_FUNCTIONS[i].title}: ${color.name}`);
    });
  }

  function renderInterpretation() {
    const { d1, d2, multiplier, tolerance } = currentValues();
    bandValueEls[0].textContent = String(d1);
    bandValueEls[1].textContent = String(d2);
    bandValueEls[2].textContent = formatMultiplier(multiplier);
    bandValueEls[3].textContent = `±${fmtNumber(tolerance, 2)}%`;
    interpretItems.forEach((item, i) => item.classList.toggle('active', i === state.selectedBand && state.mode === 'colors'));
  }

  function renderResult() {
    const { d1, d2, multiplier, tolerance, nominal } = currentValues();
    const low = nominal * (1 - tolerance / 100);
    const high = nominal * (1 + tolerance / 100);
    const sig = d1 * 10 + d2;

    calculationText.textContent = `${sig} × ${fmtNumber(multiplier, 2)} = ${fmtNumber(nominal, nominal < 10 ? 2 : 0)} Ω`;
    compactResult.textContent = `${formatOhms(nominal)} ±${fmtNumber(tolerance, 2)}%`;
    nominalValue.textContent = formatOhms(nominal);
    toleranceValue.textContent = `Tolerância · ±${fmtNumber(tolerance, 2)}%`;
    nominalOhms.textContent = formatOhms(nominal, false);
    expectedRange.textContent = `${formatOhms(low)} — ${formatOhms(high)}`;
  }

  function renderSelectedBand() {
    const meta = BAND_FUNCTIONS[state.selectedBand];
    const color = COLORS[state.bands[state.selectedBand]];
    selectedBandTitle.textContent = meta.title;
    selectedBandFunction.textContent = meta.text;
    selectedColorPreview.style.background = color.css;
  }

  function renderPalette() {
    palette.replaceChildren();
    const keys = allowedColorsForBand(state.selectedBand);
    keys.forEach((key) => {
      const color = COLORS[key];
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `color-choice${state.bands[state.selectedBand] === key ? ' active' : ''}`;
      button.innerHTML = `<span class="color-dot" style="background:${color.css}"></span><span>${color.name}</span>`;
      button.setAttribute('aria-label', `${color.name} para ${BAND_FUNCTIONS[state.selectedBand].title}`);
      button.addEventListener('click', () => {
        if (challenge && challenge.type === 'read') return;
        state.bands[state.selectedBand] = key;
        renderAll();
        resetChallengeFeedback();
      });
      palette.appendChild(button);
    });
  }

  function bandsForValue(value, tolerance) {
    // Todos os presets escolhidos são representáveis exatamente com duas casas significativas.
    if (!(value > 0)) return null;
    let multiplier = 1;
    let sig = value;
    while (sig >= 100 && multiplier < 1e9) { sig /= 10; multiplier *= 10; }
    while (sig < 10 && multiplier > 0.01) { sig *= 10; multiplier /= 10; }
    sig = Math.round(sig);
    if (sig < 10 || sig > 99 || Math.abs(sig * multiplier - value) > Math.max(1e-8, value * 1e-9)) return null;
    const d1 = Math.floor(sig / 10);
    const d2 = sig % 10;
    const digit1 = DIGIT_KEYS.find((key) => COLORS[key].digit === d1);
    const digit2 = DIGIT_KEYS.find((key) => COLORS[key].digit === d2);
    const mult = MULTIPLIER_KEYS.find((key) => Math.abs(COLORS[key].multiplier - multiplier) < 1e-12);
    const tol = TOLERANCE_KEYS.find((key) => Math.abs(COLORS[key].tolerance - tolerance) < 1e-12);
    return digit1 && digit2 && mult && tol ? [digit1, digit2, mult, tol] : null;
  }

  function renderPresets() {
    const valuePresets = $('valuePresets');
    const tolerancePresets = $('tolerancePresets');
    valuePresets.replaceChildren();
    tolerancePresets.replaceChildren();

    PRESET_VALUES.forEach((value) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = `preset-button${state.inverseValue === value ? ' active' : ''}`;
      b.textContent = formatOhms(value);
      b.addEventListener('click', () => {
        state.inverseValue = value;
        const bands = bandsForValue(state.inverseValue, state.inverseTolerance);
        if (bands) state.bands = bands;
        renderAll();
      });
      valuePresets.appendChild(b);
    });

    PRESET_TOLERANCES.forEach((tol) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = `preset-button${state.inverseTolerance === tol ? ' active' : ''}`;
      b.textContent = `±${fmtNumber(tol)}%`;
      b.addEventListener('click', () => {
        state.inverseTolerance = tol;
        const bands = bandsForValue(state.inverseValue, state.inverseTolerance);
        if (bands) state.bands = bands;
        renderAll();
      });
      tolerancePresets.appendChild(b);
    });
  }

  function setMode(mode, { force = false } = {}) {
    if (challenge && !force) return;
    state.mode = mode;
    const isColors = mode === 'colors';
    colorsControls.hidden = !isColors;
    valueControls.hidden = isColors;
    colorsMode.classList.toggle('active', isColors);
    valueMode.classList.toggle('active', !isColors);
    colorsMode.setAttribute('aria-pressed', String(isColors));
    valueMode.setAttribute('aria-pressed', String(!isColors));
    modeBadge.textContent = isColors ? 'CORES → VALOR' : 'VALOR → CORES';
    observation.textContent = isColors
      ? BAND_FUNCTIONS[state.selectedBand].text
      : 'Escolha um valor nominal e veja as quatro faixas correspondentes serem montadas automaticamente.';
    renderAll();
  }

  function renderAll() {
    renderBands();
    renderInterpretation();
    renderResult();
    renderSelectedBand();
    if (state.mode === 'colors') renderPalette();
    else renderPresets();
  }

  bandEls.forEach((el, index) => {
    el.addEventListener('click', () => {
      if (state.mode !== 'colors' || (challenge && challenge.type === 'read')) return;
      state.selectedBand = index;
      setObservationForBand(index);
      renderAll();
    });
  });

  interpretItems.forEach((item, index) => {
    item.addEventListener('click', () => {
      if (state.mode !== 'colors' || (challenge && challenge.type === 'read')) return;
      state.selectedBand = index;
      setObservationForBand(index);
      renderAll();
    });
  });

  colorsMode.addEventListener('click', () => setMode('colors'));
  valueMode.addEventListener('click', () => setMode('value'));

  // ---------------------------------------------------------------------
  // Desafios: montar cores ou interpretar um resistor já configurado.
  // ---------------------------------------------------------------------
  const CHALLENGES = [
    { type: 'build', label: 'Monte um resistor de 4,7 kΩ ±5%.', targetBands: ['yellow','violet','red','gold'], value: 4700, tolerance: 5 },
    { type: 'build', label: 'Monte um resistor de 220 Ω ±5%.', targetBands: ['red','red','brown','gold'], value: 220, tolerance: 5 },
    { type: 'build', label: 'Monte um resistor de 10 kΩ ±10%.', targetBands: ['brown','black','orange','silver'], value: 10000, tolerance: 10 },
    { type: 'read', label: 'Qual é o valor nominal representado por este resistor?', bands: ['green','blue','red','gold'], answer: 5600 },
    { type: 'read', label: 'Qual é o valor nominal representado por este resistor?', bands: ['orange','orange','brown','gold'], answer: 330 },
    { type: 'read', label: 'Qual é o valor nominal representado por este resistor?', bands: ['brown','black','yellow','silver'], answer: 100000 },
  ];

  function resetChallengeFeedback() {
    if (!challengePanel.hidden) {
      challengeResult.textContent = '';
      challengeResult.className = 'challenge-result';
    }
  }

  function lockModeControls(locked) {
    colorsMode.disabled = locked;
    valueMode.disabled = locked;
  }

  function applyChallenge(next) {
    challenge = next;
    lockModeControls(true);
    challengePrompt.textContent = next.label;
    challengeResult.textContent = '';
    challengeResult.className = 'challenge-result';
    readAnswer.value = '';

    if (next.type === 'build') {
      setMode('colors', { force: true });
      readAnswerArea.hidden = true;
      resultPanel.classList.remove('concealed');
      calculationCard.classList.remove('concealed');
      observation.textContent = 'Selecione as quatro faixas até obter o valor e a tolerância pedidos.';
    } else {
      setMode('colors', { force: true });
      state.bands = next.bands.slice();
      state.selectedBand = 0;
      readAnswerArea.hidden = false;
      resultPanel.classList.add('concealed');
      calculationCard.classList.add('concealed');
      observation.textContent = 'Leia as faixas da esquerda para a direita e informe apenas o valor nominal em ohms.';
      renderAll();
    }
  }

  function pickChallenge() {
    const pool = CHALLENGES.filter((item) => item !== challenge);
    applyChallenge(pool[Math.floor(Math.random() * pool.length)] || CHALLENGES[0]);
  }

  function endChallenge() {
    challenge = null;
    lockModeControls(false);
    resultPanel.classList.remove('concealed');
    calculationCard.classList.remove('concealed');
    readAnswerArea.hidden = true;
    if (savedBeforeChallenge) {
      state.mode = savedBeforeChallenge.mode;
      state.bands = savedBeforeChallenge.bands.slice();
      state.selectedBand = savedBeforeChallenge.selectedBand;
      state.inverseValue = savedBeforeChallenge.inverseValue;
      state.inverseTolerance = savedBeforeChallenge.inverseTolerance;
      savedBeforeChallenge = null;
    }
    setMode(state.mode, { force: true });
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) {
      savedBeforeChallenge = { ...state, bands: state.bands.slice() };
      pickChallenge();
    } else {
      endChallenge();
    }
  });

  newChallenge.addEventListener('click', pickChallenge);

  checkChallenge.addEventListener('click', () => {
    if (!challenge) return;
    if (challenge.type === 'build') {
      const ok = challenge.targetBands.every((key, index) => state.bands[index] === key);
      if (ok) {
        challengeResult.textContent = `${formatOhms(challenge.value)} ±${fmtNumber(challenge.tolerance)}% ✓ Desafio concluído`;
        challengeResult.className = 'challenge-result success';
      } else {
        challengeResult.textContent = 'Ainda não. Revise os dois algarismos, o multiplicador e a tolerância.';
        challengeResult.className = 'challenge-result';
      }
    } else {
      const answer = Number(readAnswer.value);
      const ok = Number.isFinite(answer) && Math.abs(answer - challenge.answer) <= Math.max(1e-9, challenge.answer * 0.0001);
      if (ok) {
        challengeResult.textContent = `${formatOhms(challenge.answer)} ✓ Leitura correta`;
        challengeResult.className = 'challenge-result success';
        resultPanel.classList.remove('concealed');
        calculationCard.classList.remove('concealed');
      } else {
        challengeResult.textContent = 'Ainda não. Revise os dois primeiros algarismos e o multiplicador.';
        challengeResult.className = 'challenge-result';
      }
    }
  });

  setMode('colors', { force: true });
})();
