import {CalendarDays, Clock, CornerDownLeft, Search, Trophy} from "lucide-react";
import {askOptionId, type AskAction, type AskActionGroup} from "./askTypeahead";

interface AskActionListProps {
  listboxId: string;
  groups: AskActionGroup[];
  activeId: string | null;
  onActiveChange: (id: string) => void;
  onRun: (action: AskAction) => void;
  label: string;
}

const iconBox = "grid size-[26px] flex-none place-items-center rounded-[7px] border border-hw-line bg-hw-surface-muted text-hw-ink";

function ActionIcon({action}: {action: AskAction}) {
  switch (action.kind) {
    case "recent":
      return <Clock className="size-[15px] flex-none text-hw-muted" aria-hidden="true" />;
    case "game":
      return <span className={iconBox}><CalendarDays className="size-3.5" aria-hidden="true" /></span>;
    case "bracket":
      return <span className={iconBox}><Trophy className="size-3.5" aria-hidden="true" /></span>;
    case "ask":
      return (
        <span className="grid size-[26px] flex-none place-items-center rounded-[7px] bg-hw-accent text-hw-accent-contrast">
          <Search className="size-[13px]" aria-hidden="true" />
        </span>
      );
    case "example":
      return null;
  }
}

function ActionLabel({action}: {action: AskAction}) {
  if (action.kind === "ask") {
    return (
      <span className="min-w-0 flex-1">
        <span className="font-medium text-hw-muted">Ask </span>“{action.label}”
      </span>
    );
  }
  if (action.kind === "example") {
    return (
      <>
        <span className="w-[92px] flex-none text-[10px] font-extrabold tracking-[.12em] text-hw-muted uppercase max-[700px]:w-auto">{action.detail}</span>
        <span className="min-w-0 flex-1">{action.label}</span>
      </>
    );
  }
  return (
    <span className="min-w-0 flex-1">
      {action.label}
      {action.detail && action.kind !== "recent" && <span className="ml-1.5 text-xs font-medium text-hw-muted">{action.detail}</span>}
    </span>
  );
}

function AskActionList({listboxId, groups, activeId, onActiveChange, onRun, label}: AskActionListProps) {
  return (
    <div id={listboxId} role="listbox" aria-label={label} className="grid">
      {groups.map(group => {
        const headingId = `${listboxId}-group-${group.id}`;
        return (
          <div key={group.id} role="group" aria-labelledby={headingId} className="mb-1.5">
            <div id={headingId} role="presentation" className="mx-3 mt-3.5 mb-1.5 text-[10px] font-extrabold tracking-[.12em] text-hw-muted uppercase max-[700px]:mx-0">
              {group.label}
            </div>
            <div className={`grid ${group.id === "recent" ? "max-[700px]:flex max-[700px]:flex-wrap max-[700px]:gap-2" : ""} ${group.id === "examples" ? "max-[700px]:-mr-3.5 max-[700px]:flex max-[700px]:snap-x max-[700px]:gap-2.5 max-[700px]:overflow-x-auto max-[700px]:pr-3.5 max-[700px]:pb-1" : ""}`}>
              {group.actions.map(action => {
                const isActive = action.id === activeId;
                return (
                  <div
                    key={action.id}
                    id={askOptionId(listboxId, action.id)}
                    role="option"
                    aria-selected={isActive}
                    data-active={isActive || undefined}
                    data-kind={action.kind}
                    className={`flex min-h-11 cursor-pointer items-center gap-3 rounded-[9px] px-3 py-2 text-sm leading-snug font-semibold text-hw-ink data-active:bg-hw-surface-muted data-active:shadow-[inset_3px_0_0_var(--hw-accent)] ${action.kind === "recent" ? "max-[700px]:min-h-9 max-[700px]:rounded-full max-[700px]:border max-[700px]:border-hw-line max-[700px]:px-3 max-[700px]:py-1.5 max-[700px]:text-[13px] max-[700px]:font-bold" : ""} ${action.kind === "example" ? "max-[700px]:flex-[0_0_230px] max-[700px]:snap-start max-[700px]:flex-col max-[700px]:items-start max-[700px]:gap-2 max-[700px]:rounded-[12px] max-[700px]:border max-[700px]:border-hw-line max-[700px]:px-3.5 max-[700px]:py-3 max-[700px]:text-[13px]" : ""}`}
                    onPointerMove={() => {
                      if (!isActive) onActiveChange(action.id);
                    }}
                    // Keep focus in the search field so typing can continue after a click.
                    onMouseDown={event => event.preventDefault()}
                    onClick={() => onRun(action)}
                  >
                    <ActionIcon action={action} />
                    <ActionLabel action={action} />
                    {action.meta && <span className="text-xs font-medium whitespace-nowrap text-hw-muted max-[700px]:hidden">{action.meta}</span>}
                    {isActive && (
                      <span className="inline-flex items-center rounded-md border border-hw-line bg-hw-surface-muted px-[7px] py-[5px] text-hw-muted max-[700px]:hidden" aria-hidden="true">
                        <CornerDownLeft className="size-[11px]" />
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default AskActionList;
