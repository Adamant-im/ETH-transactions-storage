-- Core database index set (4 of 5 minimal indexes)
-- Tailored specifically for ADAMANT client query patterns (adamant-im & adamant-iOS)
-- Run after initial block synchronization to accelerate data ingestion

-- 1. Block index: used by /max_block health-check endpoint (SELECT MAX(block) FROM ethtxs)
CREATE INDEX IF NOT EXISTS block_index
    ON public.ethtxs USING btree
    (block);

-- 2. Sender address index: used by adamant-im (OR branch) and adamant-iOS (ETH request #1 & ERC20 txfrom branch)
CREATE INDEX IF NOT EXISTS txfrom_index
    ON public.ethtxs USING btree
    (txfrom);

-- 3. Composite recipient + token recipient index: used by ERC-20 / USDT queries (adamant-im & adamant-iOS)
CREATE INDEX IF NOT EXISTS txto_contract_to_index
    ON public.ethtxs USING btree
    (txto, contract_to);

-- 4. Partial native transfer recipient index: used by ETH native transfer queries where contract_to is empty (adamant-im & iOS ETH request #2)
CREATE INDEX IF NOT EXISTS txto_w_empty_contract_to_index
    ON public.ethtxs USING btree
    (txto)
    WHERE contract_to = '';
