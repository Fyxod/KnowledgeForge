import { Chat } from '@/lib/api';
import { User, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import React from 'react';
import SafeMarkdownRenderer from './SafeMarkdownRenderer';
import { Button } from '@/components/ui/button';

interface ChatMessageProps {
  chat: Chat;
}

export const ChatMessage = ({ chat }: ChatMessageProps) => {
  const isUser = chat.type === 'user';
  const [mdEnabled, setMdEnabled] = React.useState(true);
  const displayTime = React.useMemo(() => {
    // User-requested simple logic:
    // 1) Try new Date(chat.timestamp + 'Z') and format to IST
    // 2) If that yields an invalid date, use current time
    try {
      const raw = chat.timestamp ?? '';
      const parsed = new Date(String(raw) + 'Z');
      if (isNaN(parsed.getTime())) {
        return new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true,
          timeZone: 'Asia/Kolkata'
        });
      }

      return parsed.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
        timeZone: 'Asia/Kolkata'
      });
    } catch (e) {
      return new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
        timeZone: 'Asia/Kolkata'
      });
    }
  }, [chat.timestamp]);

  return (
    <div className={cn('flex gap-3 p-4', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <Bot className="w-5 h-5 text-primary" />
        </div>
      )}

      {!isUser && (
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'h-6 px-2 text-[10px] leading-none mt-1 border border-transparent',
            mdEnabled ? 'text-primary' : 'text-muted-foreground'
          )}
          title={mdEnabled ? 'Markdown: ON' : 'Markdown: OFF'}
          onClick={() => setMdEnabled((v) => !v)}
          aria-pressed={mdEnabled}
        >
          {mdEnabled ? 'MD' : 'TXT'}
        </Button>
      )}

      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">{chat.content}</p>
        ) : (
          <div className="text-sm">
            <SafeMarkdownRenderer content={chat.content} enableMarkdown={mdEnabled} />
          </div>
        )}
        <p className="text-xs opacity-70 mt-2">{displayTime}</p>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <User className="w-5 h-5 text-primary" />
        </div>
      )}
    </div>
  );
};
