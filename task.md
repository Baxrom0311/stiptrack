# Stipendiya Platform — To'liq Task Breakdown

> **Metodologiya:** Sprint-based · **Jami:** ~120 task · **Taxminiy muddat:** 10-12 hafta  
> **Status belgilari:** `[ ]` Bajarilmagan · `[x]` Bajarilgan · `[~]` Jarayonda

---

## Mundarija

- [Sprint 0 — Muhit va scaffold](#sprint-0--muhit-va-scaffold-35-kun)
- [Sprint 1 — Auth va foydalanuvchilar](#sprint-1--auth-va-foydalanuvchilar-1-hafta)
- [Sprint 2 — Stipendiyalar moduli](#sprint-2--stipendiyalar-moduli-15-hafta)
- [Sprint 3 — Arizalar moduli](#sprint-3--arizalar-moduli-15-hafta)
- [Sprint 4 — AI integratsiya](#sprint-4--ai-integratsiya-2-hafta)
- [Sprint 5 — Baholash moduli](#sprint-5--baholash-moduli-1-hafta)
- [Sprint 6 — Student panel](#sprint-6--student-panel-1-hafta)
- [Sprint 7 — Admin panel](#sprint-7--admin-panel-1-hafta)
- [Sprint 8 — Polish va deploy](#sprint-8--polish-va-deploy-1-hafta)

---

## Sprint 0 — Muhit va scaffold (3–5 kun)

### Backend

- [x] **BE-001** Python 3.12 virtual muhit yaratish (`venv` yoki `uv`)
- [x] **BE-002** `requirements.txt` tuzish: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose, passlib, python-multipart, celery, redis, minio, fastmcp
- [x] **BE-003** FastAPI app skeleti yaratish (`app/main.py`, CORS, lifespan)
- [x] **BE-004** Pydantic `Settings` konfiguratsiya (`core/config.py`, `.env` o'qish)
- [x] **BE-005** SQLAlchemy async engine va session setup (`core/database.py`)
- [x] **BE-006** Base model yaratish (uuid PK, created_at, updated_at)
- [x] **BE-007** Alembic initialization (`alembic init`, `env.py` async sozlash)
- [x] **BE-008** Backend `Dockerfile` yozish
- [x] **BE-009** Barcha DB modellarini yozish (users, scholarships, scholarship_columns, jury_assignments, applications, application_values, evaluations, student_achievements, ai_jobs)
- [x] **BE-010** Birinchi Alembic migration yaratish va ishga tushirish
- [x] **BE-011** Redis client setup (`core/redis_client.py`)
- [x] **BE-012** MinIO client setup (`services/file_service.py`, bucket yaratish)
- [x] **BE-013** Celery app initialization (`workers/celery_app.py`)
- [x] **BE-014** `/health` endpoint qo'shish (DB + Redis + MinIO ping)

### Frontend

- [x] **FE-001** Next.js 14 App Router loyiha yaratish (`create-next-app --typescript`)
- [x] **FE-002** Zaruriy paketlar o'rnatish: axios, @tanstack/react-query, zustand, react-hook-form, zod, shadcn/ui
- [x] **FE-003** shadcn/ui initialization va asosiy komponentlar (Button, Input, Card, Dialog, Badge, Table, Tabs)
- [x] **FE-004** Axios instance yaratish (`lib/api.ts`): baseURL, interceptors (JWT header, 401 refresh)
- [x] **FE-005** TypeScript type definitions (`types/index.ts`): User, Scholarship, Application, Evaluation, Column, Achievement
- [x] **FE-006** TanStack Query provider wrapper (`app/providers.tsx`)
- [x] **FE-007** Zustand auth store (`store/authStore.ts`): user, token, role, setUser, logout
- [x] **FE-008** Next.js `middleware.ts`: route protection + role-based redirect
- [x] **FE-009** Layout komponentlar: AdminLayout, JuryLayout, StudentLayout (sidebar, header, breadcrumb)
- [x] **FE-010** Frontend `Dockerfile` yozish

### DevOps

- [x] **DO-001** `docker-compose.yml` yozish: postgres, redis, minio, backend, mcp-server, celery, frontend
- [x] **DO-002** `.env.example` fayllar yaratish (backend va frontend)
- [x] **DO-003** Git repo initialization, `.gitignore` (`.env`, `__pycache__`, `node_modules`, `.next`)
- [x] **DO-004** `README.md` — ishga tushirish ko'rsatmalari

---

## Sprint 1 — Auth va foydalanuvchilar (1 hafta)

### Backend

- [x] **BE-101** `User` Pydantic sxemalari: `UserCreate`, `UserOut`, `UserUpdate`, `UserLogin`
- [x] **BE-102** Password hashing utility (`passlib[bcrypt]`)
- [x] **BE-103** JWT token yaratish va verifikatsiya (`core/security.py`): access token (60 min), refresh token (30 kun)
- [x] **BE-104** `get_current_user` dependency (`core/deps.py`)
- [x] **BE-105** Role guard decoratorlar: `require_admin`, `require_jury`, `require_student`
- [x] **BE-106** `POST /auth/register` — ro'yxatdan o'tish (default role: student)
- [x] **BE-107** `POST /auth/login` — kirish, JWT qaytarish
- [x] **BE-108** `POST /auth/refresh` — refresh token bilan access token yangilash
- [x] **BE-109** `POST /auth/logout` — refresh tokenni Redis blacklist ga qo'shish
- [x] **BE-110** `GET /auth/me` — joriy foydalanuvchi
- [x] **BE-111** `PATCH /auth/me` — profil yangilash
- [x] **BE-112** `GET /users` (admin only) — filter: role, is_active, search
- [x] **BE-113** `POST /users` (admin) — foydalanuvchi yaratish
- [x] **BE-114** `PATCH /users/{id}` (admin) — tahrirlash
- [x] **BE-115** `PATCH /users/{id}/toggle-active` (admin) — bloklash/faollashtirish
- [x] **BE-116** `GET /users/supervisors` — ilmiy rahbarlar ro'yxati (`is_supervisor=true`)
- [x] **BE-117** Auth uchun unit testlar (`tests/test_auth.py`)

### Frontend

- [x] **FE-101** Login sahifasi (`app/(auth)/login/page.tsx`): email/password form, validation (zod)
- [x] **FE-102** Register sahifasi (`app/(auth)/register/page.tsx`): to'liq forma
- [x] **FE-103** `useAuth` hook: login, logout, register, me funksiyalari
- [x] **FE-104** JWT token localStorage/cookie saqlash + auto-refresh logikasi
- [x] **FE-105** Foydalanuvchilar sahifasi (admin): jadval, filter, qidirish
- [x] **FE-106** Foydalanuvchi yaratish/tahrirlash modal (admin)
- [x] **FE-107** Profil sahifasi (barcha rollar): ma'lumotlarni ko'rish va tahrirlash

---

## Sprint 2 — Stipendiyalar moduli (1.5 hafta)

### Backend

- [x] **BE-201** `Scholarship` + `ScholarshipColumn` Pydantic sxemalari
- [x] **BE-202** `ScholarshipService` yaratish (biznes logika alohida)
- [x] **BE-203** `GET /scholarships` — ro'yxat (admin: hammasi; student: faqat `open`)
- [x] **BE-204** `POST /scholarships` (admin) — yangi stipendiya yaratish (`draft` statusda)
- [x] **BE-205** `GET /scholarships/{id}` — batafsil (columns bilan birga)
- [x] **BE-206** `PATCH /scholarships/{id}` (admin) — tahrirlash (faqat `draft` yoki `open`)
- [x] **BE-207** `DELETE /scholarships/{id}` (admin) — o'chirish (faqat `draft`)
- [x] **BE-208** `PATCH /scholarships/{id}/status` (admin) — holat o'zgartirish + validatsiya (ketma-ket: draft→open→closed→done)
- [x] **BE-209** `POST /scholarships/{id}/upload-nizom` — PDF yuklash → MinIO saqlash → URL qaytarish
- [x] **BE-210** `GET /scholarships/{id}/columns` — ustunlar (order_index bo'yicha)
- [x] **BE-211** `POST /scholarships/{id}/columns` (admin) — ustun qo'shish
- [x] **BE-212** `PATCH /scholarships/{id}/columns/{col_id}` (admin) — ustun tahrirlash
- [x] **BE-213** `DELETE /scholarships/{id}/columns/{col_id}` (admin) — ustun o'chirish
- [x] **BE-214** `PATCH /scholarships/{id}/columns/reorder` (admin) — drag-drop tartibni saqlash
- [x] **BE-215** `GET /scholarships/{id}/jury` — biriktirilgan hakamlar
- [x] **BE-216** `POST /scholarships/{id}/jury` (admin) — hakim biriktirish
- [x] **BE-217** `DELETE /scholarships/{id}/jury/{jury_id}` (admin) — hakim olib tashlash
- [x] **BE-218** Stipendiya sxemalari uchun testlar

### Frontend

- [x] **FE-201** Stipendiyalar ro'yxati sahifasi (admin): jadval, status badge, filter
- [x] **FE-202** Yangi stipendiya yaratish sahifasi: asosiy ma'lumotlar forma
- [x] **FE-203** Stipendiya tahrirlash sahifasi
- [x] **FE-204** `ScholarshipCard` komponenti (student uchun)
- [x] **FE-205** Ochiq stipendiyalar sahifasi (student): kartalar, qidiruv, filter
- [x] **FE-206** Stipendiya batafsil sahifasi (student): tavsif, muddат, ustunlar
- [x] **FE-207** **`ColumnBuilder.tsx`** — drag-and-drop ustun quruvchi:
  - [x] **FE-207a** Ustun qo'shish forma (nom, tavsif, field_type, is_required, ai_analyze checkbox, max_score)
  - [x] **FE-207b** `@dnd-kit/core` bilan drag-and-drop reorder
  - [x] **FE-207c** Ustun o'chirish (confirm dialog)
  - [x] **FE-207d** AI taklif qilingan ustunlarni import tugmasi
- [x] **FE-208** Hakamlar boshqarish sahifasi (admin): qo'shish/olib tashlash
- [x] **FE-209** Stipendiya holat o'zgartirish (admin): confirm modal + validatsiya xabari
- [x] **FE-210** `useScholarships`, `useScholarship`, `useScholarshipColumns` hooks (React Query)
- [x] **FE-211** `StatusBadge` komponenti (draft/open/closed/done → rang)

---

## Sprint 3 — Arizalar moduli (1.5 hafta)

### Backend

- [x] **BE-301** `Application` + `ApplicationValue` Pydantic sxemalari
- [x] **BE-302** `ApplicationService` yaratish
- [x] **BE-303** `POST /scholarships/{id}/apply` (student) — draft ariza yaratish (yoki mavjudni qaytarish)
- [x] **BE-304** `GET /scholarships/{id}/apply` (student) — ariza forma (columns + mavjud qiymatlar)
- [x] **BE-305** `PATCH /applications/{id}` (student) — qoralama qiymatlarni saqlash
- [x] **BE-306** `POST /applications/{id}/values/{col_id}/upload` (student) — fayl yuklash (MinIO)
- [x] **BE-307** `POST /applications/{id}/submit` (student) — topshirish + validatsiya (required fieldlar to'ldirilganmi)
- [x] **BE-308** `GET /applications/my` (student) — o'zining arizalari + holat + bali
- [x] **BE-309** `GET /scholarships/{id}/applications` (admin/jury) — barcha arizalar (filter: status, sort: score)
- [x] **BE-310** `GET /applications/{id}` (admin/jury) — ariza batafsil + barcha qiymatlar + AI xulosalar
- [x] **BE-311** `PATCH /applications/{id}/status` (admin) — holat o'zgartirish
- [x] **BE-312** `POST /scholarships/{id}/announce-winners` (admin) — g'oliblarni belgilash (top N by score)
- [x] **BE-313** Stipendiya `closed` bo'lganda yangi arizalarni rad etish logikasi
- [x] **BE-314** Arizalar uchun testlar

### Frontend

- [x] **FE-301** **`DynamicForm.tsx`** — dinamik ariza forma:
  - [x] **FE-301a** `text` → `<Input>`
  - [x] **FE-301b** `textarea` → `<Textarea>` (belgilar hisoblagichi bilan)
  - [x] **FE-301c** `number` → `<NumberInput>` (min/max)
  - [x] **FE-301d** `file` → `<FileUpload>` (drag-and-drop, progress bar, fayl turi validatsiyasi)
  - [x] **FE-301e** `date` → `<DatePicker>`
  - [x] **FE-301f** `select` → `<Select>` (select_options dan)
  - [x] **FE-301g** `url` → `<Input>` + URL validatsiya
  - [x] **FE-301h** Required field belgilash (`*`)
  - [x] **FE-301i** Auto-save (debounce 2s, draft saqlash)
- [x] **FE-302** Ariza topshirish sahifasi (student): DynamicForm + ilmiy rahbar tanlash dropdown
- [x] **FE-303** `FileUpload` komponenti: drag-drop, preview, progress, o'chirish
- [x] **FE-304** Mening arizalarim sahifasi (student): holat, ball, tahlilga havola
- [x] **FE-305** Ariza natijasi sahifasi (student): balllar jadval, hakim tahlili (o'qish uchun)
- [x] **FE-306** Arizalar ro'yxati sahifasi (admin): jadval, filter, sort, export
- [x] **FE-307** Ariza batafsil sahifasi (admin): barcha qiymatlar, AI xulosalar
- [x] **FE-308** G'oliblarni e'lon qilish modal (admin): confirm + preview
- [x] **FE-309** `useApplications`, `useApplication`, `useMyApplications` hooks

---

## Sprint 4 — AI integratsiya (2 hafta)

### FastMCP Server

- [x] **AI-001** FastMCP server skeleton (`mcp/server.py`): initialization, port, logging
- [x] **AI-002** LLM provider abstraction (`core/llm_config.py`): Claude, OpenAI, Gemini, Ollama — bitta interfeys
- [x] **AI-003** LLM client factory: `get_llm_client(provider)` → unified `.complete(prompt)` metod

### Tool 1: `parse_nizom`

- [x] **AI-101** `pypdf` yoki `pdfplumber` bilan PDF matn ajratish
- [x] **AI-102** LLM prompt: nizomdan maqsad, talablar, baholash mezonlari ajratish
- [x] **AI-103** Structured output (JSON): `{purpose, requirements[], evaluation_criteria[], raw_text}`
- [x] **AI-104** Xato holatlari: o'qib bo'lmaydigan PDF, juda katta fayl (>10MB), bo'sh matn
- [x] **AI-105** Tool FastMCP serverga ro'yxatdan o'tkazish

### Tool 2: `suggest_columns`

- [x] **AI-201** Prompt engineering: nizom matnidan ustunlar yaratish
- [x] **AI-202** Har bir ustun uchun: nom, tavsif, field_type (mantiqiy tanlash), ai_analyze tavsiyasi, max_score
- [x] **AI-203** Structured JSON output validatsiyasi (Pydantic)
- [x] **AI-204** Kamida 3, ko'pi bilan 10 ta ustun taklif qilish
- [x] **AI-205** Tool FastMCP serverga ro'yxatdan o'tkazish

### Tool 3: `analyze_application`

- [x] **AI-301** Prompt: ustun tavsifi + student qiymati → batafsil tahlil
- [x] **AI-302** Output: `{analysis, suggested_score, strengths[], weaknesses[], recommendation}`
- [x] **AI-303** Fayl bo'lsa: fayl URL ni LLM ga uzatish (rasm uchun vision, PDF uchun matn)
- [x] **AI-304** Tool FastMCP serverga ro'yxatdan o'tkazish

### Tool 4: `generate_review`

- [x] **AI-401** Prompt: balllar + AI xulosalar + hakim izohlari → professional yakuniy tahlil
- [x] **AI-402** O'zbek tilida yozish (yoki konfiguratsiyaga qarab til tanlash)
- [x] **AI-403** Output: `{review_text, summary, total_score}`
- [x] **AI-404** Tool FastMCP serverga ro'yxatdan o'tkazish

### Backend AI endpointlar

- [x] **AI-501** `POST /scholarships/{id}/generate-columns` (admin):
  - [x] **AI-501a** `ai_jobs` jadvaliga `pending` yozuv qo'shish
  - [x] **AI-501b** Celery task: `run_column_generation(scholarship_id, nizom_text)`
  - [x] **AI-501c** Natijani qaytarish: job_id (frontend polling qiladi)
- [x] **AI-502** `POST /evaluations/{application_id}/ai-review` (jury):
  - [x] **AI-502a** `generate_review` tool chaqirish (sync — tez)
  - [x] **AI-502b** Natijani evaluation ga `ai_generated=true` bilan saqlash
- [x] **AI-503** `GET /ai-jobs/{id}/status` — job holati va natijasi
- [x] **AI-504** Celery task: `run_application_analysis(application_id)`:
  - [x] **AI-504a** `ai_analyze=true` ustunlarni topish
  - [x] **AI-504b** Har bir ustun uchun `analyze_application` chaqirish
  - [x] **AI-504c** Natijalarni `application_values.ai_analysis` ga saqlash
  - [x] **AI-504d** `applications.ai_summary` — umumiy xulosa
  - [x] **AI-504e** `ai_jobs` statusini yangilash

### Frontend AI

- [x] **FE-401** **`NizomUploader.tsx`**:
  - [x] **FE-401a** PDF drag-drop yuklash + preview
  - [x] **FE-401b** "AI bilan ustunlar yaratish" tugmasi
  - [x] **FE-401c** Loading state (spinner + "AI tahlil qilmoqda...")
  - [x] **FE-401d** Taklif qilingan ustunlar ro'yxati (har biri uchun qabul/rad toggle)
  - [x] **FE-401e** Tasdiqlash → ColumnBuilder ga import
- [x] **FE-402** **`AIJobStatus.tsx`** — polling komponenti:
  - [x] **FE-402a** `useQuery` + `refetchInterval: 2000` (job `done` yoki `failed` bo'lguncha)
  - [x] **FE-402b** Progress indicator (pending → running → done)
  - [x] **FE-402c** Xato holati: retry tugmasi
- [x] **FE-403** Ariza sahifasida AI xulosalar accordion (hakim uchun):
  - [x] **FE-403a** Har bir `ai_analyze=true` ustun uchun collapsible panel
  - [x] **FE-403b** `strengths` / `weaknesses` ko'rsatish
  - [x] **FE-403c** AI taklif qilingan ball (reference sifatida)
- [x] **FE-404** **`AIReviewEditor.tsx`**:
  - [x] **FE-404a** "AI bilan tahlil yozish" tugmasi
  - [x] **FE-404b** Loading (generate_review API chaqirilmoqda)
  - [x] **FE-404c** Generated matnni `<Textarea>` da ko'rsatish (tahrirlash mumkin)
  - [x] **FE-404d** "AI yordamida yaratildi" badge
  - [x] **FE-404e** Saqlash tugmasi

---

## Sprint 5 — Baholash moduli (1 hafta)

### Backend

- [x] **BE-501** `Evaluation` Pydantic sxemalari
- [x] **BE-502** `EvaluationService` yaratish
- [x] **BE-503** `GET /evaluations/{application_id}` (jury) — mavjud baholash yoki bo'sh skeleton
- [x] **BE-504** `POST /evaluations/{application_id}` (jury) — baholash boshlash (draft)
- [x] **BE-505** `PATCH /evaluations/{application_id}` (jury) — balllar va izoh yangilash (draft)
- [x] **BE-506** `POST /evaluations/{application_id}/submit` (jury) — topshirish + validatsiya (barcha ustunlar baholangan mi)
- [x] **BE-507** Barcha hakamlar topshirgandan keyin `applications.total_score` hisoblash (o'rtacha)
- [x] **BE-508** Student o'z baholashini ko'rishi (faqat hakim `is_submitted=true` bo'lganda)
- [x] **BE-509** Baholash uchun testlar

### Frontend

- [x] **FE-501** **`ScoringPanel.tsx`** — hakim baholash paneli:
  - [x] **FE-501a** Har bir ustun uchun slider (0 → max_score) + raqam input
  - [x] **FE-501b** AI xulosalar accordion (yuqoridagi FE-403)
  - [x] **FE-501c** Ustun izohi textarea (ixtiyoriy)
  - [x] **FE-501d** Yon panel: umumiy ball real-vaqt hisob-kitobi
  - [x] **FE-501e** "Qoralama saqlash" (auto-save 3s debounce)
  - [x] **FE-501f** "Topshirish" tugmasi + confirm dialog
- [x] **FE-502** Hakim arizalar ro'yxati sahifasi: baholanmagan/baholangan/topshirilgan filter
- [x] **FE-503** Hakim ariza batafsil sahifasi: chap — student ma'lumotlari, o'ng — ScoringPanel
- [x] **FE-504** AIReviewEditor baholash paneliga integratsiya
- [x] **FE-505** Student natija sahifasi: ustunlar bo'yicha balllar jadval + hakim tahlili matni

---

## Sprint 6 — Student panel (1 hafta)

### Backend

- [x] **BE-601** `Achievement` Pydantic sxemalari
- [x] **BE-602** `GET /achievements` (student) — o'zining yutuqlari
- [x] **BE-603** `POST /achievements` (student) — yangi qo'shish
- [x] **BE-604** `PATCH /achievements/{id}` (student) — tahrirlash
- [x] **BE-605** `DELETE /achievements/{id}` (student) — o'chirish
- [x] **BE-606** `POST /achievements/{id}/upload` (student) — fayl biriktirish (MinIO)
- [x] **BE-607** Hakim ariza ko'rayotganda student yutuqlarini ham ko'ra olishi

### Frontend

- [x] **FE-601** Student dashboard sahifasi: statistika kartalar (faol arizalar, natijalar, yangi stipendiyalar)
- [x] **FE-602** Portfel sahifasi (`achievements`):
  - [x] **FE-602a** Yutuqlar ro'yxati (type bo'yicha filter: maqola, mukofot, loyiha, sertifikat)
  - [x] **FE-602b** Yangi yutuq qo'shish modal: nom, tur, sana, tavsif, fayl
  - [x] **FE-602c** Tahrirlash va o'chirish
  - [x] **FE-602d** Fayl ko'rish (PDF inline, rasm preview)
- [x] **FE-603** Mening arizalarim sahifasi: holat timeline, ball, tahlilga havola
- [x] **FE-604** Stipendiya natijasi sahifasi (student): konfetti animatsiya g'olib bo'lsa 🎉
- [x] **FE-605** Student profili: ma'lumotlar + ilmiy rahbar ko'rsatish

---

## Sprint 7 — Admin panel (1 hafta)

### Backend

- [x] **BE-701** Admin dashboard statistika endpoint: `GET /admin/stats`
  - jami stipendiyalar (status bo'yicha), jami arizalar, jami foydalanuvchilar, AI job statistikasi
- [x] **BE-702** `GET /admin/scholarships/{id}/results` — stipendiya yakuniy natijalari (barcha arizalar bali bo'yicha sort)

### Frontend

- [x] **FE-701** Admin dashboard: statistika kartalar + grafiklar (recharts)
  - [x] **FE-701a** Stipendiyalar holat bo'yicha donut chart
  - [x] **FE-701b** Arizalar dinamikasi line chart
  - [x] **FE-701c** Oxirgi faoliyat feed
- [x] **FE-702** Stipendiya boshqarish sahifasi (admin):
  - [x] **FE-702a** Asosiy ma'lumotlar tahrirlash
  - [x] **FE-702b** NizomUploader + ColumnBuilder tab
  - [x] **FE-702c** Hakamlar tab
  - [x] **FE-702d** Arizalar tab (natijalar bilan)
  - [x] **FE-702e** Holat o'zgartirish tugmasi
- [x] **FE-703** Stipendiya yakuniy natijalari sahifasi: top-N jadval, g'oliblarni tasdiqlash
- [x] **FE-704** Foydalanuvchilar boshqaruv sahifasi: jadval, rol filter, search, bloklash

---

## Sprint 8 — Polish va deploy (1 hafta)

### Sifat

- [x] **QA-001** Backend barcha endpointlar uchun `pytest` testlari (kamida happy path)
- [x] **QA-002** Frontend forma validatsiyalarini tekshirish (zod schemas)
- [x] **QA-003** Mobile responsive tekshirish (NextJS layouts)
- [x] **QA-004** Loading skeleton komponentlar barcha asosiy sahifalar uchun
- [x] **QA-005** Error boundary komponent (React)
- [x] **QA-006** 404 va 403 sahifalari
- [x] **QA-007** Toast notifications: muvaffaqiyat, xato, ogohlantirish (sonner yoki shadcn toast)
- [x] **QA-008** Empty states: arizalar yo'q, stipendiyalar yo'q, va h.k.
- [x] **QA-009** Fayllar uchun tur va hajm validatsiyasi (frontend + backend ikkalasida)
- [x] **QA-010** API rate limiting (`slowapi`)

### Xavfsizlik

- [x] **SEC-001** SQL injection himoya (SQLAlchemy ORM, raw query yo'q)
- [x] **SEC-002** Fayl yuklashda MIME type tekshirish (faqat ruxsat etilgan turlar)
- [x] **SEC-003** MinIO URL larni time-limited presigned URL bilan almashtirishini tekshirish
- [x] **SEC-004** Boshqa foydalanuvchi arizasiga kirish tekshirish (ownership guard)
- [x] **SEC-005** Admin endpointlarida role guard testlari

### Deploy

- [x] **DO-101** `docker-compose.prod.yml` yozish (volume persistence, restart policy, no dev mounts)
- [x] **DO-102** Backend: `gunicorn + uvicorn workers` production config
- [x] **DO-103** Frontend: `next build` + static optimization
- [x] **DO-104** Nginx reverse proxy config (frontend :80, backend /api, MinIO /files)
- [ ] **DO-105** SSL sertifikat (Let's Encrypt / Certbot)
- [x] **DO-106** Alembic avtomatik migration (`docker entrypoint` da)
- [x] **DO-107** Health check endpointlar Docker compose da sozlash
- [x] **DO-108** MinIO production bucket policy (public read faqat kerakli papkalar uchun)
- [ ] **DO-109** Celery Flower monitoring (ixtiyoriy)
- [ ] **DO-110** GitHub Actions CI/CD pipeline (lint → test → build → deploy)

---

## Qo'shimcha (Backlog)

> Asosiy sprintlardan keyin qilinishi mumkin bo'lgan tasklar

- [x] **EXTRA-001** Email xabarnomalar: ariza holati o'zgarganda, g'olib e'lon qilinganda (FastAPI-Mail)
- [x] **EXTRA-002** Stipendiyalarni Excel/PDF formatida eksport qilish
- [x] **EXTRA-003** Hakamlar o'rtasidagi ball farqini ko'rsatish (consistency check)
- [x] **EXTRA-004** Ariza tarixini ko'rish (status log)
- [x] **EXTRA-005** Stipendiya shablonlari (template asosida yangi yaratish)
- [x] **EXTRA-006** AI modelni har bir stipendiya uchun alohida tanlash imkoni (admin)
- [x] **EXTRA-007** Hakim o'zaro ko'rmaslik (blind review) rejimi
- [x] **EXTRA-008** Student dashboard da tugatilgan stipendiyalar tarixini ko'rish
- [x] **EXTRA-009** Plagiat tekshirish (student yuklagan matnlar uchun)
- [ ] **EXTRA-010** Websocket: real-vaqt AI job progress (polling o'rniga)

---

## Task statistikasi

| Sprint | Backend | Frontend | AI | DevOps/QA | Jami |
|--------|---------|----------|----|-----------|------|
| Sprint 0 | 14 | 10 | — | 4 | **28** |
| Sprint 1 | 17 | 7 | — | — | **24** |
| Sprint 2 | 18 | 11 | — | — | **29** |
| Sprint 3 | 14 | 9 | — | — | **23** |
| Sprint 4 | 7 | 6 | 19 | — | **32** |
| Sprint 5 | 9 | 5 | — | — | **14** |
| Sprint 6 | 7 | 5 | — | — | **12** |
| Sprint 7 | 2 | 4 | — | — | **6** |
| Sprint 8 | — | — | — | 20 | **20** |
| **Jami** | **88** | **57** | **19** | **24** | **~188** |

---

*Har bir task bajarilganda `[ ]` → `[x]` qilib belgilang.*  
*Jarayonda bo'lsa `[~]` ishlating.*
