# Circuitos Elétricos I — Guia Interativo de Aprendizagem

Plataforma modular desenvolvida com **Streamlit + Python** como complemento à disciplina **Circuitos Elétricos I** da UNILA.

O projeto não substitui as aulas. Ele funciona como um repositório acadêmico para localizar conceitos, equações, convenções, ferramentas de cálculo e exercícios resolvidos.

> **Versão 1.0** — módulo **Exercícios Resolvidos** colaborativo: alunos submetem
> resoluções (vídeo no YouTube + PDF + circuito no Falstad), a administração avalia
> qualitativamente e as resoluções aprovadas são publicadas automaticamente.

## 🎯 Visão do projeto

A plataforma está organizada em quatro módulos principais:

| Módulo | Objetivo |
|---|---|
| 📘 **Aprenda a Teoria** | Espaço reservado para conceitos, definições e conteúdo teórico. |
| 🎛️ **Interaja com a Teoria** | Simulações dinâmicas com parâmetros ajustáveis e visualização do comportamento elétrico dos circuitos. |
| 📐 **Formulários** | Biblioteca organizada de equações e relações matemáticas renderizadas em LaTeX. |
| ✅ **Exercícios Resolvidos** | Biblioteca colaborativa de resoluções de estudantes aprovadas pela equipe da disciplina (vídeo, PDF e Falstad). |

## 📁 Estrutura

```text
.
├── app.py                     # página inicial
├── pages/                     # teoria, interaja, formularios, exercicios (+ rotas legadas)
├── components/experiments/    # microexperimentos
├── data/  styles/  utils/  assets/
├── resolucoes/                # módulo Exercícios Resolvidos
│   ├── services/              # regras de negócio e permissões (sem Streamlit)
│   ├── ui/                    # interface do módulo
│   ├── db.py  storage.py  validators.py  parecer.py  security.py  config.py
├── scripts/                   # criar_admin, preparar_supabase, backup, demonstração
├── tests/                     # pytest + teste de navegador (Playwright)
├── docs/                      # instalação, guia administrativo, alterações, testes
└── .streamlit/                # config.toml e modelo de segredos
```

## 🚀 Executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Por padrão, o Streamlit abre em `http://localhost:8501`.

Para experimentar o módulo Exercícios Resolvidos sem serviços externos, use o
**modo demonstração** descrito em `docs/INSTALACAO.md` (§ 2.1).

## ☁️ Publicar no Streamlit Cloud

1. Envie o repositório para o GitHub (os segredos ficam fora dele).
2. Configure o Supabase gratuito (banco + armazenamento de PDFs) — `docs/INSTALACAO.md` § 3.
3. Crie a aplicação no Streamlit Cloud com `app.py` e cole os segredos em *Settings → Secrets*.
4. Cadastre os administradores iniciais — `docs/INSTALACAO.md` § 5.

## ✅ Exercícios Resolvidos (v1.0)

* Catálogo público com miniaturas do YouTube, busca, filtros por unidade e nível e ordenação.
* Página de cada resolução com três formas de estudo: vídeo incorporado, PDF (visualizar/baixar) e circuito no Falstad.
* Botão flutuante **Ações**: Submeter Resolução, Alterar Resolução e Administração (somente administradores).
* Perfis Visitante, Aluno e Administrador com autenticação real e permissões verificadas no servidor.
* Fluxo formal Rascunho → Submetida → Em análise → Devolvida/Reenviada → Aprovada/Retirada, com versões imutáveis.
* Avaliação qualitativa (Excelente, Muito Bom, Bom ou Devolvido para Correção) — **sem notas**.
* Parecer acadêmico em PDF e compartilhamento pelo WhatsApp.
* Logs de usuários e submissões, histórico de avaliações, exportação CSV, backup completo e verificação de integridade.
* Custo zero: Streamlit Community Cloud + Supabase Free.

Documentação: [`docs/INSTALACAO.md`](docs/INSTALACAO.md) ·
[`docs/GUIA_ADMINISTRATIVO.md`](docs/GUIA_ADMINISTRATIVO.md) ·
[`docs/REGISTRO_DE_ALTERACOES.md`](docs/REGISTRO_DE_ALTERACOES.md) ·
[`docs/RELATORIO_DE_TESTES.md`](docs/RELATORIO_DE_TESTES.md)

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
