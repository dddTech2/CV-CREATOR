-- ============================================================
-- CV-App: Token Tracking & Audit Log
-- ============================================================
-- Tablas para registrar consumo de tokens de IA y auditoria de usuarios.
-- Precios base (Gemini 3 Pro Preview):
-- Input: $2.00 / 1M tokens
-- Output: $12.00 / 1M tokens
-- TRM: 4200 COP
-- ============================================================

-- --------------------------------------------------------
-- 1. Tabla token_usage
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS token_usage (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    cv_id           INTEGER REFERENCES cv_history(id) ON DELETE SET NULL,
    operation       TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    input_cost_cop  NUMERIC(10,4) NOT NULL DEFAULT 0,
    output_cost_cop NUMERIC(10,4) NOT NULL DEFAULT 0,
    total_cost_cop  NUMERIC(10,4) NOT NULL DEFAULT 0,
    model_used      TEXT NOT NULL DEFAULT 'gemini-3-flash-preview',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indices para reportes rapidos
CREATE INDEX IF NOT EXISTS idx_token_usage_user_created 
    ON token_usage (user_id, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_token_usage_cv 
    ON token_usage (cv_id);

-- RLS para token_usage
ALTER TABLE token_usage ENABLE ROW LEVEL SECURITY;

-- Usuarios ven su propio consumo
CREATE POLICY token_usage_select_own ON token_usage
    FOR SELECT USING (auth.uid() = user_id);

-- Admins ven todo el consumo
CREATE POLICY token_usage_admin_all ON token_usage
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );

-- El backend (service_role) puede insertar registros
-- (Los usuarios normales NO deben poder insertar su propio consumo directamente,
--  esto lo hace el backend con privilegios o via funcion segura)

-- --------------------------------------------------------
-- 2. Tabla user_audit_log
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_audit_log (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- Usuario afectado
    admin_id            UUID NOT NULL REFERENCES auth.users(id), -- Admin que ejecuto la accion
    action              TEXT NOT NULL CHECK (action IN ('activate', 'deactivate')),
    tokens_at_action    INTEGER DEFAULT 0,
    cost_at_action_cop  NUMERIC(10,4) DEFAULT 0,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user 
    ON user_audit_log (user_id, created_at DESC);

-- RLS para user_audit_log
ALTER TABLE user_audit_log ENABLE ROW LEVEL SECURITY;

-- Solo admins pueden ver y crear logs de auditoria
CREATE POLICY audit_log_admin_all ON user_audit_log
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );
