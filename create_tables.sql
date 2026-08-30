-- Ethereum Transactions Storage - Base Table & View Definitions
-- PostgreSQL 12+

CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS public.ethtxs
(
    time integer,
    txfrom citext,
    txto citext,
    gas bigint,
    gasprice bigint,
    block integer,
    txhash citext,
    value numeric,
    contract_to citext,
    contract_value citext
);

CREATE TABLE IF NOT EXISTS public.aval
(
    status boolean DEFAULT true
);

CREATE TABLE IF NOT EXISTS public.sync_state
(
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    last_block integer NOT NULL
);

INSERT INTO public.sync_state (singleton, last_block)
SELECT true, MAX(block)
FROM public.ethtxs
HAVING MAX(block) IS NOT NULL
ON CONFLICT (singleton) DO NOTHING;

INSERT INTO public.aval (status)
SELECT true
WHERE NOT EXISTS (SELECT 1 FROM public.aval);

CREATE OR REPLACE VIEW public.max_block AS
SELECT
    GREATEST(
        (SELECT MAX(block) FROM public.ethtxs),
        (SELECT last_block FROM public.sync_state WHERE singleton = true)
    ) AS max,
    '2.5.0'::text AS version;

-- Setup read-only anonymous role for PostgREST
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_anon') THEN
        CREATE ROLE web_anon NOLOGIN;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'api_user') THEN
        GRANT web_anon TO api_user;
        GRANT SELECT, INSERT, UPDATE ON public.sync_state TO api_user;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        GRANT web_anon TO app_user;
        GRANT SELECT, INSERT, UPDATE ON public.sync_state TO app_user;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON public.ethtxs, public.aval, public.max_block TO web_anon;
