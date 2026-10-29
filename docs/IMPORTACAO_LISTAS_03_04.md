# Relatório — Importação das Listas 03 e 04 (Boylestad, 12ª ed., cap. 8)

Versão da plataforma: **1.1** · Pacote fornecido pelo docente:
`Listas_03_04_Boylestad_Carga_e_Figuras.zip`.

## 1. Resultado

| Item | Quantidade |
|---|---:|
| Exercícios da Lista 03 (códigos 3.01–3.27) | **27** |
| Exercícios da Lista 04 (códigos 4.01–4.22) | **22** |
| Total cadastrado em Exercícios Propostos | **49** |
| Figuras PNG integradas (originais do livro) | **38** |
| Vínculos exercício–figura | **49** (1 figura por exercício) |
| Figuras compartilhadas por mais de um exercício | 10 (ex.: 8.135 → 4.17 e 4.18; 8.136 → 4.19 e 4.20; 8.113 → 3.07, 3.14 e 4.01) |
| Inconsistências encontradas entre fichas, índice e arquivos | **0** |

Todos ficam **disponíveis para entregas**, como indicado nas fichas.

## 2. Como funciona

**Pacote versionado no repositório.** O conteúdo do ZIP foi copiado sem
alterações para `conteudo/pacotes/boylestad_12ed_cap8_listas_03_04/`
(arquivo de fichas, índice e as 38 figuras). Ele é publicado junto com o
código: não há upload manual após o deploy nem caminhos absolutos.

**Leitura fiel das fichas** (`resolucoes/importacao.py`). Cada bloco do arquivo
do docente é lido campo a campo (Código, Título, Unidade ou tema, Temas e
conceitos, Enunciado, Descrição complementar, Materiais de apoio, Disponível
para entregas). Nenhum texto é reescrito. Única adaptação: nos Materiais de
apoio, a instrução ao docente *“Arquivo de apoio da figura: FIG_x.png (incluído
no pacote de figuras; publicar ou anexar…)”* — que a própria importação cumpre —
passa a ser *“Figura do circuito: FIG_x.png — exibida junto ao enunciado nesta
plataforma.”* A referência bibliográfica (Boylestad, 12ª ed., capítulo 8,
número do problema, figura e página) permanece intacta.

**Vínculo exato com a figura.** A figura de cada exercício é o arquivo citado
na própria ficha e é **conferida contra o índice** `INDICE_FIGURAS.txt` pelo par
(lista, número do problema original). Nada é deduzido da numeração sequencial.
Antes de gravar, o pacote inteiro é validado: 27 + 22 fichas, códigos únicos e
coerentes com a lista, campos obrigatórios presentes, título citando o problema
original, figura existente e idêntica à do índice, enunciado citando a figura,
referência completa, todas as figuras do índice utilizadas e — para os
problemas **57, 58, 59 e 60** da Lista 04 — **exatamente os itens a) e b)**.
Se qualquer verificação falhar, nada é gravado.

**Modelo de dados.** Nova tabela `ce1_exercise_figures` (exercício → figura,
com ordem, rótulo, legenda e dimensões). É uma tabela **nova**: nenhuma coluna
existente foi alterada, e bancos já em uso a recebem automaticamente na
inicialização. A mesma tabela atende figuras futuras enviadas pela
administração (*Gerenciar Exercícios → Editar → Figuras do enunciado*).

**Importação automática e idempotente.** Na inicialização, a plataforma aplica
o pacote **uma única vez por versão** (marcador gravado no banco). Reiniciar,
reimplantar ou repetir a operação não cria duplicatas. Se um código já existir,
o exercício do professor **não é sobrescrito** (é apenas relatado). Exercícios
excluídos pela administração não voltam sozinhos; podem ser recriados em
*Configurações → Pacotes de exercícios → Importar ausentes*.

## 3. Persistência

* **Exercícios e vínculos:** no banco PostgreSQL (Supabase), como qualquer exercício.
* **Imagens:** arquivos do repositório, publicados a cada deploy junto com o
  código e lidos pelo servidor (caminho relativo ao projeto). Uma figura usada
  por vários exercícios é armazenada uma só vez.
* **Figuras novas enviadas pela administração:** no armazenamento persistente
  (Supabase Storage), incluídas no backup completo.
* As imagens são entregues ao navegador pelo próprio Streamlit; não existem
  links externos que possam quebrar.

## 4. Apresentação ao aluno

