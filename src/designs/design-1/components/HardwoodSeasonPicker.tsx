import PlayoffYearPicker from "@/components/PlayoffYearPicker";

function HardwoodSeasonPicker() {
  return (
    <div
      className="relative min-w-[218px] rounded-hw border border-hw-line bg-hw-surface px-3.5 pt-3 pb-2 shadow-hw-small max-[700px]:min-w-0 [&_label]:text-[11px]! [&_label]:font-extrabold! [&_label]:tracking-[.1em]! [&_label]:text-hw-ink! [&_label]:uppercase! [&>div]:m-0! [&_[class*=bg-white]]:rounded-hw! [&_[class*=bg-white]]:shadow-none!"
    >
      {/* PlayoffYearPicker is shared with the real app; keep its surface override local to this preview. */}
      <PlayoffYearPicker />
    </div>
  );
}

export default HardwoodSeasonPicker;
