import PlayoffYearPicker from "@/components/PlayoffYearPicker";

function DesignSeasonPicker() {
  return (
    <div className="concept-season-picker">
      <span className="concept-control-index" aria-hidden="true">SEASON</span>
      <PlayoffYearPicker />
    </div>
  );
}

export default DesignSeasonPicker;
