-- ============================================================
-- CV-App: Políticas de Row Level Security (RLS)
-- ============================================================
-- Cada usuario solo puede ver y modificar sus propios datos.
-- Los administradores (JWT claim is_admin = true) pueden ver todo.
-- ============================================================

-- --------------------------------------------------------
-- Habilitar RLS en todas las tablas
-- --------------------------------------------------------
ALTER TABLE cv_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE base_cv ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;

-- --------------------------------------------------------
-- Políticas para cv_history
-- --------------------------------------------------------
CREATE POLICY cv_history_select_own ON cv_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY cv_history_insert_own ON cv_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY cv_history_update_own ON cv_history
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY cv_history_delete_own ON cv_history
    FOR DELETE USING (auth.uid() = user_id);

-- Admin: acceso total
CREATE POLICY cv_history_admin_all ON cv_history
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );

-- --------------------------------------------------------
-- Políticas para skill_memory
-- --------------------------------------------------------
CREATE POLICY skill_memory_select_own ON skill_memory
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY skill_memory_insert_own ON skill_memory
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY skill_memory_update_own ON skill_memory
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY skill_memory_delete_own ON skill_memory
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY skill_memory_admin_all ON skill_memory
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );

-- --------------------------------------------------------
-- Políticas para base_cv
-- --------------------------------------------------------
CREATE POLICY base_cv_select_own ON base_cv
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY base_cv_insert_own ON base_cv
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY base_cv_update_own ON base_cv
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY base_cv_delete_own ON base_cv
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY base_cv_admin_all ON base_cv
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );

-- --------------------------------------------------------
-- Políticas para interview_sessions
-- --------------------------------------------------------
CREATE POLICY interview_sessions_select_own ON interview_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY interview_sessions_insert_own ON interview_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY interview_sessions_update_own ON interview_sessions
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY interview_sessions_delete_own ON interview_sessions
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY interview_sessions_admin_all ON interview_sessions
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );
