// components/ChatInput.js
import { useState } from 'react';

export default function ChatInput({ onSend }) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput('');
  };

  return (
    <div className="p-4 border-t flex">
      <input
        className="flex-1 border rounded-l px-4 py-2"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Ask something..."
      />
      <button
        onClick={handleSend}
        className="bg-blue-600 text-white px-4 py-2 rounded-r"
      >
        Send
      </button>
    </div>
  );
}
