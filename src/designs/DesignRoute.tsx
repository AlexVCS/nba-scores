import type {ReactNode} from "react";

interface DesignRouteProps {
  children: ReactNode;
}

function DesignRoute({children}: DesignRouteProps) {
  // 14px/1.5 is the base the pages were designed against; text without its own size inherits it.
  return (
    <div className="design-hardwood min-h-screen text-[14px] leading-[1.5] scheme-light dark:scheme-dark">
      {children}
    </div>
  );
}

export default DesignRoute;
