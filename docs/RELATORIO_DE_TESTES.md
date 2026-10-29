# Relatório de testes — versão 1.1

Executado em outubro de 2026 sobre o código final entregue, em ambiente Linux
(Python 3.12, Streamlit 1.66, PostgreSQL 16, Chromium via Playwright).
Somente testes realmente executados estão listados como aprovados.

## 1. Resumo

| Bateria | Ambiente | Resultado |
|---|---|---|
| Testes de serviço (`pytest`) | SQLite + armazenamento no banco e em disco | **93 aprovados**, 2 ignorados (específicos do PostgreSQL) |
| Testes de serviço (`pytest`) | **PostgreSQL 16 real** + SQLite, ambos os armazenamentos | **161 aprovados**, 2 ignorados (RLS nos cenários SQLite) |
| Navegador de ponta a ponta (`tests/e2e_navegador.py`) | Servidor Streamlit real + Chromium (desktop e celular), instalação nova | **65/65 verificações aprovadas** |
| Regressão visual | Capturas de Aprenda a Teoria e Formulários antes/depois | Sem diferenças visíveis |

Como reproduzir: `docs/INSTALACAO.md`, § 9.

## 2. Testes obrigatórios

### Teste A — Usuário aluno ✅
Navegador: cadastro pela administração com senha provisória → login → troca
obrigatória da senha → sessão mantida ao recarregar a página → exercícios
propostos → seleção do 2.04 → link do YouTube → **upload real do PDF** → link
Falstad → envio sem declaração recusado → envio → estado “Submetida”.
Serviço: entrega incompleta recusada indicando os itens ausentes; vídeo privado
(HTTP 401) e inexistente (404) bloqueiam o envio; YouTube fora do ar não bloqueia
e marca “não verificado”.

### Teste B — Devolução ✅
Navegador: administrador inicia a análise, as abas Vídeo, PDF e Falstad estão
disponíveis, o PDF do aluno é acessível, critérios avaliados (cálculos “Não
atende”), devolução registrada, **parecer PDF baixado pelo administrador**,
link do WhatsApp com mensagem preenchida; aluna vê “Devolvida”, **baixa o
parecer**, prepara a v2, troca vídeo e PDF, reenvia (“Reenviada”) e o histórico
mantém “Versão v1 — Devolvida”.
Serviço: o texto do parecer contém “DEVOLVIDO PARA CORREÇÃO”, nome da aluna,
código do exercício e avaliador.

### Teste C — Aprovação ✅
Navegador: segundo administrador (com troca de senha provisória) aprova como
**Aprovado — Muito Bom**; o catálogo mostra título, autora e nível; a miniatura
usa o ID do vídeo **aprovado** (v2); o vídeo está incorporado; “Abrir no
YouTube” aponta para o vídeo correto; o link do Falstad é **idêntico** ao
enviado; visitante baixa o PDF e a pré-visualização funciona.
Serviço: aprovação recusada sem os três materiais, com critério “Não atende” ou
com nível inexistente; nova versão de resolução aprovada não substitui a
publicação até ser aprovada; devolução da nova versão mantém a anterior publicada.

### Teste D — Segurança ✅
* Visitante e aluno recebem *PermissionDenied* em: iniciar análise, aprovar,
  bandeja, lista de usuários, logs, backup e criação de exercícios.
* Aluna não vê “Administração” no menu e é barrada ao abrir a URL do painel.
* Aluno não altera nem lê a entrega de outro (resposta “não encontrada”, sem
  revelar a existência); PDF privado inacessível a outros alunos e a visitantes.
* Parecer privado: outro aluno e visitante não acessam.
* Devolvida nunca aparece no catálogo; retirada deixa o PDF público inacessível.
* Aluno não muda o próprio perfil nem campos protegidos (nome, matrícula,
  login), mesmo enviando-os diretamente ao serviço.
* Revogar o perfil de administrador encerra as sessões na hora.
* Último administrador não pode ser removido ou desativado.
* Configuração inicial exige token e só funciona uma vez.
* Mensagem de login idêntica para usuário inexistente e senha errada; 20 tentativas
  erradas seguidas não bloqueiam a conta (decisão da coordenação).
* Senhas e hashes nunca aparecem no log de auditoria.
* PostgreSQL: RLS ativo em todas as tabelas; um papel diferente do dono, mesmo
  com permissão SELECT, leu **0 linhas**.
