CREATE INDEX time_index
    ON public.ethtxs USING btree
    (time);

CREATE INDEX txto_txfrom_index
    ON public.ethtxs USING btree
    (txto, txfrom);

CREATE INDEX txto_contract_to_index
    ON public.ethtxs USING btree
    (txto, contract_to);

CREATE INDEX txto_w_empty_contract_to_index
    ON public.ethtxs USING btree
    (txto)
    WHERE contract_to = '';

/*
  You can replace txto_w_empty_contract_to_index with the next one.
  It uses more disk space but generally it's faster.
*/

/*
CREATE INDEX complex_index
    ON public.ethtxs USING btree
    (contract_to, txfrom, txto);
*/
