interface HardwoodWinnerArrowProps {
  className?: string;
}

function HardwoodWinnerArrow({className = ""}: HardwoodWinnerArrowProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 7 12"
      aria-hidden="true"
      className={`inline-block h-[.32em] w-[.19em] rotate-180 ${className}`}
    >
      <path fill="currentColor" fillRule="nonzero" d="M.5 6l6 5.5V.5z" />
    </svg>
  );
}

export default HardwoodWinnerArrow;
