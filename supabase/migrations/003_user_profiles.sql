-- ============================================================
-- CV-App: Perfiles de usuario y sistema de roles
-- ============================================================
-- Tabla user_profiles se crea automaticamente via trigger cuando
-- un usuario se registra en Supabase Auth.
-- Roles: 'user' (default), 'admin'
-- ============================================================

-- --------------------------------------------------------
-- 1. Tabla user_profiles
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email        TEXT NOT NULL,
    display_name TEXT,
    role         TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active    BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_role
    ON user_profiles (role);

CREATE INDEX IF NOT EXISTS idx_user_profiles_is_active
    ON user_profiles (is_active);

-- --------------------------------------------------------
-- 2. Trigger: auto-crear perfil al registrar usuario
-- --------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Eliminar trigger previo si existe (idempotente)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- --------------------------------------------------------
-- 3. RLS para user_profiles
-- --------------------------------------------------------
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Cada usuario puede leer su propio perfil
CREATE POLICY user_profiles_select_own ON user_profiles
    FOR SELECT USING (auth.uid() = id);

-- Cada usuario puede actualizar su propio display_name
-- (role e is_active solo los puede cambiar un admin)
CREATE POLICY user_profiles_update_own ON user_profiles
    FOR UPDATE USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- Admins: acceso total (leer todos los perfiles, modificar roles)
CREATE POLICY user_profiles_admin_all ON user_profiles
    FOR ALL USING (
        coalesce(
            (current_setting('request.jwt.claims', true)::json ->> 'is_admin')::boolean,
            false
        )
    );

-- --------------------------------------------------------
-- 4. Funcion para actualizar updated_at automaticamente
-- --------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_profiles_updated_at ON user_profiles;

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();
