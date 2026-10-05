interface AskHiddenValueProps {
  width?: number;
}

/** Stand-in for a protected value. The real value is never passed here, so it cannot reach the DOM. */
function AskHiddenValue({width = 34}: AskHiddenValueProps) {
  return (
    <span className="inline-flex items-center">
      <span
        className="inline-block h-[.9em] rounded border border-hw-line bg-[repeating-linear-gradient(-45deg,var(--hw-line)_0_4px,var(--hw-surface-muted)_4px_8px)] align-[-1px]"
        style={{width}}
        aria-hidden="true"
      />
      <span className="sr-only">Hidden</span>
    </span>
  );
}

export default AskHiddenValue;
