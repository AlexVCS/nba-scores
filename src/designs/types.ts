export type DesignId = "original" | "design-1";

export type DesignPage = "scores" | "boxscore" | "playoffs" | "series";

export interface DesignDefinition {
  id: DesignId;
  number: number | null;
  name: string;
  shortName: string;
  themeClass: string;
}

export type AlternateDesignId = Exclude<DesignId, "original">;
