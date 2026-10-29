# Instalação, implantação e manutenção

Guia para quem instala a plataforma pela primeira vez **e** para quem herda a
administração nos próximos semestres. Não é preciso conhecer o código.

> Custo: **US$ 0**. Todos os serviços abaixo têm plano gratuito sem cartão de
> crédito. Os limites e riscos estão em `docs/REGISTRO_DE_ALTERACOES.md` (§ 4).

---

## 1. Visão geral da arquitetura

```
Navegador ──► Streamlit Community Cloud (código vindo do GitHub)
                 │
                 ├──► Supabase PostgreSQL  (usuários, exercícios, entregas,
                 │                          versões, avaliações, logs)
                 ├──► Supabase Storage     (PDFs das resoluções e pareceres,
                 │                          bucket PRIVADO)
                 └──► YouTube (somente leitura: verificação do link e miniatura)
```

* **Vídeos** ficam no canal do próprio aluno. A plataforma guarda só o link.
* **Nada dos alunos vai para o GitHub.** O repositório contém apenas código.
* O servidor do Streamlit pode reiniciar à vontade: nenhum dado fica nele.

---

## 2. Executar localmente

Requisitos: Python 3.10 ou superior.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sem configuração, as páginas Teoria, Interaja e Formulários funcionam
normalmente e o módulo Exercícios Resolvidos exibe “Configuração pendente”
(ele **não** aceita entregas sem armazenamento persistente).

### 2.1 Modo demonstração (sem nenhum serviço externo)

Para conhecer o sistema ou testar alterações:

```bash
# Linux/macOS
export CE1_MODE=demonstracao CE1_DATABASE_URL=sqlite:///.dados_locais/demo.db \
       CE1_STORAGE_BACKEND=local CE1_LOCAL_STORAGE_DIR=.dados_locais/arquivos
mkdir -p .dados_locais
python scripts/dados_demonstracao.py      # cria exercícios, alunos e resoluções de exemplo
streamlit run app.py
```

No Windows (PowerShell), troque `export X=Y` por `$env:X="Y"`.

Credenciais de demonstração: `monitor` / `Monitor2026` (administrador),
`ana` / `Aluno2026` (aluna). Uma faixa laranja “Modo demonstração” fica visível
em todas as telas. Os dados de demonstração ficam em `.dados_locais/` (ignorada
pelo Git) e **nunca** se misturam com produção.

---

## 3. Configurar o Supabase (banco + armazenamento de PDFs)

1. Crie uma conta gratuita em <https://supabase.com> (login com GitHub serve).
2. **New project** → nome `circuitos-eletricos-1`, região **South America (São
   Paulo)**, defina e **guarde** a senha do banco.
3. **URL do banco:** botão **Connect** (topo da página) → aba *Connection
   string* → escolha **Session pooler**. Copie a URL e substitua
   `[YOUR-PASSWORD]` pela senha do passo 2. Ela tem o formato
   `postgresql://postgres.<projeto>:<senha>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres`.
   *Use o Session pooler:* a conexão direta usa IPv6, que o Streamlit Cloud não suporta.
4. **URL do projeto:** *Project Settings → Data API* → `https://<projeto>.supabase.co`.
5. **Chave secreta:** *Project Settings → API Keys* → copie uma **Secret key**
   (`sb_secret_…`). Projetos antigos podem usar a chave legada `service_role`;
   ambas funcionam. **Nunca** use a chave *publishable/anon* aqui e nunca
   publique a chave secreta.
6. Preencha `.streamlit/secrets.toml` (copie de `.streamlit/secrets.toml.example`).
7. Prepare o projeto (cria as tabelas, ativa RLS e cria o bucket privado):

   ```bash
   python scripts/preparar_supabase.py
   ```

   Alternativa sem terminal: no painel do Supabase, *Storage → New bucket* →
   nome `resolucoes`, **Public bucket desligado**. As tabelas são criadas
   automaticamente no primeiro acesso ao app.

### Segurança aplicada automaticamente
* Bucket **privado**: nenhum PDF tem URL pública; todo download passa pelas
  regras de permissão da aplicação.
* **Row Level Security** ativado em todas as tabelas `ce1_*`: a API REST
  automática do Supabase não consegue ler os dados com a chave pública.

---

## 4. Implantar no Streamlit Community Cloud

1. Envie o repositório ao GitHub (sem `secrets.toml`, já ignorado pelo `.gitignore`).
2. Em <https://share.streamlit.io> → **Create app** → repositório, branch
   `main`, arquivo principal `app.py`.
3. **Advanced settings → Secrets**: cole o conteúdo do seu `secrets.toml`.
4. **Deploy**. Atualizações futuras: basta fazer *push* no GitHub; o app se
   reimplanta sozinho e os dados permanecem no Supabase.

Para alterar segredos depois: *App → Settings → Secrets* (o app reinicia).

---

## 5. Cadastrar os dois administradores iniciais

Recomendado — pela própria interface:

1. Defina `[auth] bootstrap_token` nos segredos com um valor aleatório longo
   (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).
2. Abra *Exercícios Resolvidos → Entrar → Configuração inicial da plataforma*.
   Informe o token e os dados do **monitor**. Esse botão só aparece enquanto
   não existir nenhum administrador e exige o token.
3. Já como administrador: *Administração → Adicionar Usuários* → cadastre o
   **professor(a)** com perfil **Administrador**. A senha provisória aparece
   uma única vez (há botão para baixar em CSV); entregue-a em particular. No
   primeiro acesso a troca é obrigatória.
4. Opcional: apague `bootstrap_token` dos segredos.

Alternativa por terminal (útil também para **recuperar acesso**):

