-- Nodig voor gen_random_uuid() en performance goodies
create extension if not exists "pgcrypto";
create extension if not exists "btree_gin";
create extension if not exists "btree_gist";
