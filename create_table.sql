CREATE EXTENSION citext;

CREATE TABLE public.ethtxs
(
    "time" integer,
    txfrom citext COLLATE pg_catalog."default",
    txto citext COLLATE pg_catalog."default",
    gas bigint,
    gasprice bigint,
    block integer,
    txhash citext COLLATE pg_catalog."default",
    value numeric,
    contract_to citext COLLATE pg_catalog."default",
    contract_value citext COLLATE pg_catalog."default",
    status boolean
);

CREATE TABLE public.aval
(
    "status" INTEGER
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

CREATE VIEW max_block as 
    SELECT
        MAX(block)
    FROM public.ethtxs;

INSERT INTO public.aval(status) VALUES (1);