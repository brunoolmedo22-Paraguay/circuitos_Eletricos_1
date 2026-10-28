# Guia administrativo — Exercícios Resolvidos

Para o professor, o monitor e quem os suceder. Todas as funções ficam no botão
flutuante **Ações** (canto inferior direito) → **03 · Administração**, visível
somente para administradores.

## Conceitos em 1 minuto

* **Exercício Proposto** — criado pela administração; é o que o aluno escolhe resolver.
* **Submissão** — a entrega de um aluno para um exercício (uma por aluno e exercício).
* **Versão** — cada envio da submissão. Versões enviadas nunca são alteradas nem apagadas.
* **Avaliação** — decisão sobre uma versão: **Aprovada** (Excelente, Muito Bom
  ou Bom) ou **Devolvida para Correção**. Não existem notas nem pontos.
* **Publicação** — a versão aprovada aparece automaticamente na biblioteca pública.

Estados: Rascunho → Submetida → Em análise → Devolvida → Reenviada → … → Aprovada
(ou Retirada, por decisão administrativa).

---

## 1. Criar exercícios
*Administração → Gerenciar Exercícios → Novo exercício.*
Informe código (`2.04`), título, unidade, temas (separados por vírgula, usados na
busca) e enunciado. O enunciado aceita Markdown e LaTeX: `$V = R \cdot I$`.

* **Desativar** esconde o exercício de novas entregas, sem afetar as existentes.
* O **código** fica bloqueado depois da primeira entrega vinculada; título e
  enunciado continuam editáveis. Exercícios com entregas não podem ser excluídos.
* As unidades sugeridas são definidas em *Configurações*.

## 2. Adicionar estudantes
*Administração → Adicionar Usuários.*
* **Individual:** nome, login (sugestão: matrícula), matrícula, e-mail, WhatsApp.
* **Turma inteira:** baixe o modelo CSV, preencha (`nome;matricula;email;telefone`)
  e importe. Linhas duplicadas ou inválidas são listadas sem interromper a importação.
* As **senhas provisórias aparecem uma única vez**: baixe o CSV de credenciais e
  entregue cada senha em particular. No primeiro acesso o aluno define a própria senha.
* **Alternativa:** em *Configurações*, defina um **código da turma**. Os alunos
  criam a própria conta (sempre com perfil Aluno) informando o código. Deixe o
  campo vazio para desativar.

## 3. Revisar entregas
*Administração → Aprovar Resoluções* (bandeja). Mostra primeiro as entregas mais
antigas; filtre por estado, exercício, unidade, estudante, responsável e período.

1. Clique em **Avaliar** e depois em **Iniciar análise**. A partir daí:
   os materiais ficam bloqueados para o aluno e os outros administradores veem
   que você é o responsável. Se precisar parar, use **Devolver à fila**.
2. Use as abas **Vídeo** (player + link do YouTube + verificação automática e
   duração), **PDF** (pré-visualização e download), **Falstad** (abre o
   circuito exatamente como enviado), **Aluno** e **Versões e avaliações**.
3. No painel **Decisão acadêmica**, marque os três requisitos obrigatórios e
   avalie os seis critérios (Atende / Atende parcialmente / Não atende).

Se outro administrador já iniciou a análise, aparece **Assumir análise** —
use-o somente em comum acordo; a troca fica registrada.

## 4. Aprovar
Selecione **Aprovar Resolução**, escolha **Excelente, Muito Bom ou Bom**, confira
a duração do vídeo, marque a confirmação e clique **Registrar decisão**.
O sistema exige os três materiais cumpridos e nenhum critério “Não atende” —
nesses casos, devolva. A publicação na biblioteca é imediata e automática
(vídeo, PDF e Falstad já enviados); nada precisa ser publicado no YouTube.

## 5. Devolver para correção
Selecione **Devolver para Correção** e descreva os **problemas identificados**
(obrigatório), observações, recomendações e, se quiser, indicações para o
reenvio. A devolução não apaga nada: o aluno vê o parecer e prepara uma nova versão.

