// interface DatePickerProps {
//   setSelectedDate: (date: Date) => void;
//   datePickerValue: string;
//   setDatePickerValue: (value: string) => void;
// }

// function DatePicker({ setSelectedDate, datePickerValue, setDatePickerValue }: DatePickerProps) {
//   const handleDateChange = (event: React.ChangeEvent<HTMLInputElement>) => {
//     const utcDate = new Date(event.target.value);
//     setSelectedDate(utcDate);
//     setDatePickerValue(event.target.value);
//   };

//   return (
//     <input type="date" value={datePickerValue} onChange={handleDateChange} />
//   );
// }
// export default DatePicker;
