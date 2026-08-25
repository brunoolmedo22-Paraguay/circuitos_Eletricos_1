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
