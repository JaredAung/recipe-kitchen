alter table public.recipes
  drop column if exists prep_time_minutes,
  drop column if exists cook_time_minutes,
  drop column if exists duration_seconds;
