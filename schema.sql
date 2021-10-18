SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA public;

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

CREATE TABLE public.guilds (
    guild bigint NOT NULL,
    prefix text,
    logs bigint,
    timezone text,
    mute bigint,
    admins bigint,
    mod bigint,
    joins bigint,
    leave bigint,
    welcome text,
    goodbye text,
    twitter bigint,
    tweet text
);

CREATE TABLE public.mutes (
    guild bigint,
    muted bigint,
    ends timestamp with time zone,
    starts timestamp with time zone,
    reason text
);


CREATE TABLE public.tags (
    guild bigint,
    creator bigint,
    created timestamp with time zone,
    used bigint,
    content text,
    tag text
);

CREATE TABLE public.warns (
    guild bigint,
    warned bigint,
    author bigint,
    warn text,
    warned bigint,
    created timestamp with time zone
);