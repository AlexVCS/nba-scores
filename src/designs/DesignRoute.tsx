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
    const referrerMeta = document.querySelector<HTMLMetaElement>('meta[name="referrer"]');
    const previousRobots = robotsMeta?.content;
    const previousReferrer = referrerMeta?.content;
    const createdRobots = robotsMeta ?? document.createElement("meta");
    const createdReferrer = referrerMeta ?? document.createElement("meta");

    createdRobots.name = "robots";
    createdRobots.content = "noindex, nofollow, noarchive";
    createdReferrer.name = "referrer";
    createdReferrer.content = "no-referrer";

    if (!robotsMeta) document.head.appendChild(createdRobots);
    if (!referrerMeta) document.head.appendChild(createdReferrer);

    return () => {
      if (robotsMeta && previousRobots !== undefined) {
        robotsMeta.content = previousRobots;
      } else {
        createdRobots.remove();
      }

      if (referrerMeta && previousReferrer !== undefined) {
        referrerMeta.content = previousReferrer;
      } else {
        createdReferrer.remove();
      }
    };
  }, []);

  return (
    <div
      className={`design-route ${definition.themeClass}`}
      data-design={designId}
      data-design-name={definition.name}
    >
      <div className="design-route__content">{children}</div>
      <DesignSwitcher activeDesign={designId} />
    </div>
  );
}

export default DesignRoute;
