-- Supabase-ready PostgreSQL schema for Opportunity Tracker
-- Paste this entire file into the Supabase SQL Editor and run.

-- 1) Ensure required extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2) Types
-- Create enum type safely (some PG/Supabase environments don't accept IF NOT EXISTS on CREATE TYPE)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'opportunity_status') THEN
    EXECUTE 'CREATE TYPE public.opportunity_status AS ENUM (''open'',''closed'',''expired'')';
  END IF;
END
$$;

-- 3) Utility functions
CREATE OR REPLACE FUNCTION public.normalize_url(p_url text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT lower(regexp_replace(coalesce(p_url, ''), '^(https?://)?(www\.)?', '', 'i'));
$$;

-- 4) Full-text helper (STABLE)
CREATE OR REPLACE FUNCTION public.opportunity_tsvector(
  p_title text,
  p_organization text,
  p_description text,
  p_category text,
  p_source text,
  p_tags text[]
)
RETURNS tsvector
LANGUAGE sql
STABLE
AS $$
  SELECT
    setweight(to_tsvector('simple', coalesce(p_title, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(p_organization, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(p_category, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(p_source, '')), 'C') ||
    setweight(to_tsvector('simple', coalesce(array_to_string(p_tags, ' '), '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(p_description, '')), 'D');
$$;

-- 5) Search tsquery helper (STABLE)
CREATE OR REPLACE FUNCTION public.opportunity_tsquery(p_query text)
RETURNS tsquery
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_query IS NULL OR btrim(p_query) = '' THEN
    RETURN NULL;
  END IF;

  BEGIN
    RETURN websearch_to_tsquery('simple', p_query);
  EXCEPTION WHEN OTHERS THEN
    RETURN plainto_tsquery('simple', coalesce(p_query, ''));
  END;
END;
$$;

-- 6) Generic updated_at trigger
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

-- 7) Opportunities table (no generated columns)
CREATE TABLE IF NOT EXISTS public.opportunities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  organization text,
  description text,
  category text,
  source text,
  url text,
  url_normalized text,
  tags text[] DEFAULT ARRAY[]::text[],
  status public.opportunity_status DEFAULT 'open',
  posted_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  search_tsv tsvector NOT NULL DEFAULT ''::tsvector
);

-- Indexes for opportunities
CREATE INDEX IF NOT EXISTS idx_opportunities_search_tsv ON public.opportunities USING GIN (search_tsv);
CREATE INDEX IF NOT EXISTS idx_opportunities_posted_at ON public.opportunities (posted_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_expires_at ON public.opportunities (expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_url_normalized ON public.opportunities (url_normalized) WHERE url_normalized IS NOT NULL;

-- 8) Trigger function to populate url_normalized + search_tsv
CREATE OR REPLACE FUNCTION public.opportunities_search_tsv_trigger()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  -- normalize URL
  NEW.url_normalized := public.normalize_url(NEW.url);

  -- populate full-text vector
  NEW.search_tsv := public.opportunity_tsvector(
    NEW.title,
    NEW.organization,
    NEW.description,
    NEW.category,
    NEW.source,
    NEW.tags
  );

  RETURN NEW;
END;
$$;

-- 9) Create triggers in the correct order: search_tsv first, then updated_at
DROP TRIGGER IF EXISTS trg_opportunities_set_search_tsv ON public.opportunities;
CREATE TRIGGER trg_opportunities_set_search_tsv
BEFORE INSERT OR UPDATE ON public.opportunities
FOR EACH ROW
EXECUTE FUNCTION public.opportunities_search_tsv_trigger();

DROP TRIGGER IF EXISTS trg_opportunities_set_updated_at ON public.opportunities;
CREATE TRIGGER trg_opportunities_set_updated_at
BEFORE UPDATE ON public.opportunities
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

-- 10) Tracking table
CREATE TABLE IF NOT EXISTS public.opportunity_tracking (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid REFERENCES public.opportunities(id) ON DELETE CASCADE,
  user_id uuid,
  status text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_opportunity_tracking_set_updated_at ON public.opportunity_tracking;
CREATE TRIGGER trg_opportunity_tracking_set_updated_at
BEFORE UPDATE ON public.opportunity_tracking
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

-- 11) Scraper logs
CREATE TABLE IF NOT EXISTS public.scraper_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scraper_name text NOT NULL,
  run_at timestamptz DEFAULT now(),
  items_scraped int DEFAULT 0,
  raw_payload jsonb,
  created_at timestamptz DEFAULT now()
);

-- 12) AI extraction logs
CREATE TABLE IF NOT EXISTS public.ai_extraction_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  opportunity_id uuid REFERENCES public.opportunities(id) ON DELETE SET NULL,
  model text,
  input jsonb,
  output jsonb,
  created_at timestamptz DEFAULT now()
);

-- 13) Helper search function
CREATE OR REPLACE FUNCTION public.search_opportunities(
  p_query text,
  p_limit int DEFAULT 50,
  p_offset int DEFAULT 0
)
RETURNS TABLE (id uuid, title text, description text, rank float)
LANGUAGE sql
STABLE
AS $$
  SELECT o.id, o.title, o.description, ts_rank(o.search_tsv, q) AS rank
  FROM public.opportunities o, websearch_to_tsquery('simple', p_query) q
  WHERE o.search_tsv @@ q
  ORDER BY rank DESC
  LIMIT p_limit OFFSET p_offset;
$$;

-- 14) Utility views/functions (optional)
CREATE OR REPLACE FUNCTION public.get_latest_opportunities(p_limit int DEFAULT 20)
RETURNS SETOF public.opportunities
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM public.opportunities ORDER BY created_at DESC LIMIT p_limit;
$$;

-- End of schema
