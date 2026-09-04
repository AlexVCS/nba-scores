import type {ReactNode, RefObject} from "react";
import {Link} from "react-router";
import {ChevronLeft} from "lucide-react";
import {hwContainer} from "./hardwoodStyles";

interface HardwoodBackRowProps {
  href: string;
  label: string;
  detail: ReactNode;
  linkRef?: RefObject<HTMLAnchorElement>;
}

function HardwoodBackRow({href, label, detail, linkRef}: HardwoodBackRowProps) {
  return (
    <div className={`${hwContainer} flex min-h-[60px] items-center justify-between border-b border-hw-line text-[10px] font-extrabold tracking-[.12em] text-hw-court uppercase`}>
      <Link className="inline-flex items-center gap-[5px] no-underline" to={href} ref={linkRef}>
        <ChevronLeft className="w-[15px]" aria-hidden="true" /> {label}
      </Link>
      <span>{detail}</span>
    </div>
  );
}

export default HardwoodBackRow;
