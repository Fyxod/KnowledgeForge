import '../App.css'
export default function InputBox({ text, value, onChange, type = "text" }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={text}
      className="border border-tblue text-tblue rounded-lg p-2"
      
    />
  )
}
