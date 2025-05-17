import { ReactNode } from "react";
import Header from "./components/Header";

const PageLayout: React.FC<{children: ReactNode}> = ({children}) => {
  return (
    <div className="bg-white text-black dark:bg-black dark:text-white">
      <Header />
      {children}
    </div>
  );
};

export default PageLayout;
