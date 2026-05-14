# Publicação de Posts — Wagtail (bilouro.com) e LinkedIn

Guia de referência para agendar e publicar conteúdo nos dois canais. Responde também à
pergunta "há algum LaunchAgent no Mac que publica automaticamente no site?" — a resposta
curta é **não, e não é necessário**: o Wagtail trata isso no servidor.

---

## 1. Wagtail — bilouro.com

### Arquitectura dos sites

`bilouro-web` é um Wagtail multi-site em AWS Lightsail (Ubuntu):

| Sub-site | Modelo | Fonte dos posts |
|---|---|---|
| `tech.bilouro.com` | `BlogPostPage` | `~/Documents/GitHub/linkedin/knowledge-base/posts/` |
| `books.bilouro.com` | `BookPostPage` | `~/Documents/GitHub/book_jesus_lider/posts/pt/` (PT) e `book_jesus_leader/posts/en/` (EN) |
| `www.bilouro.com` | landing/CV | editado directamente no Wagtail Admin |

Calendário editorial: `~/Documents/GitHub/book_jesus_lider/posts_schedule.md`
(estados: `[~]` gerado · `[a]` agendado · `[x]` publicado)

### Como um post chega ao Wagtail

Os posts **não são escritos directamente no Wagtail**. São gerados por `BookBuilder` e
importados via linha de comando:

```bash
# Post de livro (BookPostPage)
cd ~/Documents/GitHub/BookBuilder
python main.py post <caminho/para/post.md>

# Post técnico (BlogPostPage)
python main.py tech-post <caminho/para/post.md>
```

O `BookBuilder` faz SSH para a VM, cria a página no Wagtail e define o `go_live_at`
(data de publicação futura) se o frontmatter do `.md` tiver `date:` no futuro.

### Agendamento — como funciona (sem LaunchAgent no Mac)

O Wagtail tem publicação agendada **nativa no servidor**. A VM corre um cron job
(ou middleware de request) que executa periodicamente:

```bash
# Na VM (Lightsail):
/opt/bilouro/web/.venv/bin/python /opt/bilouro/web/manage.py publish_scheduled
```

Quando o `go_live_at` de uma página chega, o Wagtail publica-a automaticamente.
**O Mac não precisa de fazer nada** — é por isso que não existe LaunchAgent para este fim.

### Verificar agendamentos futuros (a partir do Mac)

```bash
ssh -i ~/.ssh/lightsail-bilouro.pem ubuntu@3.251.103.83 \
  "sudo -u bilouro bash -c 'cd /opt/bilouro/web && \
    export \$(grep -v ^# /etc/bilouro.env | xargs) && \
    .venv/bin/python manage.py shell -c \"
from wagtail.models import Page
from django.utils import timezone
now = timezone.now()
for p in Page.objects.filter(go_live_at__gte=now).order_by(\\\"go_live_at\\\"):
    print(f\\\"{p.go_live_at.isoformat()} | {p.title} | {p.specific_class.__name__} | {p.url}\\\")
\"'"
```

> O assistente do Telegram/WhatsApp já tem este comando mapeado: basta dizer
> *"tenho algum agendamento"* ou *"que posts saem esta semana"*.

### Acesso SSH à VM

| Campo | Valor |
|---|---|
| Host | `ubuntu@3.251.103.83` |
| Key | `~/.ssh/lightsail-bilouro.pem` |
| App root | `/opt/bilouro/web` |
| Env file | `/etc/bilouro.env` |
| Venv | `/opt/bilouro/web/.venv/bin/python` |

### Publicar imediatamente (sem agendar)

No `BookBuilder`, omitir ou definir `date:` para hoje — o post fica `LIVE` assim que
o `manage.py post` corre.

Alternativa: Wagtail Admin → página → "Publish" manual.

---

## 2. LinkedIn

### Arquitectura

O LinkedIn não tem scheduling nativo via API. Existe um sistema próprio:

```
~/Library/Application Support/linkedin-scheduler/
├── linkedin_post.py   — script principal
├── token.json         — access_token + author URN (chmod 600)
├── schedule.json      — fila de posts pendentes
└── posts/             — cópias dos .md + .png (TCC-safe: launchd não lê ~/Documents/)
```

**LaunchAgent**: `com.bilouro.linkedin-scheduler` — dispara às **09:00, 13:00 e 18:00** todos os dias.

### Fluxo de publicação

1. **Escrever o post** num `.md` com frontmatter:

```markdown
---
ref: meu-slug
lang: pt
phase: tech
date: 2026-05-20
image: minha-imagem.png
---

![](minha-imagem.png)

Corpo do post para LinkedIn.

#Hashtag1 #Hashtag2
```

A imagem `.png` deve estar adjacente ao `.md` (mesmo stem, mesmo directório).

2. **Agendar**:

```bash
RT="$HOME/Library/Application Support/linkedin-scheduler"
"$RT/.venv/bin/python" "$RT/linkedin_post.py" schedule \
  /caminho/para/post.md \
  2026-05-20T09:00:00
```

3. O **LaunchAgent** acorda às 09/13/18h, corre `daily`, e publica o que tiver
   `scheduled_at <= now` e `posted_at = null`.

### Comandos do dia-a-dia

```bash
RT="$HOME/Library/Application Support/linkedin-scheduler"
PY="$RT/.venv/bin/python"

# Ver fila
"$PY" "$RT/linkedin_post.py" list

# Forçar publicação agora (sem esperar o LaunchAgent)
"$PY" "$RT/linkedin_post.py" daily

# Publicar imediatamente (bypass da fila)
"$PY" "$RT/linkedin_post.py" post-now /caminho/para/post.md

# Confirmar que o token está válido
"$PY" "$RT/linkedin_post.py" whoami

# Renovar token (~60 dias de validade)
"$PY" "$RT/linkedin_post.py" auth

# Ver logs
tail -f ~/.cache/linkedin-scheduler/launchd.out.log
```

### Credenciais

| Item | Localização |
|---|---|
| App LinkedIn | `bilouro-posts` (Developer Portal) |
| Client ID / Secret | macOS Keychain (`linkedin-client-id` / `linkedin-client-secret`) e `linkedin/.env` |
| Access token | `token.json` (runtime) + Keychain `linkedin-access-token` |
| Author URN | Keychain `linkedin-author-urn` |

> Documentação completa: `~/Documents/GitHub/linkedin/AUTO_POST.md`

---

## 3. Resumo — o que corre onde

| Canal | Quem publica | Quando | LaunchAgent no Mac? |
|---|---|---|---|
| **bilouro.com** (Wagtail) | Servidor Lightsail (cron `publish_scheduled`) | Quando `go_live_at` chega | ❌ Não necessário |
| **LinkedIn** | `linkedin_post.py daily` | 09h, 13h, 18h | ✅ `com.bilouro.linkedin-scheduler` |

O Mac só intervém no Wagtail na fase de **criação/importação** do post (via `BookBuilder`).
Depois disso, o servidor é autónomo.
