function DatePicker({ value, onChange }) {
 return (
    <input
      type="date"
      value={value}
      onChange={onChange}
    />
 );
}

export default DatePicker;
