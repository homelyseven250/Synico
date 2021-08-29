--
-- PostgreSQL database dump
--

-- Dumped from database version 12.7 (Ubuntu 12.7-0ubuntu0.20.04.1)
-- Dumped by pg_dump version 12.7 (Ubuntu 12.7-0ubuntu0.20.04.1)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist (
    guild_id bigint,
    blocked bigint
);


ALTER TABLE public.blacklist OWNER TO postgres;

--
-- Name: guild; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guild (
    guild_id bigint NOT NULL,
    prefix text,
    dmhelp boolean,
    logs bigint,
    timezone text,
    muterole bigint,
    admin bigint,
    mod bigint,
    joining bigint,
    leaving bigint,
    join_msg text,
    leave_msg text,
    twt_channel bigint,
    twt_msg text
);


ALTER TABLE public.guild OWNER TO postgres;

--
-- Name: mutes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mutes (
    guild_id bigint,
    users bigint,
    finishes timestamp with time zone,
    issued timestamp with time zone,
    reading text
);


ALTER TABLE public.mutes OWNER TO postgres;

--
-- Name: reminders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reminders (
    guild_id bigint,
    users bigint,
    finishes timestamp with time zone,
    reason text,
    channel bigint,
    created_at timestamp with time zone,
    reminder_num bigint
);


ALTER TABLE public.reminders OWNER TO postgres;

--
-- Name: streams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.streams (
    guild bigint,
    live_channel bigint,
    streamer text,
    still_live boolean,
    custom_message text,
    stream_title text,
    guild_notified boolean
);


ALTER TABLE public.streams OWNER TO postgres;

--
-- Name: tagging; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tagging (
    guild_id bigint,
    users bigint,
    creation timestamp with time zone,
    uses bigint,
    contents text,
    named text
);


ALTER TABLE public.tagging OWNER TO postgres;

--
-- Name: tempbans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tempbans (
    guild_id bigint,
    users bigint,
    finishes timestamp with time zone
);


ALTER TABLE public.tempbans OWNER TO postgres;

--
-- Name: tweeters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tweeters (
    guild_id bigint,
    twit_handle text
);


ALTER TABLE public.tweeters OWNER TO postgres;

--
-- Name: warnings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warnings (
    warned bigint,
    warning text,
    warner bigint,
    guild_id bigint,
    warn bigint,
    "time" timestamp with time zone
);


ALTER TABLE public.warnings OWNER TO postgres;

--
-- Name: guild guild_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guild
    ADD CONSTRAINT guild_pkey PRIMARY KEY (guild_id);


--
-- PostgreSQL database dump complete
--

