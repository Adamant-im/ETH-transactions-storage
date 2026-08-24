-- Deprecated / Legacy indexes (optional)
-- These indexes are redundant for official ADAMANT clients (adamant-im and adamant-iOS)
-- and cost ~90-110 GB of additional disk space on ~490M rows (1-year dataset).
-- Only apply these indexes if custom or third-party integrations issue non-standard queries.

-- Redundant: covered by txto_contract_to_index and txto_w_empty_contract_to_index.
-- Standard ADAMANT clients never query contract_to alone without txto.
CREATE INDEX IF NOT EXISTS contract_to_index
    ON public.ethtxs USING btree
    (contract_to);

-- Redundant: covered by partial txto_w_empty_contract_to_index (ETH)
-- and composite txto_contract_to_index (ERC-20).
CREATE INDEX IF NOT EXISTS txto_index
    ON public.ethtxs USING btree
    (txto);

-- Redundant: no client queries txto AND txfrom equality simultaneously.
CREATE INDEX IF NOT EXISTS txto_txfrom_index
    ON public.ethtxs USING btree
    (txto, txfrom);

/*
-- Complex index alternative:
-- Can replace txto_w_empty_contract_to_index if extra disk space is available.
CREATE INDEX complex_index
    ON public.ethtxs USING btree
    (contract_to, txfrom, txto);
*/

/*
-- Reclaiming disk space on existing nodes:
-- Run to drop redundant indexes concurrently without blocking ongoing ethsync writes:
DROP INDEX CONCURRENTLY IF EXISTS public.contract_to_index;
DROP INDEX CONCURRENTLY IF EXISTS public.txto_index;
DROP INDEX CONCURRENTLY IF EXISTS public.txto_txfrom_index;
*/
