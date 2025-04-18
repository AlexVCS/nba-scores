const ArrowIconRight = () => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="7"
      height="12"
      viewBox="0 0 7 12"
      role="presentation"
      className="absolute -right-3 top-1/2 transform -translate-y-1/3 mt-1"
    >
      <path fill="currentColor" fill-rule="nonzero" d="M.5 6l6 5.5V.5z"></path>
    </svg>
  );
}

const ArrowIconLeft = () => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="7"
      height="12"
      viewBox="0 0 7 12"
      role="presentation"
      className="absolute -left-3 top-1/2 transform -translate-y-1/3 mt-1 rotate-180"
    >
      <path fill="currentColor" fillRule="nonzero" d="M.5 6l6 5.5V.5z"></path>
    </svg>
  );
};

export {ArrowIconRight, ArrowIconLeft};