Em **Exercícios Propostos**, cada exercício mostra “Lista 03 · Exercício 3.08”,
título, unidade e temas. Em **Ver enunciado e circuito**: enunciado (com as
quebras de linha dos itens a, b, c…), **figura logo abaixo** em tamanho natural
(sem ampliação que borre os valores), legenda “Figura 8.114 · Boylestad, 12ª
ed., cap. 8, p. 279”, botão **Ampliar figura** (quadro rolável a 1,5× — no
celular, deslize para percorrer o circuito), descrição complementar e materiais
de apoio. Novo filtro **Lista** (integrado aos filtros existentes) e a busca
aceita o número da figura (“8.135”).

A mesma apresentação aparece em *Submeter Resolução*, na avaliação do
administrador (nova aba **Enunciado**) e na página pública das resoluções aprovadas.

## 5. Arquivos alterados

| Arquivo | Alteração |
|---|---|
| `conteudo/pacotes/boylestad_12ed_cap8_listas_03_04/` | **Novo** — pacote original do docente. |
| `resolucoes/importacao.py` | **Novo** — leitura, validação e importação idempotente. |
| `resolucoes/ui/exercise_view.py` | **Novo** — enunciado + figura + ampliação. |
| `resolucoes/db.py` | Tabela `ce1_exercise_figures` (com RLS no PostgreSQL). |
| `resolucoes/services/exercises.py` | Figuras (listar, ler, anexar, remover); inserção compartilhada com a importação. |
| `resolucoes/services/__init__.py`, `config.py` | Importação na inicialização (`[app] import_packs`, padrão ligado). |
| `resolucoes/services/admin.py`, `backup.py` | Figuras no backup; restauração em instalação recém-criada. |
| `resolucoes/ui/views_student.py` | Filtro Lista, busca por figura, figura no enunciado. |
| `resolucoes/ui/views_public.py`, `views_admin.py` | Figura na página pública e na avaliação; gestão de figuras; painel de pacotes. |
| `resolucoes/storage.py` | Bucket criado pelo script aceita PNG/JPEG além de PDF. |
| `styles/exercicios.css` | Estilo das figuras (claro, centralizado, responsivo). |
| `scripts/dados_demonstracao.py`, `scripts/restaurar_backup.py` | Compatíveis com o pacote. |
| `tests/test_importacao.py`, `tests/e2e_navegador.py` | Novos testes. |

**Não alterados:** regras de entrega (YouTube + PDF + Falstad), avaliação,
autenticação, perfis, permissões e demais módulos.

## 6. Testes executados

| Bateria | Resultado |
|---|---|
| Serviços, SQLite | **93 aprovados**, 2 ignorados (específicos do PostgreSQL) |
| Serviços, PostgreSQL 16 real | **161 aprovados**, 2 ignorados |
| Navegador de ponta a ponta (Chromium, servidor real, instalação nova) | **65/65 verificações** |

Específicos desta importação: pacote íntegro (49 = 27 + 22, códigos exatos e
únicos); campos idênticos ao arquivo do docente; 38 figuras existentes, todas
usadas e iguais às do índice; figuras compartilhadas corretas; 57–60 só com a)
e b); ausência de respostas/gabaritos; importação no banco com 49 vínculos e
38 imagens PNG legíveis; idempotência (repetição + reinício: 49 exercícios, 49
vínculos, 1 registro de importação); exercício do professor com o mesmo código
preservado; excluído não reaparece e pode ser reimportado só por administrador;
fluxo completo de entrega e aprovação num exercício importado (4.17); figura
enviada pela administração (validação, permissão e remoção).

No navegador: instalação nova já com o pacote; aluna vê 27 + 22 exercícios;
busca “8.114” encontra 3.08 e 4.02; figura carregada com legenda correta;
ampliação; **mesmos resultados após reiniciar o servidor**; no celular
(390 px) a figura cabe na tela sem corte. Fluxo de entrega anterior e
regressão das demais páginas: aprovados.

## 7. Limitações

* No celular em modo retrato, a figura cabe na largura da tela (~317 px); para
  ler valores pequenos, use **Ampliar figura** ou gire o aparelho.
* Se o repositório do GitHub for **público**, as figuras do livro ficam
  acessíveis a quem visitar o repositório. Se isso for uma preocupação de
  direitos autorais, torne o repositório privado — o Streamlit Community Cloud
  implanta a partir de repositórios privados.
* No banco de produção, códigos 3.xx/4.xx já criados manualmente durante os
  testes são preservados e listados como “mantidos” em *Configurações →
  Pacotes de exercícios*. Para usar a versão do pacote, exclua o exercício de
  teste (se não tiver entregas) e clique em **Importar ausentes**.
* Não foi possível testar contra o Supabase real neste ambiente (sem acesso
  ao domínio); a importação foi verificada em PostgreSQL 16 local e SQLite.