* Concorrência: dois administradores na mesma entrega, envio duplicado e visão
  desatualizada geram conflito claro, sem dados duplicados.

### Teste E — Persistência ✅ (local) / ⚠️ (nuvem: requer configuração)
* Serviço: nova instância da plataforma após descartar as conexões lê entrega,
  PDF, parecer e login — em SQLite e em **PostgreSQL real**.
* Navegador: **o servidor Streamlit foi encerrado e iniciado novamente**; a
  publicação, o PDF, o histórico e as avaliações continuaram disponíveis.
* Backup completo restaurado em outro banco/armazenamento, com login, catálogo e
  PDFs funcionando (simula migração de provedor).
* Falha de armazenamento ao salvar não altera o banco; falha ao gravar o parecer
  deixa a entrega “Em análise”, sem avaliação parcial; conflito na aprovação
  remove o parecer órfão.
* Configuração não persistente em modo produção é recusada (tela “Configuração pendente”).

### Teste F — Regressão ✅
Navegador: página inicial, Aprenda a Teoria, Formulários e Interaja carregam
sem exceções; um microexperimento abre; as rotas antigas `/ejercicios` e
`/interactue` redirecionam para as páginas oficiais. Capturas de Teoria antes e
depois da mudança são visualmente idênticas.

### Teste G — Listas 03 e 04 com figuras (v1.1) ✅
Detalhado em `docs/IMPORTACAO_LISTAS_03_04.md` (§ 6): integridade das 49
fichas, 38 figuras e vínculos conferidos contra o índice, itens a) e b) dos
problemas 57–60, idempotência após repetição e reinício, preservação de
exercícios do professor, entrega completa num exercício importado e exibição
da figura no navegador (desktop, celular e após reiniciar o servidor).

## 3. Classificação das funcionalidades

**Implementadas e verificadas:** catálogo, busca, filtros, agrupamento por
exercício, página da resolução, botão flutuante (desktop e celular), cadastro e
autenticação, troca obrigatória de senha, sessão por cookie (local), exercícios
propostos, formulário de entrega, rascunhos, versões, estados, bandeja, avaliação
qualitativa, pareceres em PDF, link do WhatsApp, publicação automática, retirada,
restauração e ajuste de nível, gestão de usuários e importação CSV, logs e
exportação CSV, histórico, configurações, integridade, backup e restauração,
modo demonstração, tela de configuração pendente.

**Implementadas que requerem configuração externa (não testadas contra o serviço real):**
* **Supabase Storage** — o cliente foi testado contra um servidor HTTP que
  simula a API (envio, leitura, existência, remoção, criação de bucket,
  cabeçalho da chave secreta). O ambiente de testes não tinha acesso ao domínio
  `supabase.co`. O banco foi testado em PostgreSQL 16 local.
* **Verificação do YouTube (oEmbed e Data API)** — testada com respostas
  simuladas; sem acesso à rede do YouTube no ambiente, as miniaturas e o player
  não aparecem nas capturas (o gradiente de reserva aparece, como previsto).
* **Cookie de sessão no Streamlit Community Cloud** — verificado localmente.
* **Workflow do GitHub Actions** — sintaxe revisada, não executado no GitHub.

**Primeiro teste recomendado após a implantação:** repetir o fluxo do critério
de aceitação com uma conta de aluno de teste, depois *Configurações →
Diagnóstico* (banco e armazenamento devem aparecer em verde) e *Integridade*.

## 4. Limitações conhecidas

* O componente de upload do Streamlit exibe “Upload” e “20MB per file” em
  inglês; o rótulo em português indica o limite acadêmico real (10 MB padrão).
* A duração do vídeo só é lida automaticamente com a chave gratuita da YouTube
  Data API; sem ela, o aluno declara e o avaliador confere.
* WhatsApp: a mensagem é preenchida automaticamente, mas o PDF precisa ser
  anexado manualmente (limitação do próprio WhatsApp sem API paga).
* Se o navegador bloquear cookies, a sessão dura até a aba ser fechada.
* Planos gratuitos podem mudar; veja os riscos em `REGISTRO_DE_ALTERACOES.md`.

## 5. Problemas pendentes

Nenhum defeito conhecido em aberto. Durante o desenvolvimento, as falhas
encontradas pelos testes de navegador eram dos próprios seletores do teste
(não da aplicação) e foram corrigidas; a execução final aprovou 48/48.

## 6. Capturas de tela

Capturas da execução de ponta a ponta estão em `docs/capturas/`.
