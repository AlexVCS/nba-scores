import type {ReactNode} from "react";

interface HardwoodPageProps {
  children: ReactNode;
}

function HardwoodPage({children}: HardwoodPageProps) {
  return (
    <main className="relative isolate flex min-h-dvh flex-col overflow-x-clip bg-hw-page pb-20 font-hw-display text-hw-ink before:pointer-events-none before:fixed before:inset-0 before:-z-10 before:bg-[image:var(--hw-page-texture)] before:opacity-70 dark:before:opacity-100 max-[700px]:pb-[70px]">
      {children}
    </main>
  );
}

export default HardwoodPage;
