import { useState, useEffect } from 'react';

export type ViewportSize = 'sm' | 'md' | 'lg';

function getSize(width: number): ViewportSize {
  if (width < 640) return 'sm';
  if (width < 1024) return 'md';
  return 'lg';
}

export function useViewportSize(): ViewportSize {
  const [size, setSize] = useState<ViewportSize>(() =>
    typeof window === 'undefined' ? 'lg' : getSize(window.innerWidth)
  );

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const onResize = () => {
      clearTimeout(timer);
      timer = setTimeout(() => setSize(getSize(window.innerWidth)), 150);
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      clearTimeout(timer);
    };
  }, []);

  return size;
}
