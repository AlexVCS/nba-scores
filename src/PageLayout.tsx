import {ReactNode} from "react";

const PageLayout: React.FC<{children: ReactNode}> = ({children}) => {
  return <div className="h-full">{children}</div>;
};

export default PageLayout;
