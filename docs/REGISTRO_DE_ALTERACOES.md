# Registro de alterações — versão 1.0

Implementação do sistema colaborativo de **Exercícios Resolvidos** sobre a
versão 0.5 da plataforma.

## 1. Arquivos modificados

| Arquivo | Alteração |
|---|---|
| `pages/exercicios.py` | Placeholder substituído pelo módulo completo (carrega `resolucoes.ui`). |
| `pages/ejercicios.py` | Rota legada em espanhol que exibia “Seção não encontrada”: agora redireciona para `exercicios`. |
| `pages/interactue.py` | Mesma correção: redireciona para `interaja`. |
| `utils/helpers.py` | Descrição do cartão Exercícios Resolvidos atualizada; `APP_VERSION = "1.0"`. |
| `requirements.txt` | Novas dependências gratuitas; Streamlit limitado a `<2.0` (recomendação da própria Streamlit para evitar quebras). |
| `.streamlit/config.toml` | **Novo.** Limite de upload (20 MB) e cor de destaque púrpura `#532458` nos controles (antes: vermelho padrão do Streamlit). |
| `README.md` | Atualizado. |
| `__pycache__/` | Removidos do pacote e incluídos no `.gitignore`. |

Inalterados: `app.py`, `pages/teoria.py`, `pages/interaja.py`,
`pages/formularios.py`, `components/`, `data/`, `assets/`, `styles/main.css`,
`styles/teoria.css`, `styles/interaja.css`, `styles/formularios.css`.

## 2. Arquivos novos

| Caminho | Conteúdo |
|---|---|
| `resolucoes/constants.py` | Vocabulário oficial: estados, 3 níveis, critérios, rótulos pt-BR. |
| `resolucoes/config.py` | Leitura de segredos; recusa configuração não persistente em produção. |
| `resolucoes/db.py` | Esquema relacional portátil (PostgreSQL/SQLite), RLS no PostgreSQL. |
| `resolucoes/storage.py` | PDFs: Supabase Storage, banco ou disco — mesma interface. |
| `resolucoes/security.py` | Hash scrypt, tokens de sessão, política de senha. |
| `resolucoes/validators.py` | YouTube (todos os formatos + verificação), Falstad, PDF, duração. |
| `resolucoes/parecer.py` | Gerador do parecer em PDF (ReportLab). |
| `resolucoes/backup.py` | Restauração de backup / migração de provedor. |
| `resolucoes/services/` | Regras de negócio e permissões (sem dependência do Streamlit). |
| `resolucoes/ui/` | Interface: catálogo, página da resolução, botão flutuante, área do aluno, administração. |
| `styles/exercicios.css` | Estilos do módulo usando os tokens de `main.css`. |
| `scripts/` | `preparar_supabase.py`, `criar_admin.py`, `restaurar_backup.py`, `manter_ativo.py`, `dados_demonstracao.py`. |
| `tests/` | 77 testes de serviço (pytest) + teste de navegador `e2e_navegador.py`. |
| `.github/workflows/manter-supabase-ativo.yml` | Consulta periódica para evitar pausa do Supabase. |
| `.streamlit/secrets.toml.example`, `.gitignore`, `requirements-dev.txt` | Configuração. |
| `docs/` | Instalação, guia administrativo, este registro e o relatório de testes. |

## 3. Decisões de arquitetura

1. **Supabase (PostgreSQL + Storage) como provedor padrão.** Um único provedor
   gratuito cobre banco relacional e arquivos, com região em São Paulo.
   Descartados: Firebase Storage (exige plano pago com faturamento para novos
   buckets), Google Drive via API (cotas e permissões frágeis, contrariava o
   requisito de não usar Drive), commits no GitHub (proibido), disco do
   Streamlit Cloud (efêmero).
2. **Portabilidade acima de conveniência.** O acesso ao banco usa SQLAlchemy Core
   com SQL padrão (sem recursos exclusivos do Supabase) e os PDFs passam por uma
   interface de armazenamento com três implementações. Trocar de provedor =
   trocar a URL + restaurar o backup. Não há SDK proprietário.
3. **Autenticação própria em vez do Supabase Auth/OAuth.** Contas são criadas
   pela administração (ou por código da turma), o que dispensa e-mail de
   confirmação e configuração de OAuth — mais simples de transferir entre
   monitores. Senhas com scrypt (biblioteca padrão; cada verificação é propositalmente lenta, o que dificulta ataques de força bruta), **sem bloqueio por tentativas** — decisão da coordenação para não impedir alunos de entregar; falhas ficam registradas no Log de Usuários,
   sessões com token aleatório guardado apenas como hash, perfil relido do banco
   a cada interação (revogação imediata).
4. **Sessão sobrevive a recarregar a página** via cookie (`SameSite=Lax`,
   `Secure` em HTTPS) contendo só o token; o servidor valida tudo. Sem cookie
   (navegador bloqueando), a sessão vale até fechar a aba.
5. **Permissões verificadas na camada de serviços**, não na interface. Esconder
   botões é apenas conveniência; cada operação chama `require_admin`,
   `require_student` ou checa autoria.
