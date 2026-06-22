import {Switch} from "@adobe/react-spectrum";
import TeamLogos from "@/components/TeamLogos";
import {TEAM_COLORS} from "@/constants/teamColors";
import type {RenderSeries} from "@/utils/playoffBracketModel";

interface SeriesFeatureHeroProps {
  series: RenderSeries;
  season: string;
  isRevealed: boolean;
  onRevealChange: (value: boolean) => void;
}

function SeriesFeatureHero({
  series,
  season,
  isRevealed,
  onRevealChange,
}: SeriesFeatureHeroProps) {
  const [team1, team2] = series.teams;
  const team1Wins = team1 ? series.wins[team1.id] || 0 : 0;
  const team2Wins = team2 ? series.wins[team2.id] || 0 : 0;
  const team1Color = TEAM_COLORS[team1?.id ?? 0] ?? "#b45309";
  const team2Color = TEAM_COLORS[team2?.id ?? 0] ?? "#b45309";

  if (!team1 || !team2) return null;

  return (
    <section className="grid min-h-[72dvh] overflow-hidden rounded-[2rem] border border-amber-200 bg-[#fbf7ef] shadow-[0_30px_90px_-58px_rgba(180,83,9,0.55)] dark:border-amber-300/15 dark:bg-zinc-950/72 lg:grid-cols-[0.85fr_1.15fr]">
      <div className="flex flex-col justify-between gap-8 p-6 sm:p-8">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.28em] text-amber-700 dark:text-amber-300">
            Split-screen feature
          </p>
          <h2 className="mt-4 text-4xl font-black leading-none tracking-tighter md:text-6xl">
            {series.roundName}
          </h2>
          <p className="mt-5 max-w-[65ch] text-base leading-relaxed text-slate-700 dark:text-slate-300">
            {season} postseason matchup file. Results can stay concealed for
            spoiler-safe browsing or open into the full game ledger.
          </p>
        </div>

        <div className="grid gap-4">
          <div className="rounded-[1.5rem] border border-amber-200 bg-white/70 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] dark:border-amber-300/15 dark:bg-white/5">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
              Result mode
            </p>
            <div className="mt-3">
              <Switch isSelected={isRevealed} onChange={onRevealChange}>
                <span className="text-slate-950 dark:text-slate-50">
                  {isRevealed ? "Hide Results" : "Show Results"}
                </span>
              </Switch>
            </div>
          </div>
        </div>
      </div>

      <div
        className="relative grid place-items-center overflow-hidden p-6 sm:p-10"
        style={{
          background: `linear-gradient(135deg, ${team1Color}, rgba(39,39,42,0.88) 50%, ${team2Color})`,
        }}
      >
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.14)_1px,transparent_1px),linear-gradient(0deg,rgba(255,255,255,0.10)_1px,transparent_1px)] bg-[size:44px_44px] opacity-30" />
        <div className="relative grid w-full max-w-2xl gap-6">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 text-white">
            <div className="grid justify-items-start gap-3">
              <TeamLogos
                teamName={team1.name}
                teamId={team1.id}
                size={96}
                tricode={team1.tricode}
              />
              <p className="text-4xl font-black tracking-tighter">
                {team1.tricode}
              </p>
            </div>
            <div className="rounded-[1.5rem] border border-white/20 bg-white/12 px-5 py-4 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.16)] backdrop-blur">
              <p className="text-xs font-black uppercase tracking-[0.24em] text-white/70">
                Series
              </p>
              <p className="mt-2 font-mono text-5xl font-black tabular-nums">
                {isRevealed ? `${team1Wins}-${team2Wins}` : "VS"}
              </p>
            </div>
            <div className="grid justify-items-end gap-3 text-right">
              <TeamLogos
                teamName={team2.name}
                teamId={team2.id}
                size={96}
                tricode={team2.tricode}
              />
              <p className="text-4xl font-black tracking-tighter">
                {team2.tricode}
              </p>
            </div>
          </div>
          {isRevealed && series.winnerTeamTricode && (
            <div className="justify-self-center rounded-full border border-white/20 bg-white/12 px-5 py-2 text-sm font-black uppercase tracking-[0.2em] text-white backdrop-blur">
              {series.winnerTeamTricode} wins
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default SeriesFeatureHero;
