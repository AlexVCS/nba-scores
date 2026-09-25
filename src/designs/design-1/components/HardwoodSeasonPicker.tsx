import PlayoffYearPicker from "@/components/PlayoffYearPicker";

function HardwoodSeasonPicker() {
  return (
    <div
      className="relative w-[240px] max-w-full rounded-hw border border-hw-line bg-hw-surface px-3.5 py-3 shadow-hw-small max-[700px]:w-[218px]"
    >
      <PlayoffYearPicker align="center" variant="hardwood" />
    </div>
  );
}

export default HardwoodSeasonPicker;
