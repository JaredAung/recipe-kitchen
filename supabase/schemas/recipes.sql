-- Desired state of the recipe kitchen public schema.
-- Edit this file, then generate an incremental migration:
--   supabase db diff -f <change_name>
-- Review supabase/migrations/, then:
--   supabase db push

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.recipes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete cascade,

  title text,
  description text,
  cuisine text not null default 'burmese',
  tags text[] not null default '{}',

  prep_time_minutes integer
    constraint recipes_prep_time_nonnegative
      check (prep_time_minutes is null or prep_time_minutes >= 0),
  cook_time_minutes integer
    constraint recipes_cook_time_nonnegative
      check (cook_time_minutes is null or cook_time_minutes >= 0),
  total_time_minutes integer
    constraint recipes_total_time_nonnegative
      check (total_time_minutes is null or total_time_minutes >= 0),
  difficulty text not null default 'medium'
    check (difficulty in ('easy', 'medium', 'hard')),

  source_url text,
  original_filename text,
  duration_seconds numeric
    constraint recipes_duration_nonnegative
      check (duration_seconds is null or duration_seconds >= 0),
  video_path text,
  thumbnail_path text,

  transcript_my text,
  transcript_en text not null
    constraint recipes_transcript_en_not_empty
      check (char_length(trim(transcript_en)) > 0),
  caption_text text,

  channel_status jsonb not null default jsonb_build_object(
    'audio', 'idle',
    'caption', 'idle',
    'visual', 'idle'
  ),
  extraction_meta jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index recipes_user_id_idx on public.recipes (user_id);
create index recipes_created_at_idx on public.recipes (created_at desc);
create index recipes_tags_idx on public.recipes using gin (tags);

create trigger recipes_set_updated_at
before update on public.recipes
for each row
execute function public.set_updated_at();

create table public.recipe_ingredients (
  id uuid primary key default gen_random_uuid(),
  recipe_id uuid not null references public.recipes (id) on delete cascade,
  name text not null
    constraint recipe_ingredients_name_not_empty
      check (char_length(trim(name)) > 0),
  amount text not null default '',
  evidence text not null
    constraint recipe_ingredients_evidence_not_empty
      check (char_length(trim(evidence)) > 0),
  source text not null check (source in ('audio', 'caption', 'visual')),
  sort_order integer not null default 0,
  created_at timestamptz not null default now()
);

create index recipe_ingredients_recipe_id_idx
  on public.recipe_ingredients (recipe_id, sort_order);
create index recipe_ingredients_name_idx
  on public.recipe_ingredients (lower(name));

create table public.recipe_steps (
  id uuid primary key default gen_random_uuid(),
  recipe_id uuid not null references public.recipes (id) on delete cascade,
  step_order integer not null
    constraint recipe_steps_order_positive
      check (step_order >= 1),
  instruction text not null
    constraint recipe_steps_instruction_not_empty
      check (char_length(trim(instruction)) > 0),
  evidence text not null
    constraint recipe_steps_evidence_not_empty
      check (char_length(trim(evidence)) > 0),
  source text not null check (source in ('audio', 'caption', 'visual')),
  created_at timestamptz not null default now(),
  unique (recipe_id, source, step_order)
);

create index recipe_steps_recipe_id_idx
  on public.recipe_steps (recipe_id, source, step_order);

alter table public.recipes enable row level security;
alter table public.recipe_ingredients enable row level security;
alter table public.recipe_steps enable row level security;

create policy "Users can select own recipes"
  on public.recipes for select
  to authenticated
  using (auth.uid() = user_id);

create policy "Users can insert own recipes"
  on public.recipes for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "Users can update own recipes"
  on public.recipes for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can delete own recipes"
  on public.recipes for delete
  to authenticated
  using (auth.uid() = user_id);

create policy "Users can select own recipe ingredients"
  on public.recipe_ingredients for select
  to authenticated
  using (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_ingredients.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can insert own recipe ingredients"
  on public.recipe_ingredients for insert
  to authenticated
  with check (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_ingredients.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can update own recipe ingredients"
  on public.recipe_ingredients for update
  to authenticated
  using (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_ingredients.recipe_id
        and recipes.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_ingredients.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can delete own recipe ingredients"
  on public.recipe_ingredients for delete
  to authenticated
  using (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_ingredients.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can select own recipe steps"
  on public.recipe_steps for select
  to authenticated
  using (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_steps.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can insert own recipe steps"
  on public.recipe_steps for insert
  to authenticated
  with check (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_steps.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can update own recipe steps"
  on public.recipe_steps for update
  to authenticated
  using (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_steps.recipe_id
        and recipes.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_steps.recipe_id
        and recipes.user_id = auth.uid()
    )
  );

create policy "Users can delete own recipe steps"
  on public.recipe_steps for delete
  to authenticated
  using (
    exists (
      select 1 from public.recipes
      where recipes.id = recipe_steps.recipe_id
        and recipes.user_id = auth.uid()
    )
  );
