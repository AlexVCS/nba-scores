import type {AlternateDesignId, DesignDefinition, DesignId} from "./types";

export const DESIGN_DEFINITIONS: readonly DesignDefinition[] = [
  {id: "original", number: null, name: "Original Scorez", shortName: "Original", themeClass: "design-original"},
  {id: "design-1", number: 1, name: "Hardwood Playbook", shortName: "Playbook", themeClass: "design-playbook"},
  {id: "design-2", number: 2, name: "The Radar", shortName: "Radar", themeClass: "design-radar"},
  {id: "design-3", number: 3, name: "The Marquee", shortName: "Marquee", themeClass: "design-marquee"},
  {id: "design-4", number: 4, name: "Gold on Hardwood", shortName: "Hardwood", themeClass: "design-hardwood"},
] as const;

export const ALTERNATE_DESIGNS = DESIGN_DEFINITIONS.filter(
  (design): design is DesignDefinition & {id: AlternateDesignId} => design.id !== "original",
);

export const getDesignDefinition = (id: DesignId): DesignDefinition =>
  DESIGN_DEFINITIONS.find((design) => design.id === id) ?? DESIGN_DEFINITIONS[0];
