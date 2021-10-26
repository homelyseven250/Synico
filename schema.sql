CREATE TABLE IF NOT EXISTS guilds (
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

CREATE TABLE IF NOT EXISTS mutes (
    guild bigint,
    muted bigint,
    ends timestamp with time zone,
    starts timestamp with time zone,
    reason text
);


CREATE TABLE IF NOT EXISTS tags (
    guild bigint,
    creator bigint,
    created timestamp with time zone,
    used bigint,
    content text,
    tag text
);

CREATE TABLE IF NOT EXISTS warns (
    guild bigint,
    warned bigint,
    author bigint,
    warn text,
    warned bigint,
    created timestamp with time zone
);

CREATE TABLE IF NOT EXISTS tickets
(
    guild bigint,
    ticket_id bigint,
    ticket_author bigint,
    ticket_channel bigint,
    message_id bigint
);