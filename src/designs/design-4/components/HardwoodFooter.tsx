import type {ReactNode} from "react";
import {hwContainer} from "./hardwoodStyles";

interface HardwoodFooterProps {
  detail?: ReactNode;
}

function HardwoodFooter({detail}: HardwoodFooterProps) {
  return (
    <footer className={`${hwContainer} flex min-h-[90px] items-center justify-between border-t border-hw-line pb-0 text-[9px] font-bold tracking-[.22em] text-hw-court uppercase max-[700px]:pb-[70px]`}>
      <span>NBA SCOREZ</span>
      {detail && <span>{detail}</span>}
    </footer>
  );
}

export default HardwoodFooter;
