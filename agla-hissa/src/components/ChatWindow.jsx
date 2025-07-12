// components/ChatWindow.js
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';

export default function ChatWindow({ thread, onSend }) {
  if (!thread) return <div className="w-3/4 flex items-center justify-center text-gray-500">Select a thread</div>;

  return (
    <div className="w-3/4 flex flex-col h-full bg-white">
      <div className="p-4 border-b font-semibold text-lg">{thread.thread_name}</div>
      <div className="flex-1 overflow-y-auto p-4">
        {thread.chats.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
      </div>
      <ChatInput onSend={onSend} />
    </div>
  );
}
