import {hwContainer, hwNarrowContainer} from "./hardwoodStyles";

const block = "rounded bg-hw-surface-muted animate-pulse motion-reduce:animate-none";

// Neutral box-score-shaped placeholder: no dates, logos, or team names, so a
// finished game never flashes something that reads like an upcoming matchup.
function HardwoodBoxscoreSkeleton() {
  return (
    <div role="status">
      <span className="sr-only">Loading</span>
      <div aria-hidden="true">
        <section className={`${hwNarrowContainer} mt-[46px] mb-[60px]`}>
          <div className={`${block} mx-auto h-3.5 w-28`} />
          <div className="mt-6 grid grid-cols-2 gap-px border border-hw-line bg-hw-line">
            {[0, 1].map((team) => (
              <div key={team} className="flex items-center justify-between gap-[18px] bg-hw-surface px-5 py-[34px] max-[700px]:flex-col max-[700px]:px-2.5 max-[700px]:py-[25px]">
                <div className={`${block} size-[70px] rounded-full max-[700px]:size-[52px]`} />
                <div className={`${block} h-[clamp(3rem,8vw,6rem)] w-[clamp(4.5rem,12vw,9rem)]`} />
              </div>
            ))}
          </div>
        </section>
        <section className={`${hwContainer} mb-20 grid gap-4 min-[1280px]:grid-cols-2`}>
          {[0, 1].map((team) => (
            <div key={team} className={`rounded-hw border border-hw-line bg-hw-surface p-5 ${team === 1 ? "max-[1279px]:hidden" : ""}`}>
              <div className={`${block} mb-5 h-4 w-40`} />
              <div className="grid gap-3.5">
                {Array.from({length: 8}, (_, row) => (
                  <div key={row} className="grid grid-cols-[minmax(0,2fr)_repeat(4,minmax(0,1fr))] gap-3">
                    {Array.from({length: 5}, (_, cell) => <div key={cell} className={`${block} h-3.5`} />)}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}

export default HardwoodBoxscoreSkeleton;
