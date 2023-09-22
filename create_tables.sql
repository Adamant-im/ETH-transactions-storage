CREATE EXTENSION citext;

CREATE TABLE public.ethtxs
(
    time integer,
    txfrom citext,
    txto citext,
    gas bigint,
    gasprice bigint,
    block integer,
    txhash citext,
    value numeric,
    contract_to citext,
    contract_value citext,
    status boolean
);

CREATE TABLE public.aval
(
    "status" INTEGER
);

INSERT INTO public.aval(status) VALUES (1);

CREATE VIEW max_block as 
    SELECT
        MAX(block)
    FROM public.ethtxs;
