import type {AlternateDesignId, DesignDefinition, DesignId} from "./types";

export const DESIGN_DEFINITIONS: readonly DesignDefinition[] = [
  {id: "original", number: null, name: "Original Scorez", shortName: "Original", themeClass: "design-original"},
  {id: "design-1", number: 1, name: "Courtside Ledger", shortName: "Ledger", themeClass: "design-ledger"},
  {id: "design-2", number: 2, name: "Broadcast ’96", shortName: "Broadcast", themeClass: "design-broadcast"},
  {id: "design-3", number: 3, name: "Tunnel Club", shortName: "Tunnel", themeClass: "design-tunnel"},
  {id: "design-4", number: 4, name: "Hardwood Playbook", shortName: "Playbook", themeClass: "design-playbook"},
  {id: "design-5", number: 5, name: "Swiss Stat Lab", shortName: "Stat Lab", themeClass: "design-statlab"},
] as const;

export const ALTERNATE_DESIGNS = DESIGN_DEFINITIONS.filter(
  (design): design is DesignDefinition & {id: AlternateDesignId} => design.id !== "original",
);

export const getDesignDefinition = (id: DesignId): DesignDefinition =>
  DESIGN_DEFINITIONS.find((design) => design.id === id) ?? DESIGN_DEFINITIONS[0];
