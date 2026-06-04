import type { ViewportSize } from '@/hooks/useViewportSize';

export type BracketSizing = {
  nodeWidth: number;
  logoSize: number;
  hSpacing: number;
  vSpacing: number;
  tricodeClass: string;
  scoreClass: string;
  rowPadClass: string;
  rowGapClass: string;
  logoPadClass: string;
  canvasHeight: string;
};

export const bracketSizing: Record<ViewportSize, BracketSizing> = {
  sm: {
    nodeWidth: 88,
    logoSize: 18,
    hSpacing: 96,
    vSpacing: 54,
    tricodeClass: 'text-[10px]',
    scoreClass: 'text-[10px]',
    rowPadClass: 'px-1 py-0.5',
    rowGapClass: 'gap-1',
    logoPadClass: 'p-0',
    canvasHeight: '200px',
  },
  md: {
    nodeWidth: 150,
    logoSize: 28,
    hSpacing: 170,
    vSpacing: 110,
    tricodeClass: 'text-base',
    scoreClass: 'text-base',
    rowPadClass: 'px-2 py-1',
    rowGapClass: 'gap-2',
    logoPadClass: 'p-0.5',
    canvasHeight: '380px',
  },
  lg: {
    nodeWidth: 250,
    logoSize: 48,
    hSpacing: 270,
    vSpacing: 200,
    tricodeClass: 'text-2xl',
    scoreClass: 'text-2xl',
    rowPadClass: 'p-3',
    rowGapClass: 'gap-3',
    logoPadClass: 'p-1',
    canvasHeight: '75vh',
  },
};
