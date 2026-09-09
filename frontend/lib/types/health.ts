export type Health = {
  ok: boolean;
  supabase: boolean;
};

export type CurrentUser = {
  sub: string | null;
  role: string | null;
};
