-- Runs automatically only when the database volume is empty.
\set ON_ERROR_STOP on
\getenv db_name POSTGRES_DB
\getenv app_user APP_DB_USER
\getenv app_password APP_DB_PASSWORD
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
REVOKE ALL ON DATABASE :"db_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db_name" TO :"app_user";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA app AUTHORIZATION :"app_user";
ALTER ROLE :"app_user" SET search_path TO app;
