# Circuitos Elétricos I — Guia Interativo de Aprendizagem

Plataforma modular desenvolvida com **Streamlit + Python** como complemento à disciplina **Circuitos Elétricos I** da UNILA.

O projeto não substitui as aulas. Ele funciona como um repositório acadêmico para localizar conceitos, equações, convenções, ferramentas de cálculo e exercícios resolvidos.

> **Estado atual: Versão 0.3** — arquitetura e página inicial ativas. O módulo **Aprenda a Teoria** permanece reservado para reconstrução do conteúdo teórico.

## 🎯 Visão do projeto

A plataforma está organizada em quatro módulos principais:

| Módulo | Objetivo |
|---|---|
| 📘 **Aprenda a Teoria** | Espaço reservado para conceitos, definições e conteúdo teórico. |
| 🎛️ **Interaja com a Teoria** | Simulações dinâmicas com parâmetros ajustáveis e visualização do comportamento elétrico dos circuitos. |
| 📐 **Formulários** | Biblioteca organizada de equações e relações matemáticas renderizadas em LaTeX. |
| ✅ **Exercícios Resolvidos** | Problemas desenvolvidos passo a passo com equações em LaTeX. |

## 📁 Estrutura

```text
.
├── app.py
├── assets/
├── data/
│   └── formulas.json
├── pages/
│   ├── teoria.py
│   ├── interaja.py
│   ├── formularios.py
│   └── exercicios.py
├── styles/
│   ├── main.css
│   └── formularios.css
├── utils/
│   ├── __init__.py
│   ├── formulas.py
│   └── helpers.py
└── requirements.txt
```

Todas as rotas são relativas, portanto o projeto funciona da mesma forma localmente, no GitHub e no Streamlit Cloud.

## 🚀 Executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Por padrão, o Streamlit abre em `http://localhost:8501`.

## ☁️ Publicar no Streamlit Cloud

1. Envie o repositório para o GitHub.
2. Crie uma nova aplicação no Streamlit Cloud.
3. Selecione `app.py` como arquivo principal.
4. Faça o deploy.

## 🧩 Adicionar um novo módulo

A lista `SECTIONS`, em `utils/helpers.py`, é a fonte central da navegação. Para adicionar uma seção, inclua a entrada em `SECTIONS`, coloque o ícone correspondente em `assets/` e crie a página em `pages/`.

## 📐 Formulários

O módulo `pages/formularios.py` utiliza a base `data/formulas.json` e as funções de `utils/formulas.py` para busca e filtros. A base atual contém **172 relações matemáticas distribuídas em 26 capítulos** do Boylestad, 12ª edição.

A consulta pode ser feita por:

- fórmulas mais frequentes;
- busca por nome, variável, tema, alias ou conceito;
- capítulo;
- tema.

Os detalhes são expandidos diretamente dentro do painel de cada fórmula, sem alterar a posição da consulta.

## 🎨 Identidade visual

- Paleta púrpura UNILA (`#88678b` / `#532458`).
- Cartões com bordas arredondadas, sombras suaves e estados de interação.
- Componentes matemáticos renderizados em LaTeX.
- Layout responsivo para desktop e dispositivos menores.

---

*Desenvolvido pelo Monitor **Bruno Manuel Olmedo Chavez** · UNILA.*

## Microexperimento 2 — Fontes CC
Incluído em `components/experiments/sources_dc/` com montagem interativa série/paralelo, fonte equivalente e modo desafio.


## Microexperimento 3 — Resistores em Série e Paralelo
Incluído em `components/experiments/resistors/` com montagem de 2 a 6 resistores, associação série/paralelo, circuito equivalente, cálculo instantâneo de `Req` e modo desafio.

## Microexperimento 4 — Código de Cores dos Resistores
Incluído em `components/experiments/resistor_colors/` com resistor SVG de quatro faixas, seleção visual de cores, leitura instantânea de valor/tolerância, intervalo esperado, modo inverso valor→cores e desafios de montagem/leitura.


## v26 — KCL e Divisão de Corrente
- Novo microexperimento CC com 2–3 ramos resistivos em paralelo.
- Corrente animada chega ao nó, divide-se entre os ramos e recombina.
- KCL em tempo real, campos numéricos, terceiro ramo e modo Desafio.
- Conteúdo referenciado ao Boylestad, 12ª ed., Cap. 6, §§ 6.5–6.6.


## v31 — gráfico temporal contínuo
- Carga e descarga agora compartilham o mesmo histórico contínuo de Vc(t).
- Trocar Carga ↔ Descarga durante a simulação inicia a nova fase a partir de Vc atual, sem salto artificial.
- O eixo X passou a usar janela móvel de 5τ; após 5τ, o relógio continua e a janela acompanha a simulação.

## v33 — Circuito RL · Crescimento e Decaimento da Corrente
- Nono microexperimento em `components/experiments/rl/`.
- Corrente `iL(t)` contínua entre armazenamento, decaimento e alterações de parâmetros.
- Chave SPDT em SVG com caminho fechado R–L para a fase de decaimento.
- Campo magnético qualitativo ao redor do indutor e partículas de corrente proporcionais a `iL`.
- Gráfico progressivo `iL` / `vL`, histórico contínuo e janela móvel de 5τ.
- `τ = L/R`, `Im = V/R`, energia magnética `WL = 1/2 Li²`, previsões e desafios.
- Card do catálogo incluído nos mesmos seletores CSS compartilhados dos demais microexperimentos.
