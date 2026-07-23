import GameDatePicker from "@/components/GameDatePicker";

function DesignDatePicker() {
  return (
    <div className="concept-date-picker">
      <span className="concept-control-index" aria-hidden="true">01</span>
      <GameDatePicker />
    </div>
  );
}

export default DesignDatePicker;