```bash
python scripts/criar_admin.py                    # cria administrador
python scripts/criar_admin.py --redefinir LOGIN  # senha provisória (e reativa a conta)
```

O script lê `.streamlit/secrets.toml` ou as variáveis `CE1_*`. Quem tem a URL do
banco tem controle total — guarde-a como uma senha.

---

## 6. Verificação de vídeos (opcional e gratuita)

Sem configuração, a plataforma consulta o **oEmbed** público do YouTube: detecta
vídeos privados, removidos ou com incorporação desativada, mas não informa a
duração (o aluno declara, o avaliador confere).

Com uma chave gratuita da **YouTube Data API v3** a duração é lida
automaticamente:
Google Cloud Console → novo projeto → *APIs e serviços → Biblioteca* →
*YouTube Data API v3* → Ativar → *Credenciais → Criar chave de API* →
restrinja a chave a essa API → cole em `[youtube] api_key`. Não exige
faturamento; cada verificação consome 1 unidade da cota diária gratuita.

---

## 7. Evitar a pausa do Supabase nas férias

Projetos gratuitos são pausados após 7 dias sem uso. Duas proteções:

* **Workflow incluído** `.github/workflows/manter-supabase-ativo.yml`: faz uma
  consulta de leitura a cada 3 dias. Ative em *GitHub → Settings → Secrets and
  variables → Actions → New repository secret*: `CE1_DATABASE_URL` (mesma URL
  do banco). Ele não grava nada. Atenção: o GitHub desativa agendamentos de
  repositórios **públicos** sem atividade por 60 dias — confira a aba *Actions*
  no início de cada semestre.
* **Se pausar mesmo assim**: o app mostra “Não foi possível conectar ao banco de
  dados”. No painel do Supabase, abra o projeto e clique em **Restore project**.
  Os dados não são perdidos na pausa.

---

## 7.1 Conteúdo incluído no repositório

Os exercícios e figuras das Listas 03 e 04 ficam em `conteudo/pacotes/` e são
cadastrados automaticamente na primeira inicialização após o deploy — não é
preciso subir imagens. Se o repositório for público, as figuras do livro ficam
visíveis no GitHub; o Streamlit Community Cloud também implanta repositórios
privados. Se o bucket do Supabase foi criado com restrição de tipos de arquivo,
inclua `image/png` e `image/jpeg` para anexar figuras novas pelo painel.

## 8. Backup e recuperação

* **Backup completo**: *Administração → Configurações → Backup → Gerar backup*.
  O ZIP contém todas as tabelas (JSON) e todos os PDFs. Faça ao fim de cada
  semestre e guarde em local **privado** (Drive institucional) — contém dados
  pessoais e entregas não publicadas. Nunca suba para o GitHub.
* **Restaurar / migrar de provedor**: configure os segredos do **novo** banco e
  armazenamento (vazios) e execute
  `python scripts/restaurar_backup.py backup_ce1_AAAAMMDD_HHMM.zip`.
* **Migrar para outro PostgreSQL** (Neon, servidor da UNILA…): basta trocar
  `[database] url`. Sem Supabase Storage, use `[storage] backend = "database"`
  (PDFs no próprio banco) ou um servidor com disco persistente
  (`backend = "local"` + `[app] allow_local_persistence = true`).
* **Integridade**: *Configurações → Integridade → Executar verificação* lista
  PDFs/pareceres ausentes, links inválidos e vídeos que deixaram de existir, e
  permite regenerar pareceres.

---

## 9. Atualizar o código

1. Faça as alterações em um *branch*, rode os testes:
   ```bash
   pip install -r requirements-dev.txt
   pytest                                  # testes de serviço (SQLite)
   CE1_TEST_PG_URL=postgresql+psycopg2://usuario:senha@localhost/teste pytest   # opcional
   playwright install chromium && python tests/e2e_navegador.py               # navegador
   ```
2. *Merge* em `main` → o Streamlit Cloud reimplanta. O esquema do banco é
   criado/atualizado de forma não destrutiva na inicialização.
3. Faça um backup antes de qualquer mudança no esquema (`resolucoes/db.py`).

---

## 10. Referência de configuração

| Chave (`secrets.toml`)            | Variável de ambiente          | Padrão        |
|-----------------------------------|-------------------------------|---------------|
| `[app] mode`                      | `CE1_MODE`                    | `producao`    |
| `[app] allow_local_persistence`   | `CE1_ALLOW_LOCAL_PERSISTENCE` | `false`       |
| `[database] url`                  | `CE1_DATABASE_URL`            | —             |
| `[storage] backend`               | `CE1_STORAGE_BACKEND`         | `supabase`    |
| `[storage] supabase_url`          | `CE1_SUPABASE_URL`            | —             |
| `[storage] supabase_key`          | `CE1_SUPABASE_KEY`            | —             |
| `[storage] bucket`                | `CE1_STORAGE_BUCKET`          | `resolucoes`  |
| `[storage] local_dir`             | `CE1_LOCAL_STORAGE_DIR`       | `.dados_locais/arquivos` |
| `[auth] bootstrap_token`          | `CE1_BOOTSTRAP_TOKEN`         | —             |
| `[auth] session_hours`            | `CE1_SESSION_HOURS`           | `12`          |
| `[youtube] api_key`               | `CE1_YOUTUBE_API_KEY`         | —             |
| `[youtube] check_online`          | `CE1_CHECK_VIDEO_ONLINE`      | `true`        |
| `[app] import_packs`              | `CE1_IMPORT_PACKS`            | `true` (importa os pacotes de `conteudo/pacotes/` na inicialização) |

Parâmetros acadêmicos (limite do PDF, duração recomendada, unidades, código da
turma para autocadastro, endereço público) ficam no banco e são alterados em
*Administração → Configurações*, sem mexer no código.
