// Simple, safe markdown formatter
// Handles basic formatting without external dependencies

export function formatMarkdown(text) {
  if (!text || typeof text !== 'string') return text;
  
  // Split into lines for processing
  let lines = text.split('\n');
  let result = [];
  let inCodeBlock = false;
  let codeBlockContent = [];
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];
    
    // Handle code blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        // End of code block
        result.push({
          type: 'code-block',
          content: codeBlockContent.join('\n'),
          language: ''
        });
        codeBlockContent = [];
        inCodeBlock = false;
      } else {
        // Start of code block
        inCodeBlock = true;
        const language = line.trim().substring(3).trim();
      }
      continue;
    }
    
    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }
    
    // Process regular lines
    const processed = processLine(line);
    if (processed) {
      result.push(processed);
    }
  }
  
  // Handle unclosed code block
  if (inCodeBlock && codeBlockContent.length > 0) {
    result.push({
      type: 'code-block',
      content: codeBlockContent.join('\n'),
      language: ''
    });
  }
  
  return result;
}

function processLine(line) {
  const trimmed = line.trim();
  
  // Empty line
  if (!trimmed) {
    return { type: 'break' };
  }
  
  // Headers
  if (trimmed.startsWith('#')) {
    const match = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (match) {
      return {
        type: 'header',
        level: match[1].length,
        content: processInlineFormatting(match[2])
      };
    }
  }
  
  // Lists
  if (trimmed.match(/^[-*+]\s+/)) {
    return {
      type: 'list-item',
      content: processInlineFormatting(trimmed.substring(2))
    };
  }
  
  if (trimmed.match(/^\d+\.\s+/)) {
    return {
      type: 'ordered-list-item',
      content: processInlineFormatting(trimmed.replace(/^\d+\.\s+/, ''))
    };
  }
  
  // Blockquotes
  if (trimmed.startsWith('>')) {
    return {
      type: 'blockquote',
      content: processInlineFormatting(trimmed.substring(1).trim())
    };
  }
  
  // Regular paragraph
  return {
    type: 'paragraph',
    content: processInlineFormatting(line)
  };
}

function processInlineFormatting(text) {
  if (!text) return [];
  
  const parts = [];
  let current = '';
  let i = 0;
  
  while (i < text.length) {
    // Bold (**text**)
    if (text.substring(i, i + 2) === '**') {
      if (current) {
        parts.push({ type: 'text', content: current });
        current = '';
      }
      
      const endIndex = text.indexOf('**', i + 2);
      if (endIndex !== -1) {
        parts.push({
          type: 'bold',
          content: text.substring(i + 2, endIndex)
        });
        i = endIndex + 2;
        continue;
      }
    }
    
    // Italic (*text*)
    if (text[i] === '*' && text.substring(i, i + 2) !== '**') {
      if (current) {
        parts.push({ type: 'text', content: current });
        current = '';
      }
      
      const endIndex = text.indexOf('*', i + 1);
      if (endIndex !== -1) {
        parts.push({
          type: 'italic',
          content: text.substring(i + 1, endIndex)
        });
        i = endIndex + 1;
        continue;
      }
    }
    
    // Inline code (`code`)
    if (text[i] === '`') {
      if (current) {
        parts.push({ type: 'text', content: current });
        current = '';
      }
      
      const endIndex = text.indexOf('`', i + 1);
      if (endIndex !== -1) {
        parts.push({
          type: 'inline-code',
          content: text.substring(i + 1, endIndex)
        });
        i = endIndex + 1;
        continue;
      }
    }
    
    current += text[i];
    i++;
  }
  
  if (current) {
    parts.push({ type: 'text', content: current });
  }
  
  return parts;
}
