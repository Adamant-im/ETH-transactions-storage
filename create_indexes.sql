-- Core database index set (4 of 5 recommended indexes)
-- Covers the general address-history query shapes any consumer needs:
-- transfers sent by an address, native transfers received by an address,
-- token transfers for a contract and holder, and the block health check.
-- The set was validated against production traffic from the ADAMANT clients
-- (adamant-im and adamant-iOS), which is where the sizing evidence comes from;
-- nothing in it is specific to those clients.
-- Run after the initial block synchronization: building indexes first makes
-- the historical backfill significantly slower.

-- 1. Block index
-- Query shape: SELECT MAX(block) FROM ethtxs, used by the /max_block health check.
CREATE INDEX IF NOT EXISTS block_index
    ON public.ethtxs USING btree
    (block);

-- 2. Sender address index
-- Query shape: txfrom = {address}, for outgoing native and ERC-20 transfers.
CREATE INDEX IF NOT EXISTS txfrom_index
    ON public.ethtxs USING btree
    (txfrom);

-- 3. Composite recipient and token-recipient index
-- Query shape: txto = {token contract} AND contract_to = {ABI-encoded holder},
-- for ERC-20 transfer history.
CREATE INDEX IF NOT EXISTS txto_contract_to_index
    ON public.ethtxs USING btree
    (txto, contract_to);

-- 4. Partial native-transfer recipient index
-- Query shape: txto = {address} AND contract_to = '', for incoming native ETH
-- transfers. The partial predicate keeps every token row out of the index,
-- which is where most of the space saving comes from.
CREATE INDEX IF NOT EXISTS txto_w_empty_contract_to_index
    ON public.ethtxs USING btree
    (txto)
    WHERE contract_to = '';
