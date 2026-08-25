(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const $ = (id) => document.getElementById(id);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const fmt = (v, d=2) => Number(v).toLocaleString('pt-BR', {minimumFractionDigits:d, maximumFractionDigits:d});
  const formatCurrent = (a) => Math.abs(a) < 1 ? `${fmt(a*1000,2)} mA` : `${fmt(a,3)} A`;
  const formatEnergy = (j) => j < 1 ? `${fmt(j*1000,2)} mJ` : `${fmt(j,3)} J`;

  const voltage = $('voltage');
  const resistance = $('resistance');
  const inductance = $('inductance');
  const tauPill = $('tauPill');
  const tauResult = $('tauResult');
  const tauFormula = $('tauFormula');
  const finalCurrentResult = $('finalCurrentResult');
  const finalCurrentFormula = $('finalCurrentFormula');
  const sourceLabel = $('sourceLabel');
  const resistorLabel = $('resistorLabel');
  const inductorLabel = $('inductorLabel');
  const currentSvg = $('currentSvg');
  const currentPercentSvg = $('currentPercentSvg');
  const voltageSvg = $('voltageSvg');
  const energySvg = $('energySvg');
  const phaseBadge = $('phaseBadge');
  const switchStateLabel = $('switchStateLabel');
  const switchLever = $('switchLever');
  const switchHit = $('switchHit');
  const storeMode = $('storeMode');
  const decayMode = $('decayMode');
  const storeButton = $('storeButton');
  const decayButton = $('decayButton');
  const pauseButton = $('pauseButton');
  const resetButton = $('resetButton');
  const observation = $('observation');
  const fieldGroup = $('fieldGroup');
  const inductorCoil = $('inductorCoil');
  const inductorPlus = $('inductorPlus');
  const inductorMinus = $('inductorMinus');
  const particlesGroup = $('particles');
  const storagePath = $('storagePath');
  const decayPath = $('decayPath');
  const graphGrid = $('graphGrid');
  const graphCurve = $('graphCurve');
  const graphPoint = $('graphPoint');
  const graphAnnotations = $('graphAnnotations');
  const graphTitle = $('graphTitle');
  const graphValue = $('graphValue');
  const graphUnitText = $('graphUnitText');
  const graphTau = $('graphTau');
  const timeLabel = $('timeLabel');
  const equationTitle = $('equationTitle');
  const equationSymbolic = $('equationSymbolic');
  const equationNumeric = $('equationNumeric');
  const predictionPrompt = $('predictionPrompt');
  const predictionOptions = $('predictionOptions');
  const predictionResult = $('predictionResult');
  const newPrediction = $('newPrediction');
  const compareToggle = $('compareToggle');
  const comparePanel = $('comparePanel');
  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeNote = $('challengeNote');
  const challengeResult = $('challengeResult');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');

  const state = {
    V: 10,
    R: 10,
    L: 10,
    tau: 1,
    finalI: 1,
    i: 0,
    vL: 10,
    vR: 0,
    energy: 0,
    mode: 'storage',
    running: false,
    speed: 1,
    simTime: 0,
    phaseTime: 0,
    startI: 0,
    targetI: 1,
    graphMode: 'current',
    graphPoints: [],
    lastGridLeft: Number.NaN,
    lastParam: null,
    paramMessageUntil: 0,
    previousTau: 1,
    previousFinalI: 1,
    activeChallenge: null,
    predictionIndex: 0,
  };

  function readParameters() {
    state.V = clamp(Number(voltage.value) || .1, .1, 1000);
    state.R = clamp(Number(resistance.value) || .1, .1, 10000);
    state.L = clamp(Number(inductance.value) || .001, .001, 10000);
    state.tau = state.L / state.R;
    state.finalI = state.V / state.R;
  }

  function currentAtPhase() {
    const e = Math.exp(-state.phaseTime / Math.max(state.tau, 1e-12));
    return state.targetI + (state.startI - state.targetI) * e;
  }

  function updateElectricalValues() {
    state.i = Math.max(0, currentAtPhase());
    state.vR = state.i * state.R;
    state.vL = state.mode === 'storage' ? state.V - state.vR : -state.vR;
    state.energy = .5 * state.L * state.i * state.i;
  }

  function recordPoint() {
    state.graphPoints.push({t: state.simTime, i: state.i, vL: state.vL});
    if (state.graphPoints.length > 14000) state.graphPoints.splice(0, 2500);
  }

  function beginSegment(mode, {start=true} = {}) {
    updateElectricalValues();
    const preserved = state.i;
    if (state.simTime > 0 || state.graphPoints.length) recordPoint();
    state.mode = mode;
    state.startI = preserved;
    state.targetI = mode === 'storage' ? state.finalI : 0;
    state.phaseTime = 0;
    updateElectricalValues();
    // Mesmo instante, mesma corrente. Em vL pode existir a mudança de polaridade esperada.
    recordPoint();
    if (start) state.running = true;
    renderStatic();
  }

  function pause() {
    updateElectricalValues();
    state.startI = state.i;
    state.phaseTime = 0;
    state.running = false;
    renderStatic();
  }

  function reset() {
    readParameters();
    state.i = 0;
    state.vL = state.V;
    state.vR = 0;
    state.energy = 0;
    state.mode = 'storage';
    state.running = false;
    state.simTime = 0;
    state.phaseTime = 0;
    state.startI = 0;
    state.targetI = state.finalI;
    state.graphPoints = [];
    state.lastGridLeft = Number.NaN;
    state.lastParam = null;
    renderStatic();
  }

  function updateDynamics(dt) {
    if (state.running) {
      state.simTime += dt;
      state.phaseTime += dt;
      updateElectricalValues();
      const last = state.graphPoints[state.graphPoints.length - 1];
      if (!last || state.simTime - last.t >= Math.max(.012, state.tau / 180)) recordPoint();
    }
  }

  function renderSwitch() {
    if (state.mode === 'storage') {
      switchLever.setAttribute('x2', '210');
      switchLever.setAttribute('y2', '110');
      switchStateLabel.textContent = state.running ? 'fonte conectada' : 'armazenamento selecionado';
      inductorPlus.textContent = '+';
      inductorMinus.textContent = '−';
    } else {
      switchLever.setAttribute('x2', '210');
      switchLever.setAttribute('y2', '165');
      switchStateLabel.textContent = state.running ? 'caminho R–L fechado' : 'decaimento selecionado';
      inductorPlus.textContent = '−';
      inductorMinus.textContent = '+';
    }
  }

  function renderField() {
    const reference = Math.max(state.finalI, state.startI, .0001);
    const intensity = clamp(Math.abs(state.i) / reference, 0, 1);
    [...fieldGroup.querySelectorAll('.field-line')].forEach((line, idx) => {
      const threshold = idx * .08;
      line.style.opacity = String(clamp((intensity - threshold) * 1.25, 0, .72));
      line.style.strokeWidth = String(1.8 + intensity * (idx % 2 ? 1.2 : .7));
    });
    inductorCoil.style.stroke = intensity > .7 ? '#532458' : '#2e2931';
  }

  function renderEquation() {
    const local = state.phaseTime;
    const exp = Math.exp(-local / Math.max(state.tau, 1e-12));
    if (state.mode === 'storage') {
      equationTitle.textContent = 'ARMAZENAMENTO';
      if (Math.abs(state.startI) < 1e-7) {
        equationSymbolic.innerHTML = 'iL(t) = Im(1 − e<sup>−t/τ</sup>)';
        equationNumeric.textContent = `iL(${fmt(local,2)} s) = ${fmt(state.finalI,3)}(1 − e^−${fmt(local/state.tau,2)}) = ${fmt(state.i,3)} A`;
      } else {
        equationSymbolic.innerHTML = 'iL(t) = If + (Ii − If)e<sup>−t/τ</sup>';
        equationNumeric.textContent = `iL = ${fmt(state.finalI,3)} + (${fmt(state.startI,3)} − ${fmt(state.finalI,3)})·${fmt(exp,3)} = ${fmt(state.i,3)} A`;
      }
    } else {
      equationTitle.textContent = 'DECAIMENTO';
      equationSymbolic.innerHTML = 'iL(t) = I₀e<sup>−t/τ</sup>';
      equationNumeric.textContent = `iL(${fmt(local,2)} s) = ${fmt(state.startI,3)}·e^−${fmt(local/state.tau,2)} = ${fmt(state.i,3)} A`;
    }
  }

  function setObservation() {
    observation.classList.remove('special');
    if (state.lastParam && performance.now() < state.paramMessageUntil) {
      if (state.lastParam === 'L') {
        observation.textContent = state.tau > state.previousTau
          ? 'L aumentou → τ aumentou → a corrente leva mais tempo para se estabelecer, sem alterar V/R.'
          : 'L diminuiu → τ diminuiu → o transitório ficou mais rápido, sem alterar V/R.';
      } else if (state.lastParam === 'R') {
        observation.textContent = state.tau < state.previousTau
          ? 'R maior reduz τ = L/R e também reduz a corrente final Im = V/R.'
          : 'R menor aumenta τ = L/R e também aumenta a corrente final Im = V/R.';
      } else {
        observation.textContent = 'A tensão alterou a corrente final V/R, mas não modificou τ = L/R.';
      }
      return;
    }
    if (state.lastParam && performance.now() >= state.paramMessageUntil) state.lastParam = null;
    if (!state.running && state.simTime === 0) {
      observation.textContent = 'Inicie o armazenamento. A corrente começa em zero e cresce sem saltos em direção a V/R.';
      return;
    }
    if (!state.running) {
      observation.textContent = `Pausado em iL = ${formatCurrent(state.i)}. Ao continuar, a nova exponencial partirá exatamente deste valor.`;
      return;
    }
    if (state.mode === 'storage') {
      const ratio = state.finalI > 0 ? state.i / state.finalI : 0;
      if (Math.abs(state.phaseTime - state.tau) < state.tau * .06) {
        observation.classList.add('special');
        observation.textContent = 'Em 1τ, iL está próxima de 63,2% de Im. Ao mesmo tempo, vL caiu para cerca de 36,8% de V.';
      } else if (ratio > .99) {
        observation.textContent = 'Regime praticamente estabelecido: iL ≈ V/R, vL ≈ 0 e o campo magnético está no nível máximo desta condição.';
      } else {
        observation.textContent = 'A corrente cresce progressivamente enquanto vL diminui; o campo magnético acompanha iL.';
      }
    } else {
      if (state.i < Math.max(state.startI * .01, 1e-7)) {
        observation.textContent = 'O campo magnético praticamente colapsou e a corrente tende a zero.';
      } else {
        observation.textContent = 'A fonte foi removida, mas iL não saltou para zero: o campo magnético colapsa e mantém temporariamente a corrente no mesmo sentido.';
      }
    }
  }

  function renderStatic() {
    tauPill.textContent = `${fmt(state.tau,2)} s`;
    tauResult.textContent = `τ = ${fmt(state.tau,2)} s`;
    tauFormula.textContent = `${fmt(state.L,3)} H / ${fmt(state.R,2)} Ω`;
    finalCurrentResult.textContent = `Im = ${formatCurrent(state.finalI)}`;
    finalCurrentFormula.textContent = `${fmt(state.V,2)} V / ${fmt(state.R,2)} Ω`;
    sourceLabel.textContent = `${fmt(state.V,1)} V`;
    resistorLabel.textContent = `R = ${fmt(state.R,2)} Ω`;
    inductorLabel.textContent = `L = ${fmt(state.L,3)} H`;
    storeMode.classList.toggle('active', state.mode === 'storage');
    decayMode.classList.toggle('active', state.mode === 'decay');
    storeButton.classList.toggle('active', state.mode === 'storage' && state.running);
    decayButton.classList.toggle('active', state.mode === 'decay' && state.running);
    pauseButton.classList.toggle('active', !state.running && state.simTime > 0);
    renderSwitch();
    drawGraphGrid();
    renderDynamic();
  }

  function renderDynamic() {
    const ratio = state.finalI > 0 ? clamp(state.i / state.finalI, 0, 9.99) : 0;
    currentSvg.textContent = `iL = ${formatCurrent(state.i)}`;
    currentPercentSvg.textContent = state.mode === 'storage' ? `${fmt(ratio*100,1)}% de Im` : 'corrente preservada no decaimento';
    voltageSvg.textContent = `vL = ${fmt(state.vL,2)} V`;
    energySvg.textContent = `WL = ${formatEnergy(state.energy)}`;
    timeLabel.textContent = `t = ${fmt(state.simTime,2)} s`;
    graphTau.textContent = `${fmt(state.simTime / Math.max(state.tau,1e-12),2)} τ`;
    graphValue.textContent = state.graphMode === 'current' ? formatCurrent(state.i) : `${fmt(state.vL,2)} V`;
    graphUnitText.textContent = state.graphMode === 'current' ? 'iL' : 'vL';
    phaseBadge.textContent = !state.running
      ? (state.simTime === 0 ? 'pronto para armazenar' : 'pausado')
      : (state.mode === 'storage' ? 'campo sendo estabelecido' : 'campo em colapso');
    renderField();
    renderEquation();
    setObservation();
    const w = graphWindow();
    const gridStep = Math.max(state.tau / 50, .002);
    if (!Number.isFinite(state.lastGridLeft) || Math.abs(w.left - state.lastGridLeft) >= gridStep) drawGraphGrid();
    drawGraphCurve();
  }

  const graphBox = { left: 62, right: 650, top: 28, bottom: 278 };

  function graphWindow() {
    const span = Math.max(5 * state.tau, 1e-9);
    const right = Math.max(span, state.simTime);
    const left = Math.max(0, right - span);
    return {left, right, span};
  }

  function visiblePoints() {
    const w = graphWindow();
    let usable = state.graphPoints.filter(p => p.t >= w.left - 1e-9 && p.t <= w.right + 1e-9);
    const first = state.graphPoints.findIndex(p => p.t >= w.left);
    if (first > 0) usable = [state.graphPoints[first - 1], ...usable];
    return usable;
  }

  function graphRange() {
    const pts = visiblePoints();
    if (state.graphMode === 'current') {
      const maxHistory = pts.reduce((m,p) => Math.max(m, p.i), 0);
      const ymax = Math.max(state.finalI, state.startI, state.i, maxHistory, .001) * 1.08;
      return {min: 0, max: ymax};
    }
    const vals = pts.map(p => p.vL).concat([state.vL, state.V, -Math.abs(state.startI*state.R)]);
    const maxAbs = Math.max(.1, ...vals.map(v => Math.abs(v))) * 1.08;
    return {min: -maxAbs, max: maxAbs};
  }

  function xFor(t) {
    const w = graphWindow();
    return graphBox.left + ((t - w.left) / w.span) * (graphBox.right - graphBox.left);
  }
  function yFor(v) {
    const r = graphRange();
    const frac = (v - r.min) / Math.max(r.max - r.min, 1e-12);
    return graphBox.bottom - clamp(frac, 0, 1) * (graphBox.bottom - graphBox.top);
  }

  function svgEl(tag, attrs={}, text='') {
    const el = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, String(v)));
    if (text) el.textContent = text;
    return el;
  }

  function drawGraphGrid() {
    graphGrid.innerHTML = '';
    graphAnnotations.innerHTML = '';
    const w = graphWindow();
    const r = graphRange();
    state.lastGridLeft = w.left;

    graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:graphBox.bottom,x2:graphBox.right,y2:graphBox.bottom,class:'graph-axis'}));
    graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:graphBox.top,x2:graphBox.left,y2:graphBox.bottom,class:'graph-axis'}));

    [0,.25,.5,.75,1].forEach((f) => {
      const y = graphBox.bottom - f*(graphBox.bottom-graphBox.top);
      const val = r.min + f*(r.max-r.min);
      graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:y,x2:graphBox.right,y2:y,class:'graph-gridline'}));
      graphGrid.appendChild(svgEl('text',{x:graphBox.left-10,y:y+3,'text-anchor':'end',class:'graph-tick'}, state.graphMode === 'current' ? fmt(val,2) : fmt(val,1)));
    });
    if (state.graphMode === 'voltage' && r.min < 0 && r.max > 0) {
      const yz = yFor(0);
      graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:yz,x2:graphBox.right,y2:yz,class:'graph-zero'}));
    }

    for (let k=0;k<=5;k+=1) {
      const t = w.left + k*state.tau;
      const x = graphBox.left + (k/5)*(graphBox.right-graphBox.left);
      if (k > 0) graphGrid.appendChild(svgEl('line',{x1:x,y1:graphBox.top,x2:x,y2:graphBox.bottom,class:'tau-line'}));
      const pos = t / Math.max(state.tau,1e-12);
      const label = Math.abs(pos-Math.round(pos)) < .025 ? `${Math.round(pos)}τ` : `${fmt(pos,1)}τ`;
      graphGrid.appendChild(svgEl('text',{x,y:graphBox.bottom+20,'text-anchor':'middle',class:'tau-label'},label));
    }

    graphGrid.appendChild(svgEl('text',{x:(graphBox.left+graphBox.right)/2,y:318,'text-anchor':'middle',class:'graph-axis-label'},'tempo · janela móvel de 5τ'));
    const yLabelText = state.graphMode === 'current' ? 'iL (A)' : 'vL (V)';
    graphGrid.appendChild(svgEl('text',{x:17,y:(graphBox.top+graphBox.bottom)/2,'text-anchor':'middle',class:'graph-axis-label',transform:`rotate(-90 17 ${(graphBox.top+graphBox.bottom)/2})`},yLabelText));

    // Marca 63,2% apenas quando uma fase de armazenamento parte praticamente de zero.
    const phaseStart = state.simTime - state.phaseTime;
    const oneTau = phaseStart + state.tau;
    if (state.graphMode === 'current' && state.mode === 'storage' && state.startI < state.finalI*.02 && oneTau >= w.left && oneTau <= w.right) {
      const x = xFor(oneTau);
      const y = yFor(state.finalI*(1-Math.exp(-1)));
      graphAnnotations.appendChild(svgEl('text',{x:x+8,y:y-10,class:'graph-note'},'≈ 63,2% de Im em 1τ'));
    }
  }

  function drawGraphCurve() {
    if (!state.graphPoints.length) {
      graphCurve.setAttribute('d','');
      graphPoint.setAttribute('opacity','0');
      return;
    }
    const usable = visiblePoints();
    if (!usable.length) {
      graphCurve.setAttribute('d','');
      graphPoint.setAttribute('opacity','0');
      return;
    }
    const key = state.graphMode === 'current' ? 'i' : 'vL';
    const d = usable.map((p,idx) => `${idx?'L':'M'} ${xFor(p.t).toFixed(2)} ${yFor(p[key]).toFixed(2)}`).join(' ');
    graphCurve.setAttribute('d', d);
    const last = state.graphPoints[state.graphPoints.length-1];
    const w = graphWindow();
    if (last && last.t >= w.left-1e-9 && last.t <= w.right+1e-9) {
      graphPoint.setAttribute('cx',xFor(last.t));
      graphPoint.setAttribute('cy',yFor(last[key]));
      graphPoint.setAttribute('opacity','1');
    } else graphPoint.setAttribute('opacity','0');
  }

  const MAX_PARTICLES = 18;
  const particles = [];
  for (let n=0;n<MAX_PARTICLES;n+=1) {
    const dot = svgEl('circle',{r:4.1,class:'current-particle'});
    particlesGroup.appendChild(dot);
    particles.push(dot);
  }
  const pathLengths = { storage: storagePath.getTotalLength(), decay: decayPath.getTotalLength() };
  let travelStorage = 0, travelDecay = 0;

  function animateParticles(dt) {
    const reference = Math.max(state.finalI, state.startI, .0001);
    const intensity = clamp(Math.abs(state.i)/reference,0,1);
    const visible = (!state.running || intensity < .004) ? 0 : Math.max(1,Math.round(1+intensity*(MAX_PARTICLES-1)));
    const speed = 36 + intensity*135;
    const path = state.mode === 'storage' ? storagePath : decayPath;
    const length = state.mode === 'storage' ? pathLengths.storage : pathLengths.decay;
    if (state.mode === 'storage') travelStorage = (travelStorage + speed*dt) % length;
    else travelDecay = (travelDecay + speed*dt) % length;
    const travel = state.mode === 'storage' ? travelStorage : travelDecay;
    particles.forEach((dot,index) => {
      if (index >= visible) { dot.style.opacity='0'; return; }
      const dist = (travel + index*(length/visible)) % length;
      const pt = path.getPointAtLength(dist);
      dot.setAttribute('cx',pt.x.toFixed(2));
      dot.setAttribute('cy',pt.y.toFixed(2));
      dot.style.opacity = String(.30 + intensity*.62);
    });
  }

  function handleParameterChange(kind) {
    updateElectricalValues();
    const preservedI = state.i;
    const oldTau = state.tau;
    const oldFinal = state.finalI;
    if (state.simTime > 0 || state.graphPoints.length) recordPoint();
    readParameters();
    state.previousTau = oldTau;
    state.previousFinalI = oldFinal;
    state.lastParam = kind;
    state.paramMessageUntil = performance.now() + 2200;
    state.startI = preservedI;
    state.targetI = state.mode === 'storage' ? state.finalI : 0;
    state.phaseTime = 0;
    updateElectricalValues();
    recordPoint();
    // Não zera simTime nem histórico: a corrente do indutor é contínua.
    state.lastGridLeft = Number.NaN;
    renderStatic();
  }

  voltage.addEventListener('input', () => handleParameterChange('V'));
  resistance.addEventListener('input', () => handleParameterChange('R'));
  inductance.addEventListener('input', () => handleParameterChange('L'));

  storeMode.addEventListener('click', () => beginSegment('storage',{start:false}));
  decayMode.addEventListener('click', () => beginSegment('decay',{start:false}));
  storeButton.addEventListener('click', () => beginSegment('storage',{start:true}));
  decayButton.addEventListener('click', () => beginSegment('decay',{start:true}));
  pauseButton.addEventListener('click', pause);
  resetButton.addEventListener('click', reset);
  switchHit.addEventListener('click', () => beginSegment(state.mode === 'storage' ? 'decay' : 'storage',{start:true}));
  switchHit.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      beginSegment(state.mode === 'storage' ? 'decay' : 'storage',{start:true});
    }
  });

  document.querySelectorAll('.speed-button').forEach(btn => btn.addEventListener('click', () => {
    state.speed = Number(btn.dataset.speed);
    document.querySelectorAll('.speed-button').forEach(b => b.classList.toggle('active', b === btn));
  }));

  document.querySelectorAll('.graph-mode').forEach(btn => btn.addEventListener('click', () => {
    state.graphMode = btn.dataset.graph;
    document.querySelectorAll('.graph-mode').forEach(b => b.classList.toggle('active', b === btn));
    graphTitle.textContent = state.graphMode === 'current' ? 'CORRENTE NO INDUTOR' : 'TENSÃO NO INDUTOR';
    state.lastGridLeft = Number.NaN;
    drawGraphGrid();
    drawGraphCurve();
  }));

  compareToggle.addEventListener('click', () => {
    comparePanel.hidden = !comparePanel.hidden;
    compareToggle.textContent = comparePanel.hidden ? 'Comparar com RC' : 'Ocultar comparação';
  });

  const predictions = [
    {
      prompt:'Se L aumentar mantendo R constante, a corrente chegará ao valor final:',
      options:[['Mais rápido','fast'],['Mais devagar','slow'],['No mesmo tempo','same']],
      correct:'slow',
      success:'Correto. Aumentar L aumenta τ = L/R; a resposta fica mais lenta.',
      fail:'Não. Com R constante, L maior aumenta τ e alonga o transitório.'
    },
    {
      prompt:'Se R aumentar mantendo L constante, τ:',
      options:[['Aumenta','up'],['Diminui','down'],['Não muda','same']],
      correct:'down',
      success:'Correto. Como τ = L/R, aumentar R reduz a constante de tempo.',
      fail:'Observe a razão L/R: R está no denominador.'
    },
    {
      prompt:'Se V dobrar mantendo R e L, τ:',
      options:[['Dobra','up'],['Cai à metade','down'],['Não muda','same']],
      correct:'same',
      success:'Correto. V altera Im = V/R, mas τ depende apenas de L/R.',
      fail:'τ = L/R não contém V. A tensão muda a amplitude, não a constante de tempo.'
    },
  ];

  function renderPrediction(index) {
    state.predictionIndex = index % predictions.length;
    const p = predictions[state.predictionIndex];
    predictionPrompt.textContent = p.prompt;
    predictionOptions.innerHTML = '';
    predictionResult.textContent = '';
    p.options.forEach(([label,value]) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = label;
      btn.dataset.value = value;
      btn.addEventListener('click', () => {
        [...predictionOptions.querySelectorAll('button')].forEach(b => b.classList.remove('correct','wrong'));
        if (value === p.correct) {
          btn.classList.add('correct');
          predictionResult.textContent = p.success;
        } else {
          btn.classList.add('wrong');
          predictionResult.textContent = p.fail;
        }
      });
      predictionOptions.appendChild(btn);
    });
  }
  newPrediction.addEventListener('click', () => renderPrediction((state.predictionIndex+1)%predictions.length));

  const challenges = [
    {type:'tau', targetTau:2, text:'Faça a constante de tempo ser exatamente 2 s.', note:'Altere R e L. Qualquer combinação válida com L/R = 2 s é aceita.'},
    {type:'combo', targetTau:1, targetI:2, text:'Configure o circuito para ter corrente final de 2 A e τ = 1 s.', note:'Relacione Im = V/R e τ = L/R.'},
    {type:'slower2', baseV:10, baseR:10, baseL:10, text:'Faça o transitório ficar duas vezes mais lento sem alterar R.', note:'R permanece em 10 Ω. A constante de tempo deve passar de 1 s para 2 s.'},
    {type:'halfTau', baseV:10, baseR:10, baseL:10, text:'Reduza τ pela metade sem alterar L.', note:'L permanece em 10 H. Altere R até τ = 0,5 s.'},
    {type:'doubleI', baseV:10, baseR:10, baseL:10, text:'Dobre a corrente final sem alterar R e L.', note:'R = 10 Ω e L = 10 H ficam fixos. Altere apenas V.'},
  ];

  function unlockFields() {
    voltage.disabled = false;
    resistance.disabled = false;
    inductance.disabled = false;
  }
  function setFieldValues(V,R,L) {
    voltage.value = String(V);
    resistance.value = String(R);
    inductance.value = String(L);
    reset();
  }
  function applyChallenge(ch) {
    state.activeChallenge = ch;
    unlockFields();
    challengePrompt.textContent = ch.text;
    challengeNote.textContent = ch.note;
    challengeResult.textContent = '';
    challengeResult.className = 'challenge-result';
    if (['slower2','halfTau','doubleI'].includes(ch.type)) {
      setFieldValues(ch.baseV,ch.baseR,ch.baseL);
      if (ch.type === 'slower2') { resistance.disabled = true; voltage.disabled = true; }
      if (ch.type === 'halfTau') { inductance.disabled = true; voltage.disabled = true; }
      if (ch.type === 'doubleI') { resistance.disabled = true; inductance.disabled = true; }
    }
  }
  function pickChallenge() {
    const pool = challenges.filter(c => c !== state.activeChallenge);
    applyChallenge(pool[Math.floor(Math.random()*pool.length)] || challenges[0]);
  }

  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden = !opening;
    challengeToggle.textContent = opening ? 'Ocultar desafio' : '🎯 Desafio';
    if (opening) pickChallenge();
    else { unlockFields(); state.activeChallenge = null; challengeResult.textContent = ''; }
  });
  newChallenge.addEventListener('click', pickChallenge);
  checkChallenge.addEventListener('click', () => {
    const ch = state.activeChallenge;
    if (!ch) return;
    let ok=false, success='', fail='';
    if (ch.type === 'tau') {
      ok = Math.abs(state.tau-ch.targetTau) <= Math.max(.01,ch.targetTau*.01);
      success = `τ = ${fmt(state.tau,2)} s ✓`;
      fail = `τ atual = ${fmt(state.tau,2)} s. Observe a razão L/R.`;
    } else if (ch.type === 'combo') {
      ok = Math.abs(state.tau-ch.targetTau)<=.015 && Math.abs(state.finalI-ch.targetI)<=.02;
      success = `Im = ${fmt(state.finalI,2)} A · τ = ${fmt(state.tau,2)} s ✓`;
      fail = `Atual: Im = ${fmt(state.finalI,2)} A · τ = ${fmt(state.tau,2)} s.`;
    } else if (ch.type === 'slower2') {
      ok = Math.abs(state.R-ch.baseR)<1e-8 && Math.abs(state.tau-2)<=.02;
      success = `τ = ${fmt(state.tau,2)} s ✓ Duas vezes mais lento.`;
      fail = `τ atual = ${fmt(state.tau,2)} s. Mantenha R e aumente L.`;
    } else if (ch.type === 'halfTau') {
      ok = Math.abs(state.L-ch.baseL)<1e-8 && Math.abs(state.tau-.5)<=.01;
      success = `τ = ${fmt(state.tau,2)} s ✓`;
      fail = `τ atual = ${fmt(state.tau,2)} s. Mantenha L e aumente R.`;
    } else {
      ok = Math.abs(state.R-ch.baseR)<1e-8 && Math.abs(state.L-ch.baseL)<1e-8 && Math.abs(state.finalI-2)<=.02 && Math.abs(state.tau-1)<=.01;
      success = `Im = ${fmt(state.finalI,2)} A · τ = ${fmt(state.tau,2)} s ✓`;
      fail = `Im atual = ${fmt(state.finalI,2)} A. R e L devem permanecer fixos.`;
    }
    challengeResult.textContent = ok ? success : fail;
    challengeResult.className = ok ? 'challenge-result success' : 'challenge-result';
  });

  readParameters();
  state.targetI = state.finalI;
  renderPrediction(0);
  renderStatic();

  let lastFrame = performance.now();
  function frame(now) {
    const dt = Math.min(.05,(now-lastFrame)/1000);
    lastFrame = now;
    updateDynamics(dt*state.speed);
    animateParticles(dt);
    renderDynamic();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
