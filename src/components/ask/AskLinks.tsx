import {Link, useLocation} from "react-router";
import {ArrowRight, ExternalLink} from "lucide-react";
import type {AskVerifiedLink} from "@/services/ask/types";
import {withDesignPrefix} from "./askRouting";
import {withoutSpoilers} from "./askSpoilers";
import {askButton, askPrimaryButton} from "./askStyles";

interface AskLinksProps {
  links: AskVerifiedLink[];
  resultsHidden: boolean;
  label?: string;
  compact?: boolean;
}

/**
 * Server-verified links. A link flagged as a spoiler would reveal a result the user did not ask for, so it is
 * left out entirely while results are hidden. Internal paths get the design prefix.
 */
function AskLinks({links, resultsHidden, label = "Related pages", compact = false}: AskLinksProps) {
  const {pathname} = useLocation();
  const visible = withoutSpoilers(links, !resultsHidden);
  if (visible.length === 0) return null;

  return (
    <nav aria-label={label} className={`flex flex-wrap items-center gap-2 ${compact ? "" : "max-[700px]:grid"}`}>
      {visible.map((link, index) => {
        const className = compact
          ? "inline-flex min-h-8 items-center gap-1 text-[10px] font-extrabold tracking-[.1em] uppercase underline-offset-3 hover:underline"
          : index === 0 ? askPrimaryButton : askButton;
        return link.external ? (
          <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer" className={className}>
            {link.label} <ExternalLink className="size-3" aria-hidden="true" />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        ) : (
          <Link key={link.href} to={withDesignPrefix(link.href, pathname)} className={className}>
            {link.label} {!compact && index === 0 && <ArrowRight className="size-[13px]" aria-hidden="true" />}
          </Link>
        );
      })}
    </nav>
  );
}

export default AskLinks;
