-- Additional index completing the minimal 5-index set for ADAMANT clients
-- Run after initial block synchronization

-- 5. Timestamp index: used by all history queries for ORDER BY time DESC
CREATE INDEX IF NOT EXISTS time_index
    ON public.ethtxs USING btree
    (time);
