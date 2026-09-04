import type { ViewportSize } from '@/hooks/useViewportSize';

export type BracketSizing = {
  nodeWidth: number;
  finalsNodeWidth: number;
  historicalNodeWidth: number;
  historicalHSpacing: number;
  historicalVSpacing: number;
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
    finalsNodeWidth: 88,
    historicalNodeWidth: 88,
    historicalHSpacing: 96,
    historicalVSpacing: 54,
    logoSize: 18,
    hSpacing: 96,
    vSpacing: 54,
    tricodeClass: 'text-[10px]',
    scoreClass: 'text-[10px]',
    rowPadClass: 'px-1 py-0.5',
    rowGapClass: 'gap-1',
    logoPadClass: 'p-0',
    canvasHeight: '40vw',
  },
  md: {
    nodeWidth: 208,
    finalsNodeWidth: 220,
    historicalNodeWidth: 150,
    historicalHSpacing: 170,
    historicalVSpacing: 110,
    logoSize: 28,
    hSpacing: 220,
    vSpacing: 145,
    tricodeClass: 'text-base',
    scoreClass: 'text-base',
    rowPadClass: 'px-2 py-1',
    rowGapClass: 'gap-2',
    logoPadClass: 'p-0.5',
    canvasHeight: 'clamp(640px, 78vh, 720px)',
  },
  lg: {
    nodeWidth: 220,
    finalsNodeWidth: 240,
    historicalNodeWidth: 250,
    historicalHSpacing: 270,
    historicalVSpacing: 200,
    logoSize: 48,
    hSpacing: 232,
    vSpacing: 160,
    tricodeClass: 'text-2xl',
    scoreClass: 'text-2xl',
    rowPadClass: 'p-3',
    rowGapClass: 'gap-3',
    logoPadClass: 'p-1',
    canvasHeight: 'clamp(680px, 82vh, 760px)',
  },
};
