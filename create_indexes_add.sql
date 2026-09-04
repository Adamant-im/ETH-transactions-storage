-- Additional index completing the recommended 5-index set
-- Run after the initial block synchronization

-- 5. Timestamp index
-- Query shape: ORDER BY time DESC, used by every address-history query that
-- returns the most recent transfers first.
CREATE INDEX IF NOT EXISTS time_index
    ON public.ethtxs USING btree
    (time);
