(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';

  const voltage = $('voltage');
  const resistance = $('resistance');
  const capacitance = $('capacitance');
  const tauPill = $('tauPill');
  const tauResult = $('tauResult');
  const tauFormula = $('tauFormula');
  const sourceLabel = $('sourceLabel');
  const resistorLabel = $('resistorLabel');
  const capLabel = $('capLabel');
  const vcSvg = $('vcSvg');
  const vcPercentSvg = $('vcPercentSvg');
  const currentSvg = $('currentSvg');
  const phaseBadge = $('phaseBadge');
  const switchStateLabel = $('switchStateLabel');
  const switchLever = $('switchLever');
  const switchHit = $('switchHit');
  const chargeMode = $('chargeMode');
  const dischargeMode = $('dischargeMode');
  const chargeButton = $('chargeButton');
  const dischargeButton = $('dischargeButton');
  const resetButton = $('resetButton');
  const observation = $('observation');
  const equationTitle = $('equationTitle');
  const equationSymbolic = $('equationSymbolic');
  const equationNumeric = $('equationNumeric');
  const timeLabel = $('timeLabel');
  const graphVc = $('graphVc');
  const graphTau = $('graphTau');
  const graphSvg = $('graphSvg');
  const graphGrid = $('graphGrid');
  const graphCurve = $('graphCurve');
  const graphPoint = $('graphPoint');
  const graphAnnotations = $('graphAnnotations');
  const chargeMarksTop = $('chargeMarksTop');
  const chargeMarksBottom = $('chargeMarksBottom');
  const particlesGroup = $('particles');
  const chargePathTop = $('chargePathTop');
  const chargePathBottom = $('chargePathBottom');
  const dischargePath = $('dischargePath');
  const challengeToggle = $('challengeToggle');
  const challengePanel = $('challengePanel');
  const challengePrompt = $('challengePrompt');
  const challengeNote = $('challengeNote');
  const newChallenge = $('newChallenge');
  const checkChallenge = $('checkChallenge');
  const challengeResult = $('challengeResult');
  const predictionResult = $('predictionResult');

  const state = {
    V: 10,
    Rk: 10,
    Cu: 100,
    tau: 1,
    vc: 0,
    current: 0,
    mode: 'charge',
    closed: false,
    speed: 1,
    phaseTime: 0,
    simTime: 0,
    startVc: 0,
    targetVc: 10,
    graphPoints: [],
    lastParam: null,
    activeChallenge: null,
    previousTau: 1,
    lastGridLeft: Number.NaN,
  };

  const fmt = (value, digits = 2) => Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  const clamp = (v, min, max, fallback) => Number.isFinite(v) ? Math.max(min, Math.min(max, v)) : fallback;
  const formatCurrent = (amps) => {
    const a = Math.abs(amps);
    if (a >= 1) return `${fmt(amps, 2)} A`;
    if (a >= 1e-3) return `${fmt(amps * 1e3, 2)} mA`;
    if (a >= 1e-6) return `${fmt(amps * 1e6, 2)} µA`;
    return `${fmt(amps * 1e9, 2)} nA`;
  };

  function readParameters() {
    state.V = clamp(Number(voltage.value), .1, 1000, state.V);
    state.Rk = clamp(Number(resistance.value), .1, 1000, state.Rk);
    state.Cu = clamp(Number(capacitance.value), .1, 10000, state.Cu);
    state.tau = state.Rk * state.Cu / 1000;
    state.targetVc = state.mode === 'charge' ? state.V : 0;
  }

  function setMode(mode, { start = false } = {}) {
    const modeChanged = mode !== state.mode;

    // Se o circuito já está rodando, trocar Carga ↔ Descarga inicia
    // imediatamente uma NOVA fase a partir da tensão atual do capacitor.
    // O histórico do gráfico NÃO é apagado: a curva permanece contínua.
    if (modeChanged && state.closed) start = true;

    state.mode = mode;
    chargeMode.classList.toggle('active', mode === 'charge');
    dischargeMode.classList.toggle('active', mode === 'discharge');
    chargeButton.classList.toggle('active', mode === 'charge' && state.closed);
    dischargeButton.classList.toggle('active', mode === 'discharge' && state.closed);

    // Ao escolher descarga com o circuito parado e o capacitor vazio,
    // parte-se de um capacitor previamente carregado em V para fins didáticos.
    if (mode === 'discharge' && state.vc < state.V * .01 && !state.closed) state.vc = state.V;

    if (start) {
      state.startVc = state.vc;
      state.phaseTime = 0;
      state.closed = true;
      // Garante um ponto exatamente na comutação, sem salto vertical artificial.
      const last = state.graphPoints[state.graphPoints.length - 1];
      if (!last || Math.abs(last.t - state.simTime) > 1e-9 || Math.abs(last.vc - state.vc) > 1e-9) {
        state.graphPoints.push({ t: state.simTime, vc: state.vc });
      }
    }
    state.targetVc = mode === 'charge' ? state.V : 0;
    renderStatic();
  }

  function setClosed(closed) {
    if (closed === state.closed) return;
    state.closed = closed;
    if (closed) {
      state.startVc = state.vc;
      state.phaseTime = 0;
      const last = state.graphPoints[state.graphPoints.length - 1];
      if (!last || Math.abs(last.t - state.simTime) > 1e-9 || Math.abs(last.vc - state.vc) > 1e-9) {
        state.graphPoints.push({ t: state.simTime, vc: state.vc });
      }
    }
    renderStatic();
  }

  function reset() {
    state.closed = false;
    state.mode = 'charge';
    state.vc = 0;
    state.current = 0;
    state.phaseTime = 0;
    state.simTime = 0;
    state.startVc = 0;
    state.graphPoints = [];
    state.lastGridLeft = Number.NaN;
    state.targetVc = state.V;
    renderStatic();
  }

  function updateDynamics(dtPhysical) {
    if (!state.closed) {
      state.current = 0;
      return;
    }

    state.phaseTime += dtPhysical;
    state.simTime += dtPhysical;

    const e = Math.exp(-state.phaseTime / Math.max(state.tau, 1e-9));
    if (state.mode === 'charge') {
      state.vc = state.V + (state.startVc - state.V) * e;
      state.current = (state.V - state.vc) / (state.Rk * 1000);
    } else {
      state.vc = state.startVc * e;
      state.current = -state.vc / (state.Rk * 1000);
    }

    // O eixo X mostra uma janela móvel de 5τ, mas o relógio da simulação
    // continua indefinidamente. Assim, carga e descarga aparecem no MESMO
    // histórico, sem reiniciar o gráfico em cada comutação.
    const sampleStep = Math.max((5 * state.tau) / 420, 1 / 120);
    const last = state.graphPoints[state.graphPoints.length - 1];
    if (!last || state.simTime - last.t >= sampleStep) {
      state.graphPoints.push({ t: state.simTime, vc: state.vc });
      // Proteção simples para sessões muito longas. A janela visível é de 5τ,
      // portanto milhares de pontos antigos não trazem benefício visual.
      if (state.graphPoints.length > 6000) state.graphPoints.splice(0, 1000);
    }
  }

  function setObservation() {
    observation.classList.remove('special');
    if (!state.closed) {
      observation.textContent = state.mode === 'charge'
        ? 'Chave aberta: o capacitor mantém a tensão atual. Feche-a para continuar a carga.'
        : 'Chave aberta: a descarga está interrompida. Feche-a para continuar.';
      return;
    }
    const tauPos = state.phaseTime / Math.max(state.tau, 1e-9);
    if (state.mode === 'charge' && tauPos >= .96 && tauPos <= 1.06 && state.startVc < state.V * .02) {
      observation.textContent = '1τ: Vc chegou a aproximadamente 63,2% do valor final, enquanto a corrente caiu para cerca de 36,8% do valor inicial.';
      observation.classList.add('special');
      return;
    }
    if (tauPos >= 5) {
      observation.textContent = state.mode === 'charge'
        ? 'Após 5τ, a corrente de carga é essencialmente nula e o capacitor se comporta como circuito aberto em CC.'
        : 'Após 5τ, a tensão residual do capacitor é muito pequena para fins didáticos.';
      observation.classList.add('special');
      return;
    }
    if (state.lastParam === 'R' && state.tau > state.previousTau) {
      observation.textContent = 'R aumentou → τ aumentou → o transitório ficou mais lento.';
      return;
    }
    if (state.lastParam === 'R' && state.tau < state.previousTau) {
      observation.textContent = 'R diminuiu → τ diminuiu → o transitório ficou mais rápido.';
      return;
    }
    if (state.lastParam === 'C' && state.tau > state.previousTau) {
      observation.textContent = 'C aumentou → há mais carga a armazenar → o capacitor leva mais tempo para atingir a mesma fração da tensão final.';
      return;
    }
    if (state.lastParam === 'C' && state.tau < state.previousTau) {
      observation.textContent = 'C diminuiu → τ diminuiu → a resposta ficou mais rápida.';
      return;
    }
    observation.textContent = state.mode === 'charge'
      ? 'Durante a carga, Vc cresce exponencialmente enquanto a corrente diminui.'
      : 'Durante a descarga, Vc cai exponencialmente e a corrente circula pelo caminho externo do capacitor.';
  }

  function renderSwitch() {
    if (!state.closed) {
      switchLever.setAttribute('x2', '214');
      switchLever.setAttribute('y2', '82');
      switchLever.style.opacity = '.9';
      switchStateLabel.textContent = 'chave aberta';
      phaseBadge.textContent = state.mode === 'charge' ? 'carga pausada' : 'descarga pausada';
      return;
    }
    if (state.mode === 'charge') {
      switchLever.setAttribute('x2', '188');
      switchLever.setAttribute('y2', '105');
      switchStateLabel.textContent = 'chave fechada · carga';
      phaseBadge.textContent = 'carregando';
    } else {
      switchLever.setAttribute('x2', '188');
      switchLever.setAttribute('y2', '158');
      switchStateLabel.textContent = 'chave fechada · descarga';
      phaseBadge.textContent = 'descarregando';
    }
  }

  function renderChargeMarks() {
    const fraction = Math.max(0, Math.min(1, state.V > 0 ? state.vc / state.V : 0));
    const count = 7;
    for (let i = 0; i < count; i += 1) {
      const opacity = Math.max(0, Math.min(1, fraction * count - i));
      chargeMarksTop.children[i].style.opacity = String(opacity);
      chargeMarksBottom.children[i].style.opacity = String(opacity);
    }
    const glow = .1 + fraction * .55;
    $('capTop').style.stroke = `rgba(83,36,88,${.58 + fraction * .34})`;
    $('capBottom').style.stroke = `rgba(83,36,88,${.58 + fraction * .34})`;
    $('capTop').style.filter = `drop-shadow(0 0 ${2 + fraction * 5}px rgba(139,106,143,${glow}))`;
    $('capBottom').style.filter = `drop-shadow(0 0 ${2 + fraction * 5}px rgba(139,106,143,${glow}))`;
  }

  function renderEquation() {
    const t = state.phaseTime;
    const tau = Math.max(state.tau, 1e-9);
    const e = Math.exp(-t / tau);
    if (state.mode === 'charge') {
      equationTitle.textContent = 'CARGA';
      equationSymbolic.innerHTML = 'Vc(t) = V(1 − e<sup>−t/RC</sup>)';
      if (state.startVc < state.V * .005) {
        equationNumeric.textContent = `Vc(${fmt(t,2)} s) = ${fmt(state.V,1)} · (1 − e^(−${fmt(t,2)}/${fmt(tau,2)})) = ${fmt(state.vc,2)} V`;
      } else {
        equationNumeric.textContent = `Vc parte de ${fmt(state.startVc,2)} V e tende a ${fmt(state.V,2)} V com τ = ${fmt(tau,2)} s.`;
      }
    } else {
      equationTitle.textContent = 'DESCARGA';
      equationSymbolic.innerHTML = 'Vc(t) = V₀e<sup>−t/RC</sup>';
      equationNumeric.textContent = `Vc(${fmt(t,2)} s) = ${fmt(state.startVc,2)} · e^(−${fmt(t,2)}/${fmt(tau,2)}) = ${fmt(state.vc,2)} V`;
    }
  }

  function renderStatic() {
    readParameters();
    tauPill.textContent = `${fmt(state.tau,2)} s`;
    tauResult.textContent = `τ = ${fmt(state.tau,2)} s`;
    tauFormula.textContent = `${fmt(state.Rk, state.Rk % 1 ? 1 : 0)} kΩ × ${fmt(state.Cu, state.Cu % 1 ? 1 : 0)} µF`;
    sourceLabel.textContent = `${fmt(state.V,1)} V`;
    resistorLabel.textContent = `R = ${fmt(state.Rk, state.Rk % 1 ? 1 : 0)} kΩ`;
    capLabel.textContent = `C = ${fmt(state.Cu, state.Cu % 1 ? 1 : 0)} µF`;
    chargeMode.classList.toggle('active', state.mode === 'charge');
    dischargeMode.classList.toggle('active', state.mode === 'discharge');
    chargeButton.classList.toggle('active', state.mode === 'charge' && state.closed);
    dischargeButton.classList.toggle('active', state.mode === 'discharge' && state.closed);
    renderSwitch();
    drawGraphGrid();
    renderDynamic();
  }

  function renderDynamic() {
    vcSvg.textContent = `Vc = ${fmt(state.vc,2)} V`;
    const fraction = state.V > 0 ? Math.max(0, Math.min(1, state.vc / state.V)) : 0;
    vcPercentSvg.textContent = `${fmt(fraction * 100,1)}% da tensão final`;
    currentSvg.textContent = `iC = ${formatCurrent(state.current)}`;
    timeLabel.textContent = `t = ${fmt(state.simTime,2)} s`;
    graphVc.textContent = `${fmt(state.vc,2)} V`;
    graphTau.textContent = `${fmt(state.simTime / Math.max(state.tau,1e-9),2)} τ`;
    setObservation();
    renderChargeMarks();
    renderEquation();
    const w = graphWindow();
    const gridStep = Math.max(state.tau / 50, 0.01);
    if (!Number.isFinite(state.lastGridLeft) || Math.abs(w.left - state.lastGridLeft) >= gridStep) {
      drawGraphGrid();
    }
    drawGraphCurve();
  }

  const graphBox = { left: 60, right: 650, top: 28, bottom: 278 };

  function graphWindow() {
    const span = Math.max(5 * state.tau, 1e-9);
    // Até 5τ, mantém a janela clássica 0 → 5τ. Depois disso, a janela
    // acompanha a simulação e conserva sempre uma largura de 5τ.
    const right = Math.max(span, state.simTime);
    const left = Math.max(0, right - span);
    return { left, right, span };
  }

  function xFor(t) {
    const w = graphWindow();
    return graphBox.left + ((t - w.left) / w.span) * (graphBox.right - graphBox.left);
  }

  function yFor(v) {
    const ymax = Math.max(state.V, state.startVc, .1);
    return graphBox.bottom - (Math.max(0, Math.min(ymax, v)) / ymax) * (graphBox.bottom - graphBox.top);
  }

  function svgEl(tag, attrs = {}, text = '') {
    const el = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, String(v)));
    if (text) el.textContent = text;
    return el;
  }

  function drawGraphGrid() {
    graphGrid.innerHTML = '';
    graphAnnotations.innerHTML = '';
    const w = graphWindow();
    state.lastGridLeft = w.left;

    graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:graphBox.bottom,x2:graphBox.right,y2:graphBox.bottom,class:'graph-axis'}));
    graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:graphBox.top,x2:graphBox.left,y2:graphBox.bottom,class:'graph-axis'}));

    const ymax = Math.max(state.V, state.startVc, .1);
    [0,.25,.5,.75,1].forEach((f) => {
      const y = graphBox.bottom - f * (graphBox.bottom-graphBox.top);
      graphGrid.appendChild(svgEl('line',{x1:graphBox.left,y1:y,x2:graphBox.right,y2:y,class:'graph-gridline'}));
      graphGrid.appendChild(svgEl('text',{x:graphBox.left-10,y:y+3,'text-anchor':'end',class:'graph-tick'}, `${fmt(ymax*f, f===0?0:1)}`));
    });

    // Seis marcas delimitam cinco intervalos de 1τ. Quando t > 5τ,
    // os rótulos avançam junto com a janela em vez de congelar em 1τ…5τ.
    for (let i=0;i<=5;i+=1) {
      const t = w.left + i * state.tau;
      const x = graphBox.left + (i/5) * (graphBox.right - graphBox.left);
      if (i > 0) graphGrid.appendChild(svgEl('line',{x1:x,y1:graphBox.top,x2:x,y2:graphBox.bottom,class:'tau-line'}));
      const tauPosition = t / Math.max(state.tau,1e-9);
      const label = Math.abs(tauPosition - Math.round(tauPosition)) < .025
        ? `${Math.round(tauPosition)}τ`
        : `${fmt(tauPosition,1)}τ`;
      graphGrid.appendChild(svgEl('text',{x,y:graphBox.bottom+20,'text-anchor':'middle',class:'tau-label'}, label));
    }

    graphGrid.appendChild(svgEl('text',{x:(graphBox.left+graphBox.right)/2,y:318,'text-anchor':'middle',class:'graph-axis-label'}, 'tempo · janela móvel de 5τ'));
    const yLabel = svgEl('text',{x:17,y:(graphBox.top+graphBox.bottom)/2,'text-anchor':'middle',class:'graph-axis-label',transform:`rotate(-90 17 ${(graphBox.top+graphBox.bottom)/2})`}, 'Vc (V)');
    graphGrid.appendChild(yLabel);

    // A anotação de 63,2% acompanha o PRIMEIRO τ da fase de carga atual.
    // Como phaseTime reinicia em cada comutação, o instante absoluto é:
    const phaseStart = state.simTime - state.phaseTime;
    const oneTauTime = phaseStart + state.tau;
    if (state.mode === 'charge' && state.startVc < state.V*.02 && oneTauTime >= w.left && oneTauTime <= w.right) {
      const x = xFor(oneTauTime);
      const y = yFor(state.V*(1-Math.exp(-1)));
      graphAnnotations.appendChild(svgEl('text',{x:x+8,y:y-10,class:'graph-note'}, '≈ 63,2% em 1τ desta carga'));
    }
  }

  function drawGraphCurve() {
    if (!state.graphPoints.length) {
      graphCurve.setAttribute('d','');
      graphPoint.setAttribute('opacity','0');
      return;
    }

    const w = graphWindow();
    let usable = state.graphPoints.filter(p => p.t >= w.left - 1e-9 && p.t <= w.right + 1e-9);

    // Inclui um ponto imediatamente anterior à janela para que a curva entre
    // suavemente pela borda esquerda, sem parecer começar do nada.
    const firstVisibleIndex = state.graphPoints.findIndex(p => p.t >= w.left);
    if (firstVisibleIndex > 0) usable = [state.graphPoints[firstVisibleIndex-1], ...usable];

    if (!usable.length) {
      graphCurve.setAttribute('d','');
      graphPoint.setAttribute('opacity','0');
      return;
    }

    const d = usable.map((p,i) => `${i?'L':'M'} ${xFor(p.t).toFixed(2)} ${yFor(p.vc).toFixed(2)}`).join(' ');
    graphCurve.setAttribute('d', d);

    const last = state.graphPoints[state.graphPoints.length-1];
    if (last && last.t >= w.left - 1e-9 && last.t <= w.right + 1e-9) {
      graphPoint.setAttribute('cx',xFor(last.t));
      graphPoint.setAttribute('cy',yFor(last.vc));
      graphPoint.setAttribute('opacity','1');
    } else {
      graphPoint.setAttribute('opacity','0');
    }
  }

  function createChargeMarks() {
    const xs = [548,560,572,584,596,608,620];
    xs.forEach((x) => {
      const plus = svgEl('text',{x,y:181,'text-anchor':'middle',class:'charge-mark plus'},'+');
      const minus = svgEl('text',{x,y:259,'text-anchor':'middle',class:'charge-mark minus'},'−');
      plus.style.opacity='0'; minus.style.opacity='0';
      chargeMarksTop.appendChild(plus); chargeMarksBottom.appendChild(minus);
    });
  }

  const MAX_PARTICLES = 16;
  const particles = [];
  for (let i=0;i<MAX_PARTICLES;i+=1) {
    const dot = svgEl('circle',{r:4.2,class:'current-particle'});
    particlesGroup.appendChild(dot);
    particles.push(dot);
  }
  const pathLengths = {
    top: chargePathTop.getTotalLength(),
    bottom: chargePathBottom.getTotalLength(),
    discharge: dischargePath.getTotalLength(),
  };
  let travelTop=0, travelBottom=0, travelDis=0;

  function animateParticles(dt) {
    const I = Math.abs(state.current);
    const initialI = state.V / Math.max(state.Rk*1000,1e-9);
    const intensity = initialI <= 0 ? 0 : Math.min(1, I / initialI);
    const visible = (!state.closed || I < initialI*.004) ? 0 : Math.max(2, Math.round(2 + intensity*(MAX_PARTICLES-2)));
    const speed = 42 + intensity*130;
    if (state.mode === 'charge') {
      travelTop = (travelTop + speed*dt) % pathLengths.top;
      travelBottom = (travelBottom + speed*dt) % pathLengths.bottom;
    } else {
      travelDis = (travelDis + speed*dt) % pathLengths.discharge;
    }
    particles.forEach((dot,index) => {
      if (index >= visible) { dot.style.opacity='0'; return; }
      let point;
      if (state.mode === 'charge') {
        const topCount = Math.ceil(visible/2);
        if (index < topCount) {
          const d = (travelTop + index*(pathLengths.top/topCount)) % pathLengths.top;
          point = chargePathTop.getPointAtLength(d);
        } else {
          const j = index-topCount; const bottomCount = visible-topCount;
          const d = (travelBottom + j*(pathLengths.bottom/Math.max(bottomCount,1))) % pathLengths.bottom;
          point = chargePathBottom.getPointAtLength(d);
        }
      } else {
        const d = (travelDis + index*(pathLengths.discharge/visible)) % pathLengths.discharge;
        point = dischargePath.getPointAtLength(d);
      }
      dot.setAttribute('cx',point.x.toFixed(2));
      dot.setAttribute('cy',point.y.toFixed(2));
      dot.style.opacity=String(.35 + intensity*.55);
    });
  }

  function handleParameterChange(kind) {
    const oldTau = state.tau;
    const oldVc = state.vc;
    readParameters();
    state.previousTau = oldTau;
    state.lastParam = kind;
    state.vc = Math.min(oldVc, state.V);
    state.startVc = state.vc;
    state.phaseTime = 0;
    state.simTime = 0;
    state.graphPoints = [];
    state.lastGridLeft = Number.NaN;
    if (state.closed) state.targetVc = state.mode === 'charge' ? state.V : 0;
    renderStatic();
  }

  voltage.addEventListener('input', () => handleParameterChange('V'));
  resistance.addEventListener('input', () => handleParameterChange('R'));
  capacitance.addEventListener('input', () => handleParameterChange('C'));

  chargeMode.addEventListener('click', () => setMode('charge'));
  dischargeMode.addEventListener('click', () => setMode('discharge'));
  chargeButton.addEventListener('click', () => setMode('charge',{start:true}));
  dischargeButton.addEventListener('click', () => setMode('discharge',{start:true}));
  resetButton.addEventListener('click', reset);
  switchHit.addEventListener('click', () => setClosed(!state.closed));
  switchHit.addEventListener('keydown', (e) => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); setClosed(!state.closed); } });

  document.querySelectorAll('.speed-button').forEach((btn) => btn.addEventListener('click', () => {
    state.speed = Number(btn.dataset.speed);
    document.querySelectorAll('.speed-button').forEach(b => b.classList.toggle('active', b===btn));
  }));

  document.querySelectorAll('.prediction-options button').forEach((btn) => btn.addEventListener('click', () => {
    document.querySelectorAll('.prediction-options button').forEach(b => b.classList.remove('correct','wrong'));
    if (btn.dataset.answer === 'slow') {
      btn.classList.add('correct');
      predictionResult.textContent = 'Correto. Como τ = RC, aumentar R aumenta τ e torna o transitório mais lento.';
    } else {
      btn.classList.add('wrong');
      predictionResult.textContent = 'Não. Aumentar R aumenta o produto RC; portanto, o transitório fica mais lento.';
    }
  }));

  const challenges = [
    {type:'tau', target:2, text:'Faça a constante de tempo ser exatamente 2 s.', note:'Altere R e C. Qualquer combinação válida com RC = 2 s é aceita.'},
    {type:'tau', target:.5, text:'Configure o circuito para atingir aproximadamente 63,2% da tensão final em 0,5 s.', note:'Isso acontece em 1τ; portanto, procure τ = 0,5 s.'},
    {type:'slower', baseR:10, baseC:100, text:'Faça o capacitor carregar mais lentamente sem alterar C.', note:'C fica fixo em 100 µF. Modifique apenas R.'},
    {type:'faster2', baseR:10, baseC:100, text:'Faça o transitório ficar duas vezes mais rápido mantendo R constante.', note:'R fica fixo em 10 kΩ. A constante de tempo deve cair pela metade.'},
  ];

  function applyChallenge(ch) {
    state.activeChallenge = ch;
    challengePrompt.textContent = ch.text;
    challengeNote.textContent = ch.note;
    challengeResult.textContent=''; challengeResult.className='challenge-result';
    if (ch.type==='slower' || ch.type==='faster2') {
      resistance.value=String(ch.baseR); capacitance.value=String(ch.baseC);
      handleParameterChange(null);
      resistance.disabled = ch.type==='faster2';
      capacitance.disabled = ch.type==='slower';
    } else {
      resistance.disabled=false; capacitance.disabled=false;
    }
  }
  function pickChallenge() {
    const pool = challenges.filter(c => c !== state.activeChallenge);
    applyChallenge(pool[Math.floor(Math.random()*pool.length)] || challenges[0]);
  }
  challengeToggle.addEventListener('click', () => {
    const opening = challengePanel.hidden;
    challengePanel.hidden=!opening;
    challengeToggle.textContent=opening?'Ocultar desafio':'🎯 Desafio';
    if (opening) pickChallenge();
    else { resistance.disabled=false; capacitance.disabled=false; state.activeChallenge=null; challengeResult.textContent=''; }
  });
  newChallenge.addEventListener('click', pickChallenge);
  checkChallenge.addEventListener('click', () => {
    const ch=state.activeChallenge; if (!ch) return;
    let ok=false, success='', fail='';
    if (ch.type==='tau') {
      ok=Math.abs(state.tau-ch.target)<=Math.max(.01,ch.target*.01);
      success=`τ = ${fmt(state.tau,2)} s ✓`;
      fail=`τ atual = ${fmt(state.tau,2)} s. Observe o produto RC.`;
    } else if (ch.type==='slower') {
      ok=Math.abs(state.Cu-ch.baseC)<1e-6 && state.tau>1.05;
      success=`τ = ${fmt(state.tau,2)} s ✓ O transitório ficou mais lento.`;
      fail=`τ atual = ${fmt(state.tau,2)} s. Mantenha C = ${fmt(ch.baseC,0)} µF e aumente R.`;
    } else {
      ok=Math.abs(state.Rk-ch.baseR)<1e-6 && Math.abs(state.tau-.5)<=.01;
      success=`τ = ${fmt(state.tau,2)} s ✓ Duas vezes mais rápido.`;
      fail=`τ atual = ${fmt(state.tau,2)} s. Mantenha R e reduza C até τ = 0,50 s.`;
    }
    challengeResult.textContent=ok?success:fail;
    challengeResult.className=ok?'challenge-result success':'challenge-result';
  });

  createChargeMarks();
  renderStatic();
  let lastFrame=performance.now();
  function frame(now) {
    const dt=Math.min(.05,(now-lastFrame)/1000); lastFrame=now;
    updateDynamics(dt*state.speed);
    animateParticles(dt);
    renderDynamic();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
