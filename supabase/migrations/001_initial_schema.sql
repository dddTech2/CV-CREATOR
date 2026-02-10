-- ============================================================
-- CV-App: Esquema inicial PostgreSQL (migrado desde SQLite)
-- ============================================================
-- Tablas: cv_history, skill_memory, base_cv, interview_sessions
-- Todas las tablas incluyen user_id UUID para soporte multiusuario.
-- user_id será NULL hasta que se implemente autenticación (PRD auth).
-- Se usa NULLS NOT DISTINCT en constraints UNIQUE para que
-- NULL se trate como valor igual (PostgreSQL 15+).
-- ============================================================

-- --------------------------------------------------------
-- 1. cv_history: Historial de CVs generados
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS cv_history (
    id          SERIAL PRIMARY KEY,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    job_title   TEXT NOT NULL,
    company     TEXT,
    language    TEXT DEFAULT 'es',
    theme       TEXT DEFAULT 'classic',
    yaml_content TEXT NOT NULL,
    yaml_path   TEXT,
    pdf_path    TEXT,
    original_cv TEXT,
    job_description TEXT,
    gap_analysis TEXT,
    questions_asked TEXT
);

CREATE INDEX IF NOT EXISTS idx_cv_history_user_created
    ON cv_history (user_id, created_at DESC);

-- --------------------------------------------------------
-- 2. skill_memory: Respuestas de habilidades del usuario
-- --------------------------------------------------------
-- PK surrogate (id) + UNIQUE(user_id, skill_name) para upsert.
-- En SQLite era skill_name TEXT PRIMARY KEY (single-user).
-- Ahora cada usuario puede tener sus propias respuestas.
CREATE TABLE IF NOT EXISTS skill_memory (
    id          SERIAL PRIMARY KEY,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    skill_name  TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    usage_count INTEGER DEFAULT 1,
    UNIQUE NULLS NOT DISTINCT (user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_skill_memory_user
    ON skill_memory (user_id);

-- --------------------------------------------------------
-- 3. base_cv: CV base predeterminado (uno por usuario)
-- --------------------------------------------------------
-- En SQLite era singleton con CHECK(id = 1).
-- Ahora UNIQUE(user_id) garantiza un solo CV base por usuario.
CREATE TABLE IF NOT EXISTS base_cv (
    id          SERIAL PRIMARY KEY,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    cv_text     TEXT NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE NULLS NOT DISTINCT (user_id)
);

-- --------------------------------------------------------
-- 4. interview_sessions: Preguntas/respuestas de entrevista
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_sessions (
    id               SERIAL PRIMARY KEY,
    user_id          UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    cv_id            INTEGER REFERENCES cv_history(id) ON DELETE CASCADE,
    question         TEXT NOT NULL,
    generated_answer TEXT NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user
    ON interview_sessions (user_id);
