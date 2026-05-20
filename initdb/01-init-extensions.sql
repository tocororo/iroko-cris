-- Conectarse a la base de datos correcta (por si acaso)
\c iroko;

-- 2. Habilitar pg_trgm para búsqueda difusa de texto (fuzzy search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 3. Habilitar unaccent para ignorar tildes (útil para español)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Ejemplo: Crear la tabla de búsqueda híbrida (opcional, solo referencia)
-- CREATE TABLE IF NOT EXISTS search_index (
--     id_nodo BIGINT PRIMARY KEY,
--     name TEXT,
--     embedding vector(1536) -- Ajustar dimensión según tu modelo AI
-- );
-- CREATE INDEX IF NOT EXISTS trgm_idx ON search_index USING GIN (name gin_trgm_ops);