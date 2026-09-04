-- Deprecated / legacy indexes (optional)
--
-- These indexes are redundant for the standard address-history query shapes
-- covered by create_indexes.sql and create_indexes_add.sql, and cost roughly
-- 90-110 GB of additional disk space on ~490M rows (a 1-year dataset).
-- Production traffic from the ADAMANT clients (adamant-im and adamant-iOS)
-- never issues the query shapes below.
--
-- Apply them only when a custom or third-party consumer needs those shapes.

-- Query shape: contract_to = {ABI-encoded holder} without a txto predicate.
-- Redundant otherwise: covered by txto_contract_to_index and
-- txto_w_empty_contract_to_index.
CREATE INDEX IF NOT EXISTS contract_to_index
    ON public.ethtxs USING btree
    (contract_to);

-- Query shape: txto = {address} with no contract_to predicate at all.
-- Redundant otherwise: covered by the partial txto_w_empty_contract_to_index
-- for native transfers and by the composite txto_contract_to_index for ERC-20.
CREATE INDEX IF NOT EXISTS txto_index
    ON public.ethtxs USING btree
    (txto);

-- Query shape: simultaneous equality on txto and txfrom.
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
