// Search tokens inherit the active design and fall back to the original palette.
export const ASK_ROOT =
  "@container [--ask-surface:var(--hw-surface,#fff)] [--ask-muted-surface:var(--hw-surface-muted,#f1f5f9)] [--ask-ink:var(--hw-ink,#131210)] [--ask-muted:var(--hw-muted,#5f574a)] [--ask-line:var(--hw-line,#cbd5e1)] [--ask-accent:var(--hw-accent,#d7a500)] [--ask-link:var(--hw-accent-ink,#6f5000)] dark:[--ask-surface:var(--hw-surface,#161815)] dark:[--ask-muted-surface:var(--hw-surface-muted,#101310)] dark:[--ask-ink:var(--hw-ink,#fff)] dark:[--ask-muted:var(--hw-muted,#b8c2b0)] dark:[--ask-line:var(--hw-line,#41463c)] dark:[--ask-accent:var(--hw-accent,#ffd524)] dark:[--ask-link:var(--hw-accent-ink,#ffd524)] text-[13px] text-[var(--ask-ink)] [font-family:var(--font-hw-display,Poppins,sans-serif)]";

export const ASK_FOCUS =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ask-accent)]";
export const ASK_BUTTON = `min-h-11 cursor-pointer [font-family:inherit] font-extrabold ${ASK_FOCUS}`;
export const ASK_PANEL =
  "relative overflow-hidden rounded-[10px] border border-[var(--ask-line)] bg-[var(--ask-surface)] shadow-[var(--hw-shadow-card,0_10px_26px_rgb(43_29_6/14%))]";
export const ASK_NOTICE = `${ASK_PANEL} p-5 leading-[1.55] [&>p:first-child]:max-w-[70ch] [&>p:first-child]:font-semibold`;
export const ASK_EXAMPLE = `${ASK_BUTTON} min-h-[34px] rounded-[7px] border border-[var(--ask-line)] bg-[var(--ask-surface)] px-[.7rem] py-[.35rem] text-[11px] leading-[1.25] text-[var(--ask-link)]`;
export const ASK_INTERPRETATION =
  "mt-3 flex flex-wrap items-center gap-[.3rem] text-[11px] leading-[1.4] text-[var(--ask-muted)] [&>span:first-child]:mr-[.15rem] [&>span:first-child]:font-extrabold [&>span:first-child]:tracking-[.1em] [&>span:first-child]:uppercase";
export const ASK_INTERPRETATION_CHIP = "not-last:after:ml-[.3rem] not-last:after:content-['·']";
export const ASK_REVEAL = `${ASK_BUTTON} col-start-3 row-start-1 inline-flex shrink-0 items-center gap-[.45rem] rounded-[7px] border-0 bg-[var(--ask-accent)] px-[.8rem] py-[.55rem] text-[10.4px] tracking-[.08em] text-[#131210] uppercase`;
export const ASK_PULSE = "animate-pulse rounded-[7px] bg-[var(--ask-line)] motion-reduce:animate-none";
export const ASK_VEIL =
  "mt-4 grid min-h-[118px] gap-[.7rem] rounded-[7px] bg-[var(--ask-muted-surface)] p-4";
export const ASK_VEIL_LINE = `${ASK_PULSE} block h-4 max-w-[75%] nth-2:max-w-[92%] nth-3:max-w-[55%]`;
export const ASK_STAT_FOCUS = "bg-[color-mix(in_srgb,var(--ask-accent)_18%,transparent)]";
export const ASK_TABLE_CELL =
  "flex min-h-[46px] items-center border-b border-[var(--ask-line)] px-[.8rem] py-[.65rem] text-left @[600px]:table-cell @[600px]:min-h-0 @[600px]:text-right";
export const ASK_TABLE_HEADER = `${ASK_TABLE_CELL} text-[10px] font-extrabold tracking-[.12em] text-[var(--ask-muted)] uppercase first:text-left`;
export const ASK_TABLE_VALUE = `${ASK_TABLE_CELL} ${ASK_STAT_FOCUS} col-span-full justify-between text-[13px] font-extrabold before:text-[10px] before:font-extrabold before:tracking-[.1em] before:text-[var(--ask-muted)] before:uppercase before:content-[attr(data-label)] @[600px]:text-base @[600px]:before:content-none`;
export const ASK_LINK = `${ASK_FOCUS} inline-flex min-h-12 items-center justify-center gap-[.35rem] rounded-[10px] border border-[var(--ask-line)] bg-[var(--ask-surface)] px-[.9rem] py-[.65rem] text-[11px] font-extrabold tracking-[.1em] text-[var(--ask-ink)] uppercase no-underline`;
