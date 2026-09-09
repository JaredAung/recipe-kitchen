"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { getAppOrigin, safeNextPath } from "@/lib/auth/paths";
import { createClient } from "@/lib/supabase/server";

export type AuthFormState = {
  error: string | null;
  message: string | null;
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function formFields(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const intent = String(formData.get("intent") ?? "login");
  const next = safeNextPath(String(formData.get("next") ?? "") || null);
  return { email, password, intent, next };
}

function authErrorMessage(message: string) {
  const lower = message.toLowerCase();
  if (lower.includes("invalid login")) {
    return "That email or password is not right.";
  }
  if (lower.includes("email not confirmed")) {
    return "Confirm this address from the email we sent.";
  }
  if (lower.includes("user already registered")) {
    return "An account with this email already exists. Log in instead.";
  }
  if (lower.includes("password should be")) {
    return "Use at least 6 characters for the password.";
  }
  return message;
}

export async function authenticate(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const { email, password, intent, next } = formFields(formData);

  if (!EMAIL_PATTERN.test(email)) {
    return { error: "Enter a valid email address.", message: null };
  }

  if (password.length < 6) {
    return { error: "Use at least 6 characters for the password.", message: null };
  }

  const supabase = await createClient();

  if (intent === "signup") {
    const origin = await getAppOrigin();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${origin}/auth/callback${next === "/" ? "" : `?next=${encodeURIComponent(next)}`}`,
      },
    });

    if (error) {
      return { error: authErrorMessage(error.message), message: null };
    }

    if (data.user?.identities && data.user.identities.length === 0) {
      return {
        error: "An account with this email already exists. Log in instead.",
        message: null,
      };
    }

    if (!data.session) {
      return {
        error: null,
        message: "Check your inbox to confirm this address, then log in.",
      };
    }

    revalidatePath("/", "layout");
    redirect(next);
  }

  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    return { error: authErrorMessage(error.message), message: null };
  }

  revalidatePath("/", "layout");
  redirect(next);
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  revalidatePath("/", "layout");
  redirect("/");
}
