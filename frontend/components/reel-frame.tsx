export function ReelFrame() {
  return (
    <figure className="reel-enter mx-auto w-full max-w-[19rem] origin-center">
      <div className="rounded-[2rem] bg-cast-iron p-3 shadow-[12px_28px_40px_-24px_rgba(20,24,26,0.55)]">
        <div
          className="relative flex aspect-[9/16] flex-col overflow-hidden rounded-[1.35rem] bg-[#8b9688]"
          role="img"
          aria-label="Example cooking reel of tomato garlic noodles"
        >
          <div className="flex items-center justify-between px-3.5 pt-3.5 text-phone-glow">
            <span className="font-display text-sm tracking-[0.04em]">reel</span>
            <span aria-hidden="true" className="text-lg leading-none">
              ···
            </span>
          </div>

          <div className="flex flex-1 items-center justify-center px-4">
            <svg viewBox="0 0 160 110" className="w-[78%]" aria-hidden="true">
              <ellipse cx="80" cy="62" rx="68" ry="36" fill="#1a1f21" />
              <circle cx="58" cy="56" r="16" fill="#8f3a28" />
              <circle cx="86" cy="48" r="14" fill="#a34430" />
              <rect x="108" y="52" width="11" height="11" rx="1.5" fill="#e3b23c" />
              <rect x="96" y="66" width="9" height="9" rx="1.5" fill="#d4a434" />
              <circle cx="118" cy="70" r="6" fill="#efe6c9" />
              <circle cx="44" cy="70" r="5" fill="#efe6c9" />
              <path
                d="M52 28c8-14 24-18 36-6"
                fill="none"
                stroke="#f3f6f8"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <path
                d="M92 24c10-12 24-10 32 2"
                fill="none"
                stroke="#f3f6f8"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>

          <div className="px-4 pb-4 text-phone-glow">
            <p className="font-body text-[1.35rem] leading-7">tomato garlic noodles</p>
            <p className="mt-1 font-myanmar text-[1.05rem] leading-7">
              ခရမ်းချဉ်သီး ခေါက်ဆွဲ
            </p>
            <div className="mt-4 flex items-center justify-between text-phone-glow/80">
              <HeartIcon />
              <BoltIcon />
              <ShareIcon />
            </div>
          </div>
        </div>
      </div>
      <figcaption className="mt-6 text-center font-display text-sm tracking-[0.02em] text-steam">
        A reel, before it becomes a recipe
      </figcaption>
    </figure>
  );
}

function HeartIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
      <path
        d="M12 20s-7-4.4-7-9.2C5 8 6.8 6.4 9 6.4c1.3 0 2.4.6 3 1.6.6-1 1.7-1.6 3-1.6 2.2 0 4 1.6 4 4.4 0 4.8-7 9.2-7 9.2Z"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  );
}

function BoltIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
      <path
        d="M13 3 6 14h6l-1 7 8-12h-6l1-6Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ShareIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
      <path
        d="M7 12v7h10v-7M12 4v12M8 8l4-4 4 4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
