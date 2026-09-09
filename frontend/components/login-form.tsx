"use client";

import { useActionState } from "react";

import { authenticate, type AuthFormState } from "@/lib/auth/actions";

const initialState: AuthFormState = { error: null, message: null };

type LoginFormProps = {
  callbackError?: string;
  next?: string;
};

export function LoginForm({ callbackError, next }: LoginFormProps) {
  const [state, formAction, pending] = useActionState(authenticate, initialState);
  const error = state.error ?? callbackError ?? null;

  return (
    <form action={formAction} className="mt-8 w-full max-w-md">
      {next ? <input type="hidden" name="next" value={next} /> : null}
      <label htmlFor="email" className="block font-display text-sm text-cast-iron">
        Email
      </label>
      <input
        id="email"
        name="email"
        type="email"
        autoComplete="email"
        required
        className="mt-2 min-h-12 w-full rounded-none border border-cast-iron bg-phone-glow px-3 font-body text-[0.95rem] text-cast-iron placeholder:text-steam"
      />

      <label htmlFor="password" className="mt-5 block font-display text-sm text-cast-iron">
        Password
      </label>
      <input
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        minLength={6}
        className="mt-2 min-h-12 w-full rounded-none border border-cast-iron bg-phone-glow px-3 font-body text-[0.95rem] text-cast-iron placeholder:text-steam"
      />

      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <button
          type="submit"
          name="intent"
          value="login"
          disabled={pending}
          className="inline-flex min-h-12 items-center justify-center bg-turmeric px-6 font-display text-base font-semibold text-cast-iron disabled:opacity-60"
        >
          Log in
        </button>
        <button
          type="submit"
          name="intent"
          value="signup"
          disabled={pending}
          className="inline-flex min-h-12 items-center justify-center border border-cast-iron bg-transparent px-6 font-display text-base font-semibold text-cast-iron disabled:opacity-60"
        >
          Create account
        </button>
      </div>

      <p role="alert" className="mt-4 min-h-6 text-sm text-chili">
        {error}
      </p>
      {state.message ? (
        <p className="mt-1 text-sm text-cast-iron/85">{state.message}</p>
      ) : null}
    </form>
  );
}
