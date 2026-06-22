import {Link, useSearchParams} from "react-router";

const routes = [
  {to: "/designs/scorez", label: "Studio"},
  {to: "/designs/scorez-arcade", label: "Arcade"},
  {to: "/designs/scorez-masonry", label: "Masonry"},
  {to: "/designs/scorez-coverflow", label: "Coverflow"},
  {to: "/designs/playoffz", label: "Control"},
  {to: "/designs/playoffz-map", label: "Transit"},
];

function RoutePatternNav() {
  const [searchParams] = useSearchParams();
  const dateParam = searchParams.get("date");
  const seasonParam = searchParams.get("season");

  const buildRouteTo = (to: string) => {
    if (to.includes("/scorez") && dateParam) return `${to}?date=${dateParam}`;
    if (to.includes("/playoffz") && seasonParam) return `${to}?season=${seasonParam}`;
    return to;
  };

  return (
    <div className="flex max-w-full flex-wrap items-center justify-end gap-2 text-xs font-black uppercase tracking-[0.14em]">
      {routes.map((route) => (
        <Link
          key={route.to}
          to={buildRouteTo(route.to)}
          className="rounded-full border border-current/20 px-3 py-1.5 transition-colors hover:bg-current/10 active:scale-[0.98]"
        >
          {route.label}
        </Link>
      ))}
    </div>
  );
}

export default RoutePatternNav;
