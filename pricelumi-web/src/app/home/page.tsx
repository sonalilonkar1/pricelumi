import Link from "next/link";

const recentlyReviewed = [
  { id: "house-blend", name: "House Blend Coffee", tone: "from-[#E8CFA8] to-[#B98A5B]" },
  { id: "hydrating-toner", name: "Hydrating Toner", tone: "from-[#F3E6D3] to-[#D9B98F]" },
  { id: "noise-cancelling-headphones", name: "Noise-Cancelling Headphones", tone: "from-[#EAD9C6] to-[#C9A98A]" },
  { id: "sunny-pals", name: "Sunny Pals Blind Box", tone: "from-[#F2DCC4] to-[#D8A77E]" },
];

const iconClass = "h-7 w-7 sm:h-8 sm:w-8";

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={iconClass} aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="10" r="3.5" />
      <path d="M5.5 19c1.5-3 4-4 6.5-4s5 1 6.5 4" />
    </svg>
  );
}

function CartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={iconClass} aria-hidden="true">
      <path d="M2 4h3l2.5 11h11L21 7H6" />
      <circle cx="9" cy="19.5" r="1" />
      <circle cx="17" cy="19.5" r="1" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={iconClass} aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h0a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6" aria-hidden="true">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v4" />
    </svg>
  );
}

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#F97B45]";

export default function HomePage() {
  return (
    <div className="min-h-dvh bg-[#F4F8FB] font-[family-name:var(--font-poppins)] text-[#1B2230]">
      {/* Top bar */}
      <header className="bg-[#1B2230] text-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:h-20 sm:px-8 lg:px-12">
          <nav aria-label="Main" className="flex items-center gap-5 sm:gap-10">
            <Link href="/home" className={`text-lg font-semibold sm:text-xl ${focusRing}`}>
              LOGO
            </Link>
            <Link href="/orders" className={`text-base uppercase sm:text-lg ${focusRing}`}>
              Orders
            </Link>
          </nav>
          <div className="flex items-center gap-4 sm:gap-8">
            <Link href="/account" aria-label="Account" className={focusRing}>
              <UserIcon />
            </Link>
            <Link href="/cart" aria-label="Cart" className={focusRing}>
              <CartIcon />
            </Link>
            <Link href="/settings" aria-label="Settings" className={focusRing}>
              <SettingsIcon />
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-8 lg:px-12">
        {/* Search */}
        <section className="pb-10 pt-10 text-center sm:pb-16 sm:pt-16 lg:pb-24">
          <h1 className="font-[family-name:var(--font-montserrat)] text-2xl font-extrabold uppercase tracking-tight sm:text-4xl lg:text-5xl">
            What are you looking for today?
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-base font-medium sm:mt-4 sm:text-xl">
            Tell our AI what you need, and we&rsquo;ll find the best option for you.
          </p>

          <form
            action="/results"
            method="get"
            role="search"
            className="mx-auto mt-8 flex max-w-5xl flex-col gap-3 sm:mt-10 sm:flex-row sm:gap-5"
          >
            <div className="relative flex-1">
              <label htmlFor="q" className="sr-only">
                What are you shopping for?
              </label>
              <input
                id="q"
                name="q"
                type="text"
                placeholder="e.g. Wireless headphone with noise reduction under $200"
                className={`h-12 w-full rounded-2xl bg-[#DCE4F3] pl-5 pr-14 text-sm placeholder:text-[#7C8799] sm:h-14 sm:text-base ${focusRing}`}
              />
              <button
                type="button"
                aria-label="Search by voice"
                className={`absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-[#1B2230] ${focusRing}`}
              >
                <MicIcon />
              </button>
            </div>
            <button
              type="submit"
              className={`h-12 rounded-2xl bg-[#F97B45] px-8 text-sm font-semibold uppercase tracking-wide text-white transition-colors hover:bg-[#E56A35] sm:h-14 sm:text-base ${focusRing}`}
            >
              Search
            </button>
          </form>
        </section>

        {/* Recently reviewed */}
        <section aria-labelledby="recent-heading" className="pb-12">
          <h2
            id="recent-heading"
            className="font-[family-name:var(--font-montserrat)] text-xl font-bold uppercase sm:text-2xl"
          >
            Recently reviewed
          </h2>

          <ul className="-mx-4 mt-5 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-4 sm:-mx-8 sm:gap-6 sm:px-8 lg:-mx-12 lg:px-12">
            {recentlyReviewed.map((item) => (
              <li key={item.id} className="w-64 flex-none snap-start sm:w-72 lg:w-80">
                {/* Replace the gradient with <Image> once product photos are in /public */}
                <div
                  className={`flex aspect-[3/4] items-end rounded-3xl bg-gradient-to-br ${item.tone} p-5`}
                >
                  <span className="text-lg font-semibold text-[#1B2230]">{item.name}</span>
                </div>
                <Link
                  href={`/reviews/${item.id}`}
                  className={`-mt-6 relative mx-auto flex h-11 w-4/5 items-center justify-center rounded-2xl bg-[#88A5DC] text-sm font-semibold text-[#1B2230] transition-colors hover:bg-[#7494CF] ${focusRing}`}
                >
                  View review
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}