## 6. Pareceres em PDF e WhatsApp
Cada decisão gera automaticamente um parecer em PDF com a identidade da
disciplina, guardado junto à avaliação. Use **Pré-visualizar parecer** antes de
registrar, se quiser conferir. Depois da decisão aparecem:
* **Baixar parecer (PDF)**;
* **Compartilhar pelo WhatsApp** — abre o WhatsApp com a mensagem pronta (para o
  número do aluno, se cadastrado). O WhatsApp não permite anexar arquivos por
  link: **anexe o PDF baixado** antes de enviar.

O aluno também baixa o parecer em *Alterar Resolução*. Pareceres antigos:
*Histórico de Avaliações → Consultar um parecer*.

## 7. Publicações
*Administração → Publicações.*
* **Alterar nível** — exige justificativa; fica no histórico.
* **Retirar publicação** — exige motivo; o PDF deixa de ser público na hora. O
  aluno vê o motivo e pode enviar uma nova versão.
* **Restaurar publicação** — volta a exibir a última versão aprovada.

Quando um aluno envia nova versão de uma resolução aprovada, a versão antiga
**continua publicada** até que a nova seja aprovada.

## 8. Usuários
*Administração → Gerenciar Usuários.* Busque, edite dados, **Tornar
administrador / Revogar administração**, **Desativar / Reativar conta**, **Gerar
senha provisória** (para quem esqueceu a senha) e **Ver atividade**.
Desativar uma conta não remove as resoluções publicadas nem o histórico. O
sistema impede remover ou desativar o último administrador ativo.

## 9. Logs e auditoria
* **Log de Usuários:** logins (inclusive falhos), acessos administrativos,
  cadastros, alterações de perfil e de conta.
* **Log de Submissões:** rascunhos, envios, reenvios, início de análise,
  publicações, retiradas e alterações em exercícios.
* **Histórico de Avaliações:** avaliador, data, versão, resultado, observações e parecer.

Todos podem ser filtrados e **exportados em CSV** (abre no Excel). Senhas e
tokens nunca são registrados.

## 10. Configurações e manutenção
*Administração → Configurações:* nome da disciplina e semestre, limite do PDF,
duração recomendada do vídeo, código da turma, unidades, endereço público (usado
nas mensagens de WhatsApp), **diagnóstico** dos serviços, **verificação de
integridade** (PDFs ausentes, vídeos removidos, links inválidos, regenerar
pareceres) e **backup completo**.

Rotina sugerida: no início do semestre, confira o diagnóstico e o workflow do
GitHub; mensalmente, rode a verificação de integridade; no fim do semestre, faça
o backup.

## 11. Transferir a administração (troca de monitor ou professor)
1. Quem sai cadastra quem entra como **Administrador** e confirma o primeiro acesso.
2. Transfira também, se necessário:
   * **GitHub** — adicione a nova pessoa como colaboradora do repositório;
   * **Streamlit Cloud** — o app pertence à conta GitHub que o implantou; dê acesso
     de desenvolvedor ou transfira o repositório para uma organização da disciplina;
   * **Supabase** — *Organization → Members → Invite* (papel *Owner*).
3. Só então quem sai tem a administração revogada. Nenhuma função depende da
   conta pessoal de um administrador específico.
4. Recomendação: mantenha o projeto Supabase e o repositório numa **organização**
   da disciplina (não em contas pessoais) e guarde as credenciais de serviço com
   o professor responsável.
5. Perdeu todos os acessos de administrador? Quem tiver a URL do banco executa
   `python scripts/criar_admin.py` (veja `docs/INSTALACAO.md`, § 5).

## 12. Proteção de dados (LGPD)
* Só são coletados dados necessários: nome, matrícula, e-mail e, opcionalmente, WhatsApp.
* Ao enviar, o aluno declara a autoria e **autoriza** a publicação com seu nome
  caso aprovada. O aluno pode escolher o **nome exibido** em *Minha conta*.
* Rascunhos, entregas pendentes ou devolvidas, pareceres e dados de contato são
  visíveis apenas ao próprio aluno e à administração.
* Vídeos “não listados” tornam-se de fato públicos quando a resolução é
  publicada, pois qualquer visitante pode abrir o link.
* Pedidos de remoção: retire a publicação e, se necessário, desative a conta.
