SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE IF EXISTS piano_export;

CREATE DATABASE piano_export WITH TEMPLATE = template0 ENCODING = 'UTF8';


ALTER DATABASE piano_export OWNER TO postgres;

\connect piano_export

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA dwh_extract;

CREATE TABLE dwh_extract.myexport (
  click varchar(128) NULL,
  page varchar(400) NULL,
  click_date varchar(50) NULL,
  m_events varchar(50) NULL
);

create table dwh_extract.brochuremonthlyexport(
  id varchar (500),
  title varchar (500),
  received_at_date varchar (500),
  catalog_title varchar (500),
  count_brochure_clicks varchar (500),
  duration_per_brochure_click varchar (500),
  shown_pages_per_brochure_click varchar (500)
);

create table dwh_extract.dailyvisit(
  site varchar (500),
  page_chapter2 varchar (500),
  page varchar (500),
  page_chapter1 varchar (500),
  date varchar (500),
  m_visits varchar (500),
  m_page_loads_per_visit varchar (500),
  m_time_spent_per_visits_loads varchar (500)
);

CREATE SCHEMA traffic;

CREATE TABLE traffic.load_statistics (
  start_time timestamp with time zone,
  duration_s integer,
  filename varchar(256),
  csv_rows_count integer,
  tablename varchar(256),
  loaded_count integer,
  status varchar(10),
  status_msg varchar(500)
);

