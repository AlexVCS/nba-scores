import {useCallback, useEffect, useState} from "react";
import {
  Button,
  Calendar,
  CalendarCell,
  CalendarGrid,
  CalendarGridBody,
  CalendarGridHeader,
  CalendarHeaderCell,
  DateField,
  DateInput,
  DateSegment,
  Dialog,
  DialogTrigger,
  Modal,
  ModalOverlay,
  OverlayArrow,
  Popover,
} from "react-aria-components";
import type {DateValue} from "react-aria-components";
import {CalendarDate, getLocalTimeZone, parseDate, today} from "@internationalized/date";
import {Link, useSearchParams} from "react-router";
import {useGameDays} from "@/hooks/useGameDays";
import {hwContainer} from "./components/hardwoodStyles";

/** First night of the BAA/NBA: November 1, 1946. */
const MIN_DATE = new CalendarDate(1946, 11, 1);
const MIN_YEAR = MIN_DATE.year;
const YEARS_PER_PAGE = 9;

const calendarNavButton =
  "flex size-[34px] shrink-0 cursor-pointer items-center justify-center rounded-full border border-hw-ink/16 bg-transparent text-hw-court transition-colors duration-[160ms] [transition-timing-function:ease] hover:border-hw-accent hover:text-hw-accent data-disabled:cursor-default data-disabled:opacity-[.35] data-focus-visible:outline-2 data-focus-visible:outline-offset-2 data-focus-visible:outline-hw-accent motion-reduce:transition-none max-[700px]:size-10 [&_svg]:size-[15px]";
const travelOption =
  "cursor-pointer rounded-lg border border-transparent bg-transparent px-0 py-3 text-center text-[13px] font-semibold text-hw-ink tabular-nums data-hovered:bg-hw-ink/9 data-disabled:cursor-default data-disabled:bg-transparent data-disabled:text-[color-mix(in_srgb,var(--hw-muted)_45%,var(--hw-surface))] data-focus-visible:outline-2 data-focus-visible:outline-offset-2 data-focus-visible:outline-hw-accent";

const toJsDate = (date: CalendarDate) => new Date(date.year, date.month - 1, date.day);
const longDate = (date: CalendarDate) =>
  toJsDate(date).toLocaleDateString("en-US", {weekday: "long", month: "long", day: "numeric", year: "numeric"});
const yearPageStartFor = (year: number) =>
  MIN_YEAR + Math.floor((Math.max(year, MIN_YEAR) - MIN_YEAR) / YEARS_PER_PAGE) * YEARS_PER_PAGE;

function Chevron({direction}: {direction: "left" | "right" | "down"}) {
  const path = direction === "left" ? "M15 5l-7 7 7 7" : direction === "right" ? "M9 5l7 7-7 7" : "M6 9l6 6 6-6";
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={path} />
    </svg>
  );
}

