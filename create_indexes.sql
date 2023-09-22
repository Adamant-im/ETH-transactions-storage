CREATE INDEX block_index
    ON public.ethtxs USING btree
    (block);

CREATE INDEX contract_to_index
    ON public.ethtxs USING btree
    (contract_to);

CREATE INDEX txfrom_index
    ON public.ethtxs USING btree
    (txfrom);

CREATE INDEX txto_index
    ON public.ethtxs USING btree
    (txto);