6. **Uma submissão por aluno e exercício; versões imutáveis.** Correções e
   melhorias geram versões novas; a publicação aponta para uma versão
   específica. Isso garante que nenhuma alteração não avaliada chegue ao catálogo.
7. **Concorrência otimista (`row_version`).** Duplo clique, duas abas ou dois
   administradores na mesma entrega produzem uma mensagem clara, nunca dados
   duplicados ou sobrescritos. A análise é “assumida” explicitamente.
8. **Ordem segura de gravação.** O arquivo é gravado primeiro; o banco só é
   alterado depois (em transação). Se o banco falhar, o arquivo é removido. Uma
   falha nunca deixa uma entrega “enviada” sem PDF.
9. **Catálogo agrupado por exercício.** Um cartão por exercício com a resolução
   de melhor nível em destaque e o selo “N resoluções”; a página da resolução
   lista as demais. Evita cartões repetidos sem perder a identidade do exercício.
10. **Avaliação qualitativa sem notas.** Três níveis oficiais apenas. A
    aprovação exige os três materiais e nenhum critério “Não atende”.
11. **Duração do vídeo.** Sem chave de API, o aluno declara e o avaliador
    confere; com chave gratuita da YouTube Data API, é lida automaticamente. O
    catálogo só exibe duração obtida da API ou conferida pelo avaliador. Acima
    do recomendado (8 min, configurável) há aviso, não bloqueio.
12. **Vídeo privado ou removido bloqueia o envio**; falha de rede com o YouTube
    não bloqueia (fica “não verificado” para o avaliador).
13. **Falstad:** o link é guardado byte a byte (os parâmetros `ctz`/`cct`
    carregam o circuito compactado). Encurtadores e links sem circuito são recusados.
14. **WhatsApp honesto:** link `wa.me` com mensagem pronta + PDF para anexar
    manualmente. Não há envio automático (exigiria API paga do WhatsApp Business).
15. **Privacidade do YouTube:** player via `youtube-nocookie.com`.
16. **Rotas legadas** em espanhol redirecionam em vez de serem apagadas, para
    não quebrar links antigos.

## 4. Serviços externos e limites do plano gratuito

Valores conferidos em outubro de 2026. Provedores podem mudar condições:
confira as páginas oficiais antes de cada semestre.

| Serviço | Uso | Limites gratuitos relevantes |
|---|---|---|
| **Supabase** (Free) | Banco + PDFs | 500 MB de banco, 1 GB de arquivos, 5 GB de tráfego/mês, 2 projetos ativos; **pausa após 7 dias sem uso** (dados preservados; reativação manual). |
| **Streamlit Community Cloud** | Hospedagem | App “dorme” após 12 h sem visitas (qualquer visitante o acorda); ~1 GB de memória garantida. |
| **GitHub** | Código + workflow de manutenção | Agendamentos de repositórios públicos são desativados após 60 dias sem atividade no repositório. |
| **YouTube oEmbed** | Verificação de vídeo | Público, sem chave; não informa duração. |
| **YouTube Data API v3** (opcional) | Duração do vídeo | 10.000 unidades/dia gratuitas; cada verificação usa 1. |

Estimativa de capacidade: o banco guarda só texto (≈ dezenas de KB por entrega).
Com PDFs de 2 MB em média, 1 GB comporta ~400–450 PDFs entre resoluções,
versões e pareceres (pareceres têm ~10 KB). O limite padrão é 10 MB por PDF
(ajustável). Monitore em *Supabase → Project → Usage*.

## 5. Riscos operacionais

1. **Pausa do Supabase** em férias — mitigado pelo workflow; procedimento de
   reativação no guia de instalação.
2. **Mudança de condições dos provedores** — mitigado pela portabilidade e pelo
   backup completo; faça backup a cada semestre.
3. **Perda de acesso às contas de serviço** quando o monitor sair — mantenha
   Supabase, Streamlit e GitHub em organização da disciplina (guia § 11).
4. **Vídeos removidos pelos alunos** após a publicação — detectados pela
   verificação de integridade; o visitante vê aviso e o link continua disponível.
5. **Cota de 1 GB de arquivos** — acompanhe o uso; reduza o limite do PDF ou
   migre versões antigas se necessário.
6. **O backup contém dados pessoais** — armazene em local privado.
7. **Quem possui a URL do banco tem controle total** — trate-a como senha; troque
   a senha do banco no Supabase se houver suspeita de vazamento.

---

## v1.0.1 — ajustes após o primeiro uso

* **Removido o bloqueio por excesso de tentativas de login.** O aluno pode
  tentar a senha quantas vezes precisar; cada falha continua registrada no Log
  de Usuários. Contas que estavam bloqueadas são liberadas automaticamente.
* **Tema claro fixo** (`.streamlit/config.toml`) com a paleta da plataforma.
  Antes, em computadores e celulares com o sistema em modo escuro, os campos de
  texto apareciam com fundo preto. Campos, seletores, datas e upload agora são
  brancos com borda lilás e foco púrpura, em todas as páginas.
* **Telas Entrar, Configuração inicial e Criar conta** ganharam os botões
  “← Voltar à biblioteca” e “Início da plataforma”.