function useIsNarrow() {
  const [isNarrow, setIsNarrow] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 700px)").matches,
  );
  useEffect(() => {
    const query = window.matchMedia("(max-width: 700px)");
    const onChange = (event: MediaQueryListEvent) => setIsNarrow(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return isNarrow;
}

type TravelView = "calendar" | "years" | "months";

function MarqueeDatePicker() {
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  const dateParam = searchParams.get("date") ?? "";
  const isNarrow = useIsNarrow();

  const now = today(getLocalTimeZone());
  const maxDate = now.add({years: 1});
  let selected: CalendarDate | null = null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateParam)) {
    try {
      selected = parseDate(dateParam);
    } catch {
      selected = null;
    }
  }
  const anchor = selected ?? now;
  const prevDate = anchor.subtract({days: 1});
  const nextDate = anchor.add({days: 1});
  const jsAnchor = toJsDate(anchor);
  const weekdayText = jsAnchor.toLocaleDateString("en-US", {weekday: "long"});
  const dateText = jsAnchor.toLocaleDateString("en-US", {month: "long", day: "numeric", year: "numeric"});
  const fullLabel = `${weekdayText}, ${dateText}`;

  const [isOpen, setIsOpen] = useState(false);
  const [fieldValue, setFieldValue] = useState<DateValue | null>(null);
  const [view, setView] = useState<TravelView>("calendar");
  const [focusedDate, setFocusedDate] = useState<CalendarDate>(anchor);
  const [pendingYear, setPendingYear] = useState(anchor.year);
  const [yearPageStart, setYearPageStart] = useState(() => yearPageStartFor(anchor.year));
  const [traveled, setTraveled] = useState(false);

  const {gameDays, isLoading: gameDaysLoading} = useGameDays(focusedDate.year, focusedDate.month);

  const isDateUnavailable = useCallback(
    (date: DateValue): boolean => {
      if (gameDaysLoading) return false;
      return !gameDays.has(date.toString());
    },
    [gameDays, gameDaysLoading],
  );

  const inRange = useCallback(
    (date: DateValue) => date.compare(MIN_DATE) >= 0 && date.compare(maxDate) <= 0,
    [maxDate],
  );

  const goToDate = (date: DateValue) => {
    setSearchParams({date: date.toString()});
    setIsOpen(false);
  };

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (open) {
      setFieldValue(selected);
      setFocusedDate(anchor);
      setView("calendar");
      setPendingYear(anchor.year);
      setYearPageStart(yearPageStartFor(anchor.year));
      setTraveled(false);
    }
  };

  const handleFieldChange = (value: DateValue | null) => {
    const previous = fieldValue;
    setFieldValue(value);
    // Commit when typing first reaches a complete in-range date; an already
    // complete (seeded) field commits on Enter instead, so segment edits
    // don't navigate mid-thought.
    if (value && inRange(value) && (previous === null || !inRange(previous))) {
      goToDate(value);
    }
  };

  const handleFieldKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && fieldValue && inRange(fieldValue)) {
      event.preventDefault();
      goToDate(fieldValue);
    }
  };

  const openYearTravel = () => {
    setPendingYear(focusedDate.year);
    setYearPageStart(yearPageStartFor(focusedDate.year));
    setView("years");
  };

  const pickMonth = (month: number) => {
    let next = new CalendarDate(pendingYear, month, 1);
    if (next.compare(MIN_DATE) < 0) next = MIN_DATE;
    if (next.compare(maxDate) > 0) next = new CalendarDate(maxDate.year, maxDate.month, 1);
    setFocusedDate(next);
    setTraveled(true);
    setView("calendar");
  };

  const monthLabel = toJsDate(focusedDate).toLocaleDateString("en-US", {month: "long", year: "numeric"});
  const yearPageEnd = Math.min(yearPageStart + YEARS_PER_PAGE - 1, maxDate.year);
  const monthNames = Array.from({length: 12}, (_, index) =>
    new Date(2026, index, 1).toLocaleDateString("en-US", {month: "short"}),
  );

  const pickerDialog = (
    <Dialog className="p-5 pb-[18px] outline-none max-[700px]:p-0" aria-label="Choose a date">
      <div className="flex items-center gap-2.5 rounded-hw border border-hw-line bg-hw-surface-muted px-3.5 py-2.5 text-hw-ink transition-shadow duration-[160ms] [transition-timing-function:ease] focus-within:shadow-[0_0_0_2px_var(--hw-accent)] motion-reduce:transition-none" role="presentation">
        <DateField
          value={fieldValue}
          onChange={handleFieldChange}
          onKeyDown={handleFieldKeyDown}
          minValue={MIN_DATE}
          maxValue={maxDate}
          shouldForceLeadingZeros
          aria-label="Go to date"
          className="min-w-0 flex-1"
        >
          <DateInput className="flex items-center text-[15px] font-semibold tabular-nums">
            {(segment) => (
              <DateSegment
                segment={segment}
                className="rounded-sm px-[3px] py-px not-italic caret-transparent outline-none data-[type=literal]:px-0.5 data-[type=literal]:text-hw-muted data-placeholder:text-hw-muted data-focused:bg-hw-accent data-focused:font-extrabold data-focused:text-hw-accent-contrast"
              />
            )}
          </DateInput>
        </DateField>
        <svg
          className="size-4 shrink-0 text-hw-muted"
          aria-hidden="true"
          focusable="false"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M3 10h18M8 3v4M16 3v4" />
        </svg>
      </div>
      <p className="mx-0.5 mt-2 text-xs font-semibold text-hw-muted">Type any date back to 1946 — Enter to go</p>
      <div className="my-4 -mx-5 h-px bg-hw-line max-[700px]:-mx-4" role="presentation" />

      <div className="min-h-[300px] w-[292px] max-[700px]:min-h-0 max-[700px]:w-full">
        {view === "calendar" && (
          <Calendar
            value={selected}
            onChange={goToDate}
            focusedValue={focusedDate}
            onFocusChange={setFocusedDate}
            isDateUnavailable={isDateUnavailable}
            minValue={MIN_DATE}
            maxValue={maxDate}
            autoFocus={traveled}
            aria-label="Calendar"
          >
            <header className="mb-3 flex items-center justify-between gap-2">
              <Button
                slot={null}
                className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-hw-line bg-hw-surface-muted px-[11px] py-[7px] text-sm font-extrabold tracking-[.06em] text-hw-ink uppercase transition-colors duration-[160ms] [transition-timing-function:ease] hover:border-hw-accent data-focus-visible:outline-2 data-focus-visible:outline-offset-2 data-focus-visible:outline-hw-accent motion-reduce:transition-none [&_svg]:size-[13px] [&_svg]:text-hw-accent"
                onPress={openYearTravel}
                aria-label={`Choose month and year, currently ${monthLabel}`}
              >
                {monthLabel}
                <Chevron direction="down" />
              </Button>
              <div className="flex gap-2">
                <Button slot="previous" className={calendarNavButton} aria-label="Previous month">
                  <Chevron direction="left" />
                </Button>
                <Button slot="next" className={calendarNavButton} aria-label="Next month">
                  <Chevron direction="right" />
                </Button>
              </div>
            </header>
            <CalendarGrid weekdayStyle="short" className="mx-auto border-separate [border-spacing:3px]">
              <CalendarGridHeader>
                {(day) => <CalendarHeaderCell className="pb-1 text-[11px] font-semibold text-hw-muted">{day.slice(0, 2)}</CalendarHeaderCell>}
              </CalendarGridHeader>
              <CalendarGridBody>
                {(date) => (
                  <CalendarCell
                    date={date}
                    className="flex size-9 cursor-pointer items-center justify-center rounded-full text-[13px] text-hw-ink outline-none data-hovered:bg-hw-ink/9 data-outside-month:invisible data-unavailable:cursor-default data-unavailable:text-[color-mix(in_srgb,var(--hw-muted)_62%,var(--hw-surface))] data-unavailable:line-through data-unavailable:data-hovered:bg-transparent data-disabled:cursor-default data-disabled:text-[color-mix(in_srgb,var(--hw-muted)_45%,var(--hw-surface))] data-selected:bg-hw-accent data-selected:font-extrabold data-selected:text-hw-accent-contrast data-focus-visible:outline-2 data-focus-visible:outline-offset-2 data-focus-visible:outline-hw-accent max-[700px]:size-10 max-[700px]:text-sm"
                  />
                )}
              </CalendarGridBody>
            </CalendarGrid>
          </Calendar>
        )}

        {view === "years" && (
          <div>
            <div className="mb-3 flex items-center justify-between gap-2">
              <Button
                className={calendarNavButton}
                onPress={() => setYearPageStart((start) => Math.max(MIN_YEAR, start - YEARS_PER_PAGE))}
                isDisabled={yearPageStart <= MIN_YEAR}
                aria-label="Earlier years"
              >
                <Chevron direction="left" />
              </Button>
              <span className="flex-1 text-center text-[13px] font-extrabold tracking-[.14em] text-hw-ink uppercase tabular-nums">
                {yearPageStart} – {yearPageEnd}
              </span>
              <Button
                className={calendarNavButton}
                onPress={() => setYearPageStart((start) => start + YEARS_PER_PAGE)}
                isDisabled={yearPageStart + YEARS_PER_PAGE > maxDate.year}
                aria-label="Later years"
              >
                <Chevron direction="right" />
              </Button>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {Array.from({length: YEARS_PER_PAGE}, (_, index) => yearPageStart + index).map((year) => (
                <Button
                  key={year}
                  className={`${travelOption} ${year === anchor.year ? "bg-hw-accent font-extrabold text-hw-accent-contrast" : ""}`}
                  isDisabled={year > maxDate.year}
                  autoFocus={year === pendingYear}
                  onPress={() => {
                    setPendingYear(year);
                    setView("months");
                  }}
                >
                  {year}
                </Button>
              ))}
            </div>
          </div>
        )}

        {view === "months" && (
          <div>
            <div className="mb-3 flex items-center justify-between gap-2">
              <Button className={calendarNavButton} onPress={() => setView("years")} aria-label="Back to years">
                <Chevron direction="left" />
              </Button>
              <span className="flex-1 text-center text-[13px] font-extrabold tracking-[.14em] text-hw-ink uppercase tabular-nums">{pendingYear}</span>
              <span className="w-[34px] shrink-0 max-[700px]:w-10" aria-hidden="true" />
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {monthNames.map((name, index) => {
                const month = index + 1;
                const monthStart = new CalendarDate(pendingYear, month, 1);
                const monthEnd = monthStart.add({months: 1}).subtract({days: 1});
                const disabled = monthEnd.compare(MIN_DATE) < 0 || monthStart.compare(maxDate) > 0;
                const isCurrent = pendingYear === anchor.year && month === anchor.month;
                return (
                  <Button
                    key={name}
                    className={`${travelOption} text-xs font-extrabold tracking-[.06em] uppercase ${isCurrent ? "bg-hw-accent text-hw-accent-contrast" : ""}`}
                    isDisabled={disabled}
                    autoFocus={month === (pendingYear === focusedDate.year ? focusedDate.month : 1)}
                    onPress={() => pickMonth(month)}
                  >
                    {name}
                  </Button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );

  const stepButton =
    "flex size-12 items-center justify-center rounded-full border border-hw-ink/16 bg-hw-ink/4 text-hw-accent-ink transition-colors duration-[160ms] [transition-timing-function:ease] group-hover:border-hw-accent group-hover:bg-hw-accent/10 group-focus-visible:outline-2 group-focus-visible:outline-offset-3 group-focus-visible:outline-hw-accent motion-reduce:transition-none max-[700px]:size-11 max-[700px]:border-hw-accent/40 max-[700px]:bg-hw-accent/6 [&_svg]:size-5";
  const marqueeDate =
    "relative inline-block text-inherit text-balance after:absolute after:right-[.04em] after:bottom-[-.16em] after:left-[.04em] after:h-[3px] after:rounded-sm after:bg-hw-accent after:opacity-55 after:transition-opacity after:duration-[160ms] group-hover:after:opacity-100 group-aria-expanded:after:opacity-100 group-data-focus-visible:after:h-[5px] group-data-focus-visible:after:opacity-100 motion-reduce:after:transition-none";

  return (
    <section className={`${hwContainer} flex items-center justify-center gap-[clamp(20px,4vw,48px)] pt-[clamp(34px,6vw,78px)] pb-7 max-[700px]:grid max-[700px]:grid-cols-[44px_minmax(0,1fr)_44px] max-[700px]:gap-[clamp(10px,3vw,20px)] max-[700px]:pt-[38px]`}>
      <Link
        className="group flex shrink-0 items-center gap-[9px] text-hw-court no-underline outline-none max-[700px]:justify-center"
        to={`?date=${prevDate.toString()}`}
        aria-label={`Previous day — ${longDate(prevDate)}`}
      >
        <span className={stepButton}><Chevron direction="left" /></span>
        <small className="hidden text-[10px] font-semibold tracking-[.14em] uppercase" aria-hidden="true">
          {toJsDate(prevDate).toLocaleDateString("en-US", {weekday: "short", day: "numeric"})}
        </small>
      </Link>

      <h1 className="m-0 min-w-0 text-center text-[clamp(2rem,5vw,4.8rem)] leading-[1.04] font-extrabold tracking-[-.02em] uppercase max-[700px]:w-full max-[700px]:leading-[1.08]">
        <DialogTrigger isOpen={isOpen} onOpenChange={handleOpenChange}>
          <Button
            className="group inline-block cursor-pointer border-0 bg-transparent px-0 pb-[.18em] text-center text-inherit uppercase outline-none [font:inherit] [letter-spacing:inherit] [line-height:inherit] dark:text-hw-accent data-focus-visible:rounded-md data-focus-visible:outline-3 data-focus-visible:outline-offset-[12px] data-focus-visible:outline-hw-accent/75"
            aria-label={dateParam ? `Change date — ${fullLabel}` : "Choose a date"}
          >
            {dateParam ? (
              <>
                <span className="block text-inherit">{weekdayText},</span>
                <span className={marqueeDate}>{dateText}</span>
              </>
            ) : (
              <span className={marqueeDate}>Tonight’s games</span>
            )}
          </Button>
          {isNarrow ? (
            /* Portals carry the scope because react-aria mounts them under document.body. */
            <ModalOverlay className="design-hardwood group fixed inset-0 z-[130] flex items-end bg-black/50 font-hw-display text-hw-ink data-entering:animate-hw-fade-in data-exiting:animate-hw-fade-out motion-reduce:data-entering:animate-none motion-reduce:data-exiting:animate-none" isDismissable>
              <Modal className="w-full rounded-t-2xl border border-b-0 border-hw-line bg-hw-surface px-4 pt-2.5 pb-[calc(18px+env(safe-area-inset-bottom))] group-data-entering:animate-hw-sheet-up motion-reduce:group-data-entering:animate-none">
                <div className="mx-auto mb-3.5 h-1 w-9 rounded-sm bg-hw-ink/25" role="presentation" />
                {pickerDialog}
              </Modal>
            </ModalOverlay>
          ) : (
            /* Portals carry the scope because react-aria mounts them under document.body. */
            <Popover
              className="design-hardwood overflow-y-auto overscroll-contain rounded-hw border border-hw-line bg-hw-surface font-hw-display text-hw-ink shadow-hw-card [scrollbar-gutter:stable] data-entering:animate-hw-pop-in data-exiting:animate-hw-pop-out motion-reduce:data-entering:animate-none motion-reduce:data-exiting:animate-none"
              placement="bottom"
              offset={20}
              containerPadding={12}
              shouldFlip={false}
            >
              <OverlayArrow className="[&>div]:size-[13px] [&>div]:translate-y-[-6.5px] [&>div]:rotate-45 [&>div]:border-t [&>div]:border-l [&>div]:border-hw-line [&>div]:bg-hw-surface">
                <div />
              </OverlayArrow>
              {pickerDialog}
            </Popover>
          )}
        </DialogTrigger>
      </h1>

      <Link
        className="group flex shrink-0 items-center gap-[9px] text-hw-court no-underline outline-none max-[700px]:justify-center"
        to={`?date=${nextDate.toString()}`}
        aria-label={`Next day — ${longDate(nextDate)}`}
      >
        <span className={stepButton}><Chevron direction="right" /></span>
        <small className="hidden text-[10px] font-semibold tracking-[.14em] uppercase" aria-hidden="true">
          {toJsDate(nextDate).toLocaleDateString("en-US", {weekday: "short", day: "numeric"})}
        </small>
      </Link>
    </section>
  );
}

export default MarqueeDatePicker;
