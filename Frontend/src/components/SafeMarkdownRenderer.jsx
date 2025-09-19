import { formatMarkdown } from '../utils/markdownFormatter';

export default function SafeMarkdownRenderer({ content, enableMarkdown = true }) {
  // If markdown is disabled, return plain text
  if (!enableMarkdown || !content) {
    return <div className="whitespace-pre-wrap leading-relaxed">{content}</div>;
  }

  // Format the markdown safely
  let formattedContent;
  try {
    formattedContent = formatMarkdown(content);
  } catch (error) {
    console.warn('Markdown formatting failed, falling back to plain text:', error);
    return <div className="whitespace-pre-wrap leading-relaxed">{content}</div>;
  }

  const renderElement = (element, index) => {
    switch (element.type) {
      case 'header':
        const HeaderTag = `h${Math.min(element.level, 6)}`;
        const headerClasses = {
          1: 'text-xl font-bold mb-2',
          2: 'text-lg font-bold mb-2',
          3: 'text-base font-bold mb-1',
          4: 'text-sm font-bold mb-1',
          5: 'text-sm font-semibold mb-1',
          6: 'text-xs font-semibold mb-1'
        };
        return (
          <HeaderTag key={index} className={headerClasses[element.level] || headerClasses[6]}>
            {renderInlineContent(element.content)}
          </HeaderTag>
        );

      case 'paragraph':
        return (
          <p key={index} className="mb-2">
            {renderInlineContent(element.content)}
          </p>
        );

      case 'list-item':
        return (
          <div key={index} className="flex items-start mb-1">
            <span className="w-2 h-2 bg-gray-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
            <span>{renderInlineContent(element.content)}</span>
          </div>
        );

      case 'ordered-list-item':
        return (
          <div key={index} className="flex items-start mb-1">
            <span className="text-gray-600 mr-2 font-mono text-sm">{index + 1}.</span>
            <span>{renderInlineContent(element.content)}</span>
          </div>
        );

      case 'blockquote':
        return (
          <div key={index} className="border-l-4 border-gray-300 pl-4 italic text-gray-600 my-2">
            {renderInlineContent(element.content)}
          </div>
        );

      case 'code-block':
        return (
          <pre key={index} className="bg-gray-800 text-white p-3 rounded-lg overflow-x-auto my-2 text-sm">
            <code>{element.content}</code>
          </pre>
        );

      case 'break':
        return <br key={index} />;

      default:
        return (
          <div key={index} className="whitespace-pre-wrap">
            {element.content || ''}
          </div>
        );
    }
  };

  const renderInlineContent = (parts) => {
    if (!Array.isArray(parts)) {
      return parts;
    }

    return parts.map((part, index) => {
      switch (part.type) {
        case 'bold':
          return <strong key={index} className="font-semibold">{part.content}</strong>;
        
        case 'italic':
          return <em key={index} className="italic">{part.content}</em>;
        
        case 'inline-code':
          return (
            <code key={index} className="bg-gray-200 text-gray-800 px-1 py-0.5 rounded text-sm font-mono">
              {part.content}
            </code>
          );
        
        case 'text':
        default:
          return <span key={index}>{part.content}</span>;
      }
    });
  };

  return (
    <div className="leading-relaxed">
      {Array.isArray(formattedContent) ? 
        formattedContent.map(renderElement) : 
        <div className="whitespace-pre-wrap">{content}</div>
      }
    </div>
  );
}
