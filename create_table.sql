CREATE TABLE public.ethtxs
(
    "time" integer,
    txfrom text COLLATE pg_catalog."default",
    txto text COLLATE pg_catalog."default",
    gas bigint,
    gasprice bigint,
    block integer,
    txhash text COLLATE pg_catalog."default",
    value numeric,
    contract_to text COLLATE pg_catalog."default",
    contract_value text COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

CREATE INDEX block_index
    ON public.ethtxs USING btree
    (block)
    TABLESPACE pg_default;

CREATE INDEX contract_to_index
    ON public.ethtxs USING btree
    (contract_to COLLATE pg_catalog."default")
    TABLESPACE pg_default;

CREATE INDEX txfrom_index
    ON public.ethtxs USING btree
    (txfrom COLLATE pg_catalog."default")
    TABLESPACE pg_default;

CREATE INDEX txto_index
    ON public.ethtxs USING btree
    (txto COLLATE pg_catalog."default")
    TABLESPACE pg_default;