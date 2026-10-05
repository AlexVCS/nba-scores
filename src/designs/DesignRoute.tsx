import {useEffect} from "react";
import type {ReactNode} from "react";
import DesignSwitcher from "./DesignSwitcher";
import {getDesignDefinition} from "./designRegistry";
import type {DesignId} from "./types";

interface DesignRouteProps {
  designId: DesignId;
  children: ReactNode;
}

function DesignRoute({designId, children}: DesignRouteProps) {
  const definition = getDesignDefinition(designId);

  useEffect(() => {
    const robotsMeta = document.querySelector<HTMLMetaElement>('meta[name="robots"]');
    const previousRobots = robotsMeta?.content;
    const createdRobots = robotsMeta ?? document.createElement("meta");

    createdRobots.name = "robots";
    createdRobots.content = "noindex, nofollow, noarchive";

    // No referrer meta: WebKit tabs opened from here inherit it and NBA.com event pages never load.
    if (!robotsMeta) document.head.appendChild(createdRobots);

    return () => {
      if (robotsMeta && previousRobots !== undefined) {
        robotsMeta.content = previousRobots;
      } else {
        createdRobots.remove();
      }
    };
  }, []);

  return (
    <div
      className={`design-route ${definition.themeClass}`}
      data-design={designId}
      data-design-name={definition.name}
    >
      <div className="design-route__content switcher:px-[66px]">{children}</div>
      <DesignSwitcher activeDesign={designId} />
    </div>
  );
}

export default DesignRoute;
