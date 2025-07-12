// components/Sidebar.js
export default function Sidebar({ threads, selectedId, onSelect }) {
  return (
    <div className="w-1/4 bg-gray-900 text-white p-4 overflow-y-auto">
      <h2 className="text-xl font-bold mb-4">Your Threads</h2>
      {threads.map(({ id, thread_name, updatedAt }) => (
        <div
          key={id}
          onClick={() => onSelect(id)}
          className={`p-3 mb-2 rounded cursor-pointer ${
            id === selectedId ? 'bg-blue-700' : 'hover:bg-gray-700'
          }`}
        >
          <div className="font-medium">{thread_name}</div>
          <div className="text-sm text-gray-400">
            {new Date(updatedAt.$date).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
