import {useCallback, useMemo, useSyncExternalStore} from "react";

const getServerSnapshot = () => false;

export default function useMediaQuery(query: string) {
  const mediaQuery = useMemo(
    () => typeof window === "undefined" ? undefined : window.matchMedia?.(query),
    [query],
  );
  const subscribe = useCallback((onChange: () => void) => {
    mediaQuery?.addEventListener("change", onChange);
    return () => mediaQuery?.removeEventListener("change", onChange);
  }, [mediaQuery]);
  const getSnapshot = useCallback(() => mediaQuery?.matches ?? false, [mediaQuery]);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
