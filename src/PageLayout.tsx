import { ReactNode } from "react";
import Header from "./components/Header";

const PageLayout:React.FC<{children: ReactNode}> = ({children}) => {
  return (
    <div>
      <Header />
      {children}
    </div>
  );
};

export default PageLayout;
