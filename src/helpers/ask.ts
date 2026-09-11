export interface AskField {
  label: string;
  value: string | number | null;
  spoiler: boolean;
}

export interface AskLink {
  label: string;
  path: string;
  spoiler: boolean;
}

export interface AskTeam {
  id: number;
  tricode: string;
  name: string;
}

export interface AskItem {
  kind: "game" | "statistic" | "series" | "postseason";
  title: string;
  title_spoiler: boolean;
  fields: AskField[];
  links: AskLink[];
  context?: string | null;
  teams?: AskTeam[];
  player_id?: number | null;
  game?: GameData | null;
}

export interface AskResponse {
  status:
    | "ok"
    | "unsupported"
    | "needs_clarification"
    | "not_found"
    | "unavailable";
  message?: string | null;
  items: AskItem[];
  interpretation?: string[];
}
import type {GameData} from "@/helpers/helpers";
