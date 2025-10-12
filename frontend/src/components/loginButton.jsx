import '../App.css'

export default function LoginButton({ text, onClick }) {
  return (
    <button
      className="bg-slblue  text-white  py-3 px-10 rounded-xl"
      onClick={onClick}
    >
      {text}
    </button>
  )
}
