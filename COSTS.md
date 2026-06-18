# Estimări Cost Lunar — Andrei AI Agent System

Estimări bazate pe prețuri iunie 2026. Costurile reale depind de volumul de utilizare.

## Rezumat Rapid

| Nivel | Utilizare | Railway | Hostinger VPS |
|-------|-----------|---------|---------------|
| **Light** | 1 briefing/zi, 1 review/săpt. | $25–45/lună | **€12–15/lună** |
| **Medium** | Briefing + alerts + dashboard | $60–120/lună | €20–35/lună |
| **Heavy** | Utilizare intensă | $150–300/lună | €40–60/lună |

> Hostinger VPS are cost fix predictibil. Vezi [DEPLOY_HOSTINGER.md](DEPLOY_HOSTINGER.md).

---

## Detaliere pe Serviciu

### 1a. Hostinger VPS (Hosting alternativ)

| Plan | Preț | Include |
|------|------|---------|
| KVM 1 | ~€4–5/lună | 1 vCPU, 4GB RAM — suficient Light |
| KVM 2 | ~€6–8/lună | 2 vCPU, 8GB RAM — recomandat Medium |

**Estimare consum:** preț fix, fără surprize usage-based.

### 1b. Railway.app (Hosting)

| Plan | Preț | Include |
|------|------|---------|
| Hobby | $5/lună | $5 credit inclus, suficient pentru Light |
| Pro | $20/lună | $20 credit, recomandat pentru Medium/Heavy |

**Estimare consum:**
- Light: ~$3–5/lună (1 serviciu scheduler + API)
- Medium: ~$8–15/lună (scheduler + dashboard opțional)
- Heavy: ~$15–30/lună (multiple replicas, cron jobs)

> Railway facturează per resurse consumate (CPU, RAM, network). Monitorizează în Dashboard > Usage.

### 2. LLM APIs

#### Grok (xAI) — Principal
| Model | Input | Output |
|-------|-------|--------|
| grok-2-latest | ~$2/1M tokens | ~$10/1M tokens |

**Estimare lunară:**
- Light: ~$5–10 (daily briefing + weekly review)
- Medium: ~$20–40
- Heavy: ~$80–150

#### Claude 3.5 Sonnet (Fallback)
| Input | Output |
|-------|--------|
| ~$3/1M tokens | ~$15/1M tokens |

Folosit doar când Grok e indisponibil. Estimare: +$2–10/lună.

#### GPT-4o (Fallback secundar)
| Input | Output |
|-------|--------|
| ~$2.5/1M tokens | ~$10/1M tokens |

Folosit rar. Estimare: +$1–5/lună.

### 3. Supabase (Memory)

| Plan | Preț | Include |
|------|------|---------|
| Free | $0 | 500MB DB, 50K MAU |
| Pro | $25/lună | 8GB DB, backups |

**Recomandare:** Free tier suficient pentru Light/Medium. Pro pentru Heavy sau date sensibile.

### 4. Pinecone (Alternativă Memory)

| Plan | Preț |
|------|------|
| Starter | Free (1 index, 100K vectors) |
| Standard | ~$70/lună |

**Recomandare:** Supabase e mai economic. Pinecone doar dacă ai nevoie de search vectorial avansat.

### 5. Integrări Gratuite

| Serviciu | Cost |
|----------|------|
| Notion API | Gratuit |
| Google APIs (Calendar, Docs, Drive) | Gratuit (quotas generoase) |
| Telegram Bot API | Gratuit |
| Discord Webhooks | Gratuit |
| WhatsApp Cloud API | ~1000 conv/lună gratuit, apoi ~$0.05–0.15/conversație |

### 6. GitHub

| Plan | Cost |
|------|------|
| Free (public/private repo) | $0 |

---

## Scenarii Detaliate

### Light (~$25–45/lună)

```
Railway Hobby:        $5
Grok API:             $8
Supabase Free:        $0
Integrări:            $0
─────────────────────────
Total:               ~$13–25 + buffer

Cu Pro Railway:      ~$25–45
```

**Profil:** Daily briefing automat, weekly review duminică, alerte 3x/zi, ocazional query manual.

### Medium (~$60–120/lună)

```
Railway Pro:          $15
Grok API:             $30
Claude fallback:      $5
Supabase Free/Pro:    $0–25
Dashboard Streamlit:  +$5 Railway
─────────────────────────
Total:               ~$55–80

Cu buffer Heavy-light: ~$60–120
```

**Profil:** Utilizare zilnică activă, dashboard, content pipeline, multe interogări crew.

### Heavy (~$150–300/lună)

```
Railway Pro:          $25
Grok API:             $100
Fallbacks:            $15
Supabase Pro:         $25
Multiple cron jobs:   $10
─────────────────────────
Total:               ~$175

Peak usage:           ~$250–300
```

**Profil:** Echipă mică, multe agenți paraleli, analize content frecvente, memory intens.

---

## Optimizare Costuri

1. **Folosește Grok ca principal** — cel mai bun raport preț/performanță pentru acest use case
2. **Cache memory în Supabase** — evită re-procesarea aceluiași context
3. **Limitează `max_iter` agenți** — deja setat la 10–15
4. **Railway Hobby pentru start** — upgrade doar când Usage > $5
5. **Cron jobs vs always-on** — folosește Railway Cron pentru job-uri punctuale (reduce CPU idle)
6. **Monitorizează token usage** — loghează în structlog, verifică lunar

## Monitorizare

- **Railway:** Dashboard → Project → Usage → setează alert la $10, $25, $50
- **xAI:** [console.x.ai](https://console.x.ai) → Usage
- **Supabase:** Dashboard → Settings → Usage

---

*Ultima actualizare: iunie 2026. Prețurile pot varia — verifică site-urile oficiale înainte de bugetare.*