# Stipendiya Platform — To'liq Arxitektura Hujjati

> **Stack:** FastAPI · Next.js 14 · PostgreSQL · Redis · FastMCP · Celery  
> **Rollar:** Admin · Hakim (Jury) · Student  
> **Versiya:** 1.0.0

---

## Mundarija

1. [Loyiha haqida](#1-loyiha-haqida)
2. [Rollar va vakolatlar](#2-rollar-va-vakolatlar)
3. [Tizim arxitekturasi](#3-tizim-arxitekturasi)
4. [Ma'lumotlar bazasi sxemasi](#4-malumotlar-bazasi-sxemasi)
5. [API endpointlar](#5-api-endpointlar)
6. [AI / FastMCP qatlami](#6-ai--fastmcp-qatlami)
7. [Frontend arxitekturasi](#7-frontend-arxitekturasi)
8. [Fayl tuzilmasi](#8-fayl-tuzilmasi)
9. [Muhit o'zgaruvchilari](#9-muhit-ozgaruvchilari)
10. [Deployment](#10-deployment)
11. [Ishlab chiqish bosqichlari](#11-ishlab-chiqish-bosqichlari)

---

## 1. Loyiha haqida

Universitet ichki stipendiyalarini raqamlashtiruvchi platforma. E'lon qilishdan tortib ariza topshirish, baholash va g'oliblarni aniqlashgacha bo'lgan jarayonni yagona tizimda boshqaradi.

### Asosiy xususiyatlar

- Admin stipendiya yaratadi va nizomni yuklaydi → **AI avtomatik baholash ustunlarini taklif qiladi**
- Har bir ustun uchun `ai_analyze` flag — student yuklagan ma'lumotlar AI tomonidan tahlil qilinadi
- Hakamlar balllar qo'yib, yakuniy tahlil yozadi (qo'lda yoki AI yordamida)
- Student o'z natijasi va hakim tahlilini kuzatib boradi
- **FastMCP** orqali Claude, GPT-4, Gemini, Ollama — istalgan LLM bilan ishlaydi

---

## 2. Rollar va vakolatlar

### 2.1 Admin

| Vazifa | Tavsif |
|--------|--------|
| Stipendiya yaratish | Sarlavha, tavsif, muddат, g'oliblar soni |
| Nizom yuklash | PDF yuklash → AI ustunlar taklif qiladi |
| Ustunlar boshqarish | Qo'shish, o'chirish, tartib o'zgartirish, `ai_analyze` belgilash |
| Hakamlar biriktirish | Bir stipendiyaga bir nechta hakim |
| Holat boshqarish | `draft → open → closed → done` |
| G'oliblarni tasdiqlash | Yakuniy ro'yxatni tasdiqlash |

### 2.2 Hakim (Jury)

| Vazifa | Tavsif |
|--------|--------|
| Arizalarni ko'rish | Faqat biriktirilgan stipendiyalar |
| Baholash | Har bir ustun bo'yicha ball qo'yish |
| AI xulosasini ko'rish | `ai_analyze = true` bo'lgan ustunlar uchun |
| Tahlil yozish | Qo'lda yoki `generate_review` tool orqali |
| Natijani chiqarish | Ball + tahlil → studentga ko'rinadi |

### 2.3 Student

| Vazifa | Tavsif |
|--------|--------|
| Ochiq stipendiyalarga ariza topshirish | Dinamik form (admin belgilagan ustunlar) |
| Ilmiy rahbar tanlash | Tizimda ro'yxatdagi o'qituvchilar orasidan |
| Portfel yuklash | Stipendiya yopiq bo'lsa ham yutuqlar yuklanadi |
| Natijani kuzatish | Ball va hakim tahliliga kirish |

---

## 3. Tizim arxitekturasi

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│   Admin Panel (Next.js)  │  Hakim Panel  │  Student Portal      │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS / JWT
┌───────────────────────────────▼─────────────────────────────────┐
│                      FASTAPI GATEWAY                            │
│         JWT Auth · Role Guard · Rate Limit · CORS               │
└──────┬──────────────┬────────────────┬──────────────┬───────────┘
       │              │                │              │
┌──────▼──┐    ┌──────▼──┐    ┌────────▼──┐   ┌──────▼──────┐
│  Auth   │    │Stipend. │    │  Ariza    │   │  Baholash   │
│ Service │    │ Service │    │  Service  │   │  Service    │
└─────────┘    └────┬────┘    └─────┬─────┘   └──────┬──────┘
                    │               │                 │
              ┌─────▼───────────────▼─────────────────▼──────┐
              │            FastMCP AI Layer                    │
              │  parse_nizom · suggest_columns                 │
              │  analyze_application · generate_review         │
              │                                                │
              │  FastMCP Server → Claude / GPT-4 / Gemini /   │
              │                   Ollama (ixtiyoriy)           │
              └────────────────────┬───────────────────────────┘
                                   │ async (Celery)
┌──────────────────────────────────▼───────────────────────────────┐
│                          DATA LAYER                               │
│  PostgreSQL (asosiy)  │  Redis (cache/session)  │  MinIO/S3       │
│  Celery + Redis (task queue)                                      │
└───────────────────────────────────────────────────────────────────┘
```

---

## 4. Ma'lumotlar bazasi sxemasi

### 4.1 `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'jury', 'student')),
    department      VARCHAR(100),
    student_id      VARCHAR(50),              -- Talabalar uchun
    is_supervisor   BOOLEAN DEFAULT FALSE,    -- Ilmiy rahbar bo'la oladimi
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

### 4.2 `scholarships`

```sql
CREATE TABLE scholarships (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by           UUID NOT NULL REFERENCES users(id),
    title                VARCHAR(300) NOT NULL,
    description          TEXT,
    nizom_file_url       TEXT,                -- MinIO/S3 path
    status               VARCHAR(20) DEFAULT 'draft'
                         CHECK (status IN ('draft','open','closed','done')),
    deadline             TIMESTAMP,
    ai_analysis_enabled  BOOLEAN DEFAULT FALSE,  -- Global AI switch
    max_winners          INTEGER DEFAULT 1,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);
```

### 4.3 `scholarship_columns` ⭐ (Asosiy jadval)

```sql
CREATE TABLE scholarship_columns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_id  UUID NOT NULL REFERENCES scholarships(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    field_type      VARCHAR(20) NOT NULL
                    CHECK (field_type IN ('text','textarea','file','number','date','select','url')),
    select_options  JSONB,          -- field_type='select' bo'lganda: ["A'lo","Yaxshi","Qoniqarli"]
    is_required     BOOLEAN DEFAULT TRUE,
    ai_analyze      BOOLEAN DEFAULT FALSE,  -- Bu ustun uchun AI tahlil
    max_score       INTEGER DEFAULT 10,     -- Hakim bu ustun uchun max ball
    order_index     INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 4.4 `jury_assignments`

```sql
CREATE TABLE jury_assignments (
    scholarship_id  UUID NOT NULL REFERENCES scholarships(id) ON DELETE CASCADE,
    jury_id         UUID NOT NULL REFERENCES users(id),
    assigned_at     TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (scholarship_id, jury_id)
);
```

### 4.5 `applications`

```sql
CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_id  UUID NOT NULL REFERENCES scholarships(id),
    student_id      UUID NOT NULL REFERENCES users(id),
    supervisor_id   UUID REFERENCES users(id),   -- Ilmiy rahbar (ixtiyoriy)
    status          VARCHAR(20) DEFAULT 'draft'
                    CHECK (status IN ('draft','submitted','in_review','winner','rejected')),
    submitted_at    TIMESTAMP,
    ai_summary      TEXT,           -- Butun ariza bo'yicha AI umumiy xulosa
    total_score     DECIMAL(6,2),   -- Hamma hakamlar o'rtacha bali
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (scholarship_id, student_id)  -- Bir student bir marta topshiradi
);
```

### 4.6 `application_values`

```sql
CREATE TABLE application_values (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    column_id       UUID NOT NULL REFERENCES scholarship_columns(id),
    value_text      TEXT,           -- Matn/raqam/sana qiymatlari
    value_file_url  TEXT,           -- Fayl yuklangan bo'lsa MinIO path
    ai_analysis     TEXT,           -- ai_analyze=true bo'lganda AI xulosa
    ai_score        DECIMAL(4,1),   -- AI taklif qilgan ball (ixtiyoriy)
    analyzed_at     TIMESTAMP,
    UNIQUE (application_id, column_id)
);
```

### 4.7 `evaluations`

```sql
CREATE TABLE evaluations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id),
    jury_id         UUID NOT NULL REFERENCES users(id),
    scores          JSONB NOT NULL DEFAULT '{}',
                    -- Format: {"<column_id>": 8, "<column_id>": 7}
    total_score     DECIMAL(6,2),
    final_comment   TEXT,           -- Yakuniy tahlil matni
    ai_generated    BOOLEAN DEFAULT FALSE,  -- AI yozdimi yoki qo'ldami
    is_submitted    BOOLEAN DEFAULT FALSE,
    submitted_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (application_id, jury_id)
);
```

### 4.8 `student_achievements`

```sql
CREATE TABLE student_achievements (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(300) NOT NULL,
    type        VARCHAR(30) CHECK (type IN ('paper','award','project','cert','olympiad','other')),
    file_url    TEXT,
    date        DATE,
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### 4.9 `ai_jobs`

```sql
CREATE TABLE ai_jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type    VARCHAR(50) NOT NULL
                CHECK (job_type IN ('column_gen','app_analysis','review_gen')),
    ref_id      UUID NOT NULL,         -- scholarship_id yoki application_id
    model_used  VARCHAR(100),          -- 'claude-3-5-sonnet', 'gpt-4o', ...
    status      VARCHAR(20) DEFAULT 'pending'
                CHECK (status IN ('pending','running','done','failed')),
    input_data  JSONB,
    result      JSONB,
    error_msg   TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP
);
```

### Indekslar

```sql
-- Performance uchun muhim indekslar
CREATE INDEX idx_applications_scholarship ON applications(scholarship_id);
CREATE INDEX idx_applications_student ON applications(student_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_evaluations_application ON evaluations(application_id);
CREATE INDEX idx_evaluations_jury ON evaluations(jury_id);
CREATE INDEX idx_app_values_application ON application_values(application_id);
CREATE INDEX idx_columns_scholarship ON scholarship_columns(scholarship_id);
CREATE INDEX idx_ai_jobs_status ON ai_jobs(status);
CREATE INDEX idx_achievements_student ON student_achievements(student_id);
```

---

## 5. API Endpointlar

### 5.1 Auth

```
POST   /api/v1/auth/register          # Ro'yxatdan o'tish
POST   /api/v1/auth/login             # Kirish → JWT access + refresh token
POST   /api/v1/auth/refresh           # Token yangilash
POST   /api/v1/auth/logout            # Chiqish
GET    /api/v1/auth/me                # Joriy foydalanuvchi ma'lumotlari
PATCH  /api/v1/auth/me                # Profil yangilash
```

### 5.2 Stipendiyalar (Admin)

```
GET    /api/v1/scholarships                      # Ro'yxat (filter: status, search)
POST   /api/v1/scholarships                      # Yangi yaratish
GET    /api/v1/scholarships/{id}                 # Batafsil
PATCH  /api/v1/scholarships/{id}                 # Tahrirlash
DELETE /api/v1/scholarships/{id}                 # O'chirish (faqat draft)
PATCH  /api/v1/scholarships/{id}/status          # Holat o'zgartirish

# Nizom va AI ustunlar
POST   /api/v1/scholarships/{id}/upload-nizom    # PDF yuklash
POST   /api/v1/scholarships/{id}/generate-columns# AI ustunlar taklif (nizomdan)

# Ustunlar CRUD
GET    /api/v1/scholarships/{id}/columns         # Ustunlar ro'yxati
POST   /api/v1/scholarships/{id}/columns         # Ustun qo'shish
PATCH  /api/v1/scholarships/{id}/columns/{col_id}# Ustun tahrirlash
DELETE /api/v1/scholarships/{id}/columns/{col_id}# Ustun o'chirish
PATCH  /api/v1/scholarships/{id}/columns/reorder # Tartib o'zgartirish

# Hakamlar
GET    /api/v1/scholarships/{id}/jury            # Biriktirilgan hakamlar
POST   /api/v1/scholarships/{id}/jury            # Hakim biriktirish
DELETE /api/v1/scholarships/{id}/jury/{jury_id}  # Hakim olib tashlash
```

### 5.3 Arizalar

```
# Student uchun
GET    /api/v1/scholarships/{id}/apply           # Ariza formi (ustunlar bilan)
POST   /api/v1/scholarships/{id}/apply           # Yangi ariza (draft)
PATCH  /api/v1/applications/{id}                 # Qoralama yangilash
POST   /api/v1/applications/{id}/submit          # Topshirish
GET    /api/v1/applications/my                   # Mening arizalarim

# Fayl yuklash
POST   /api/v1/applications/{id}/values/{col_id}/upload # Ustun uchun fayl

# Hakim uchun
GET    /api/v1/jury/applications                 # Ko'rishi kerak bo'lgan arizalar
GET    /api/v1/jury/applications/{id}            # Ariza batafsil + AI xulosalar

# Admin uchun
GET    /api/v1/scholarships/{id}/applications    # Barcha arizalar (filter, sort)
PATCH  /api/v1/applications/{id}/status          # Holat o'zgartirish
POST   /api/v1/scholarships/{id}/announce-winners# G'oliblarni e'lon qilish
```

### 5.4 Baholash

```
GET    /api/v1/evaluations/{application_id}          # Mening baholashim
POST   /api/v1/evaluations/{application_id}          # Baholash boshlash
PATCH  /api/v1/evaluations/{application_id}          # Ball/tahlil yangilash
POST   /api/v1/evaluations/{application_id}/submit   # Yakuniy topshirish
POST   /api/v1/evaluations/{application_id}/ai-review# AI tahlil generatsiya
```

### 5.5 Yutuqlar (Portfel)

```
GET    /api/v1/achievements                  # Mening yutuqlarim
POST   /api/v1/achievements                  # Yangi qo'shish
PATCH  /api/v1/achievements/{id}             # Tahrirlash
DELETE /api/v1/achievements/{id}             # O'chirish
POST   /api/v1/achievements/{id}/upload      # Fayl biriktirish
```

### 5.6 Foydalanuvchilar (Admin)

```
GET    /api/v1/users                         # Ro'yxat (filter: role)
POST   /api/v1/users                         # Yangi yaratish
PATCH  /api/v1/users/{id}                    # Tahrirlash
PATCH  /api/v1/users/{id}/toggle-active      # Faollashtirish/bloklash
GET    /api/v1/users/supervisors             # Ilmiy rahbarlar ro'yxati
```

### 5.7 AI Jobs

```
GET    /api/v1/ai-jobs/{ref_id}             # Biror stipendiya/ariza AI ishlari
GET    /api/v1/ai-jobs/{id}/status          # Ishning holati (polling)
```

---

## 6. AI / FastMCP qatlami

### 6.1 FastMCP Server sozlash

```python
# mcp/server.py
from fastmcp import FastMCP

mcp = FastMCP("stipendiya-ai")

# Tool'larni ro'yxatdan o'tkazish
from mcp.tools.parse_nizom import parse_nizom_tool
from mcp.tools.suggest_columns import suggest_columns_tool
from mcp.tools.analyze_application import analyze_application_tool
from mcp.tools.generate_review import generate_review_tool

mcp.add_tool(parse_nizom_tool)
mcp.add_tool(suggest_columns_tool)
mcp.add_tool(analyze_application_tool)
mcp.add_tool(generate_review_tool)
```

### 6.2 Tool 1: `parse_nizom`

**Qachon ishlatiladi:** Admin PDF nizom yuklaganda  
**Kirish:** PDF fayl binary yoki URL  
**Chiqish:** Stipendiya maqsadi, talablar, baholash mezonlari — tuzilgan matn

```python
@mcp.tool()
async def parse_nizom(file_url: str) -> dict:
    """
    Stipendiya nizomidan asosiy ma'lumotlarni ajratib oladi.
    
    Returns:
        {
            "title": "...",
            "purpose": "...",
            "requirements": ["...", "..."],
            "evaluation_criteria": ["...", "..."],
            "raw_text": "..."
        }
    """
```

### 6.3 Tool 2: `suggest_columns`

**Qachon ishlatiladi:** Nizom parse qilingandan keyin, admin ustunlar yaratishda  
**Kirish:** Nizom matni (parse_nizom chiqishi)  
**Chiqish:** Tavsiya etilgan ustunlar ro'yxati

```python
@mcp.tool()
async def suggest_columns(nizom_text: str, scholarship_title: str) -> dict:
    """
    Nizom asosida ariza ustunlarini taklif qiladi.
    
    Returns:
        {
            "columns": [
                {
                    "name": "GPA (o'rtacha ball)",
                    "description": "...",
                    "field_type": "number",
                    "is_required": true,
                    "ai_analyze": false,
                    "max_score": 30
                },
                {
                    "name": "Ilmiy maqolalar",
                    "description": "...",
                    "field_type": "file",
                    "is_required": false,
                    "ai_analyze": true,
                    "max_score": 40
                }
            ]
        }
    """
```

### 6.4 Tool 3: `analyze_application`

**Qachon ishlatiladi:** Student ariza topshirgandan keyin, `ai_analyze=true` ustunlar uchun  
**Kirish:** Ustun tavsifi + student yuklagan ma'lumot  
**Chiqish:** Har bir ustun uchun batafsil AI tahlil

```python
@mcp.tool()
async def analyze_application(
    column_name: str,
    column_description: str,
    student_value: str,
    max_score: int,
    scholarship_context: str
) -> dict:
    """
    Student ma'lumotini ustun bo'yicha AI tahlil qiladi.
    
    Returns:
        {
            "analysis": "Student tomonidan taqdim etilgan...",
            "suggested_score": 8.5,
            "strengths": ["...", "..."],
            "weaknesses": ["..."],
            "recommendation": "..."
        }
    """
```

### 6.5 Tool 4: `generate_review`

**Qachon ishlatiladi:** Hakim "AI bilan tahlil yoz" tugmasini bosganda  
**Kirish:** Barcha balllar, AI xulosalar, hakim izohlari  
**Chiqish:** Professional yakuniy tahlil matni

```python
@mcp.tool()
async def generate_review(
    student_name: str,
    scholarship_title: str,
    scores: dict,          # {column_name: score}
    ai_analyses: list,     # analyze_application natijalari
    jury_notes: str        # Hakim qo'lda yozgan izohlari
) -> dict:
    """
    Yakuniy hakim tahlilini generatsiya qiladi.
    
    Returns:
        {
            "review_text": "Hurmatli ..., sizning arizangiz...",
            "summary": "...",
            "total_score": 87.5
        }
    """
```

### 6.6 LLM konfiguratsiya (multi-model)

```python
# core/llm_config.py
from enum import Enum

class LLMProvider(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"

LLM_CONFIGS = {
    LLMProvider.CLAUDE: {
        "model": "claude-3-5-sonnet-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    LLMProvider.OPENAI: {
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
    },
    LLMProvider.GEMINI: {
        "model": "gemini-1.5-pro",
        "api_key_env": "GOOGLE_API_KEY",
    },
    LLMProvider.OLLAMA: {
        "model": "llama3.1",
        "base_url": "http://localhost:11434",
    },
}

# .env da: DEFAULT_LLM_PROVIDER=claude
```

### 6.7 Async AI vazifalar (Celery)

```python
# workers/tasks.py

@celery_app.task(bind=True, max_retries=3)
def run_application_analysis(self, application_id: str):
    """
    Student ariza topshirgandan keyin avtomatik ishga tushadi.
    ai_analyze=True bo'lgan barcha ustunlar uchun tahlil qiladi.
    """
    ...

@celery_app.task
def run_column_generation(scholarship_id: str, nizom_text: str):
    """
    Nizom yuklangandan keyin ustunlar taklif qiladi.
    """
    ...
```

---

## 7. Frontend arxitekturasi

### 7.1 Next.js App Router tuzilmasi

```
app/
├── (auth)/
│   ├── login/page.tsx
│   └── register/page.tsx
│
├── (admin)/
│   ├── layout.tsx                   # Admin sidebar layout
│   ├── dashboard/page.tsx           # Statistika
│   ├── scholarships/
│   │   ├── page.tsx                 # Ro'yxat
│   │   ├── new/page.tsx             # Yangi yaratish
│   │   └── [id]/
│   │       ├── page.tsx             # Batafsil + tahrirlash
│   │       ├── columns/page.tsx     # Ustunlar boshqarish
│   │       ├── jury/page.tsx        # Hakamlar boshqarish
│   │       └── applications/page.tsx# Arizalar ro'yxati
│   └── users/page.tsx               # Foydalanuvchilar
│
├── (jury)/
│   ├── layout.tsx
│   ├── dashboard/page.tsx
│   └── applications/
│       ├── page.tsx                 # Ko'rish kerak bo'lgan arizalar
│       └── [id]/page.tsx            # Baholash sahifasi
│
└── (student)/
    ├── layout.tsx
    ├── dashboard/page.tsx
    ├── scholarships/
    │   ├── page.tsx                 # Ochiq stipendiyalar
    │   └── [id]/
    │       ├── page.tsx             # Stipendiya haqida
    │       └── apply/page.tsx       # Ariza topshirish
    ├── applications/page.tsx        # Mening arizalarim + natijalar
    └── achievements/page.tsx        # Portfel
```

### 7.2 Muhim komponentlar

#### `DynamicForm.tsx` — eng murakkab komponent

```tsx
// Scholarship columns asosida dinamik form render qiladi
interface DynamicFormProps {
  columns: ScholarshipColumn[]
  onSubmit: (values: ApplicationValue[]) => void
  mode: 'create' | 'edit'
}

// field_type ga qarab render:
// 'text'     → <Input>
// 'textarea' → <Textarea>
// 'number'   → <NumberInput min/max>
// 'file'     → <FileUpload> (drag & drop, progress bar)
// 'date'     → <DatePicker>
// 'select'   → <Select> (select_options dan)
// 'url'      → <UrlInput> (validatsiya bilan)
```

#### `ColumnBuilder.tsx` — Admin ustun quruvchi

```tsx
// Drag-and-drop ustun tartibini o'zgartirish
// Har bir ustun uchun:
//   - Nom, tavsif, field_type
//   - is_required toggle
//   - ai_analyze checkbox ⭐
//   - max_score input
// AI taklif qilingan ustunlarni import qilish tugmasi
```

#### `ScoringPanel.tsx` — Hakim baholash paneli

```tsx
// Har bir ustun uchun:
//   - Slider yoki number input (0 → max_score)
//   - AI analiz accordion (ai_analyze=true bo'lganda)
//   - Hakim izohi maydoni
// Yon panel:
//   - Umumiy ball hisob-kitobi
//   - "AI bilan tahlil yozish" tugmasi
//   - "Yuborish" tugmasi
```

#### `AIReviewEditor.tsx`

```tsx
// generate_review API ga so'rov yuboradi
// Loading state (streaming yoki polling)
// AI generated matnni tahrirlash imkoni
// Hakim tasdiqlaydi → evaluations ga saqlaydi
```

#### `NizomUploader.tsx`

```tsx
// 1. PDF yuklash (drag & drop)
// 2. parse_nizom → loading
// 3. suggest_columns → natijani ko'rsatish
// 4. Admin har bir ustunni tasdiqlash/rad etish
// 5. Tasdiqlangan ustunlar → scholarship_columns ga saqlash
```

### 7.3 State management

```
React Query (TanStack Query) — server state
  ├── useScholarships()
  ├── useApplication(id)
  ├── useEvaluation(applicationId)
  └── useAIJobStatus(jobId)   # polling (refetchInterval: 2000)

Zustand — client state
  ├── authStore (user, token, role)
  └── uiStore (sidebar, modals)
```

### 7.4 Auth middleware

```typescript
// middleware.ts
const roleRoutes = {
  '/admin/*': ['admin'],
  '/jury/*':  ['jury'],
  '/student/*': ['student'],
}
// JWT verifikatsiya → yo'naltirish
```

---

## 8. Fayl tuzilmasi

```
stipendiya-platform/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI app
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── scholarships.py
│   │   │       ├── applications.py
│   │   │       ├── evaluations.py
│   │   │       ├── achievements.py
│   │   │       └── users.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── scholarship.py
│   │   │   ├── application.py
│   │   │   ├── evaluation.py
│   │   │   └── ai_job.py
│   │   ├── schemas/
│   │   │   ├── user.py                  # Pydantic schemas
│   │   │   ├── scholarship.py
│   │   │   ├── application.py
│   │   │   └── evaluation.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── scholarship_service.py
│   │   │   ├── application_service.py
│   │   │   ├── evaluation_service.py
│   │   │   └── file_service.py          # MinIO/S3 operations
│   │   └── core/
│   │       ├── config.py                # Pydantic settings
│   │       ├── database.py              # SQLAlchemy + asyncpg
│   │       ├── security.py              # JWT utils
│   │       ├── deps.py                  # Role guards, get_current_user
│   │       ├── redis_client.py
│   │       └── llm_config.py
│   │
│   ├── mcp/
│   │   ├── server.py                    # FastMCP server
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── parse_nizom.py
│   │       ├── suggest_columns.py
│   │       ├── analyze_application.py
│   │       └── generate_review.py
│   │
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks.py
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── test_auth.py
│   │   ├── test_scholarships.py
│   │   └── test_ai_tools.py
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/                             # Next.js App Router (yuqorida)
│   ├── components/
│   │   ├── ui/                          # shadcn/ui bazaviy komponentlar
│   │   ├── scholarship/
│   │   │   ├── ColumnBuilder.tsx
│   │   │   ├── NizomUploader.tsx
│   │   │   └── ScholarshipCard.tsx
│   │   ├── application/
│   │   │   ├── DynamicForm.tsx
│   │   │   ├── ApplicationCard.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── evaluation/
│   │   │   ├── ScoringPanel.tsx
│   │   │   └── AIReviewEditor.tsx
│   │   └── shared/
│   │       ├── FileUpload.tsx
│   │       ├── AIJobStatus.tsx          # Polling component
│   │       └── RoleGuard.tsx
│   ├── lib/
│   │   ├── api.ts                       # Axios instance + interceptors
│   │   ├── auth.ts                      # JWT helpers
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useScholarships.ts
│   │   └── useAIJob.ts
│   ├── store/
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   ├── types/
│   │   └── index.ts                     # TypeScript type definitions
│   ├── middleware.ts
│   ├── next.config.ts
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── docker-compose.prod.yml
└── README.md
```

---

## 9. Muhit o'zgaruvchilari

### Backend `.env`

```env
# Application
APP_NAME=stipendiya-platform
DEBUG=true
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/stipendiya_db

# Redis
REDIS_URL=redis://localhost:6379/0

# File Storage (MinIO)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=stipendiya-files
MINIO_USE_SSL=false

# AI Providers
DEFAULT_LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# MCP Server
MCP_SERVER_PORT=8001
```

### Frontend `.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=Stipendiya Platform
```

---

## 10. Deployment

### `docker-compose.yml` (development)

```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: stipendiya_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    depends_on:
      - db
      - redis

  mcp-server:
    build: ./backend
    command: python mcp/server.py
    ports:
      - "8001:8001"
    env_file: ./backend/.env
    depends_on:
      - backend

  celery:
    build: ./backend
    command: celery -A workers.celery_app worker --loglevel=info
    volumes:
      - ./backend:/app
    env_file: ./backend/.env
    depends_on:
      - redis
      - backend

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    env_file: ./frontend/.env.local

volumes:
  postgres_data:
  minio_data:
```

---

## 11. Ishlab chiqish bosqichlari

### Sprint 1 — Foundation (1-2 hafta)

- [ ] Backend scaffold: FastAPI + SQLAlchemy async + Alembic
- [ ] Barcha DB jadvallari va migratsiyalar
- [ ] Auth moduli: JWT + 3 rol
- [ ] Foydalanuvchilar CRUD (admin)
- [ ] Next.js scaffold + routing + middleware
- [ ] Login / register sahifalari

### Sprint 2 — Core Features (2-3 hafta)

- [ ] Stipendiyalar CRUD (admin)
- [ ] Scholarship columns CRUD + DynamicForm component
- [ ] File upload (MinIO integratsiyasi)
- [ ] Arizalar topshirish (student)
- [ ] Ilmiy rahbar tanlash

### Sprint 3 — AI Integration (2 hafta)

- [ ] FastMCP server setup
- [ ] `parse_nizom` + `suggest_columns` tools
- [ ] `analyze_application` tool + Celery async
- [ ] NizomUploader component (AI flow)
- [ ] AI job status polling (frontend)

### Sprint 4 — Evaluation (1-2 hafta)

- [ ] Hakamlar baholash paneli
- [ ] `generate_review` tool
- [ ] AIReviewEditor component
- [ ] Student natijalar sahifasi
- [ ] G'oliblarni e'lon qilish

### Sprint 5 — Polish (1 hafta)

- [ ] Student portfeli (achievements)
- [ ] Admin dashboard statistika
- [ ] Email xabarnomalar (ixtiyoriy)
- [ ] Testlar
- [ ] Production deployment

---

## Texnologiyalar versiyalari

| Texnologiya | Versiya |
|-------------|---------|
| Python | 3.12+ |
| FastAPI | 0.115+ |
| SQLAlchemy | 2.0+ (async) |
| Alembic | 1.14+ |
| FastMCP | 2.0+ |
| Celery | 5.4+ |
| Node.js | 20+ |
| Next.js | 14+ (App Router) |
| React | 18+ |
| TypeScript | 5+ |
| TanStack Query | 5+ |
| Zustand | 4+ |
| PostgreSQL | 16+ |
| Redis | 7+ |

---

*Hujjat oxiri. Savollar bo'lsa — har bir modulni alohida batafsil yozib berish mumkin.*