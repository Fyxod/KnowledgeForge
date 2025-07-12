// components/MessageBubble.js
export default function MessageBubble({ message }) {
  const isUser = message.type === 'user';
  return (
    <div className={`mb-4 ${isUser ? 'text-right' : 'text-left'}`}>
      <div
        className={`inline-block px-4 py-2 rounded-xl max-w-xl ${
          isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-black'
        }`}
      >
        {message.content}
      </div>
      <div className="text-xs text-gray-400 mt-1">
        {new Date(message.timestamp.$date).toLocaleTimeString()}
      </div>
    </div>
  );
}
