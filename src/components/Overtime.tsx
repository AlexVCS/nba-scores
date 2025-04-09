export interface OvertimeHeadProps {
  period: number
}

const OvertimeHead = ({period}: OvertimeHeadProps) => {
  return period > 4 ? (
    <>
      {Array(period - 4)
        .fill(null)
        .map((_, i) => (
          <th className="px-2" key={i}>{i === 0 ? "OT" : `OT${i + 1}`}</th>
        ))}
    </>
  ) : null;
}

export default OvertimeHead