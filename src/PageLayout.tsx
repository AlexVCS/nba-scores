import {ReactNode} from "react";

const PageLayout: React.FC<{children: ReactNode}> = ({children}) => {
  return <div>{children}</div>;
};

export default PageLayout;
