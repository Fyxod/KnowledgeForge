import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Upload, Send, FileText, Brain, Globe, Loader2 } from 'lucide-react';
import { api, Chat } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { ChatMessage } from '@/components/ChatMessage';
import { SourcesDisplay } from '@/components/SourcesDisplay';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

const ThreadView = () => {
  const { threadId } = useParams();
  const { user } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [webEnhanced, setWebEnhanced] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);
  const [lastSources, setLastSources] = useState<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (threadId && user) {
      loadThread();
    }
  }, [threadId, user]);

  useEffect(() => {
    scrollToBottom();
  }, [chats]);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  const loadThread = async () => {
    if (!threadId) return;
    
    try {
      const thread = await api.getThread(threadId);
      setChats(thread.chats || []);
      setDocuments(thread.documents || []);
    } catch (error) {
      toast.error('Failed to load thread');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !threadId) return;

    const files = Array.from(e.target.files);
    setLoading(true);

    try {
      const response = await api.uploadFiles({
        thread_id: threadId,
        files,
      });
      setDocuments(prev => [...prev, ...response.documents]);
      toast.success('Files uploaded successfully!');
    } catch (error) {
      toast.error('Failed to upload files');
    } finally {
      setLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !threadId || loading) return;

    const userMessage: Chat = {
      type: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setChats(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    const agentMessage: Chat = {
      type: 'agent',
      content: '',
      timestamp: new Date().toISOString(),
    };
    setChats(prev => [...prev, agentMessage]);

    try {
      const response = await api.query(
        threadId,
        userMessage.content,
        webEnhanced ? 'External' : 'Internal'
      );

      setChats(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: response.answer,
        };
        return updated;
      });

      setLastSources({
        docsUsed: response.docs_used,
        webUsed: response.web_used,
      });
    } catch (error) {
      toast.error('Failed to get response');
      setChats(prev => prev.slice(0, -2));
      setInput(userMessage.content);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b p-4 flex items-center justify-between bg-background">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {webEnhanced ? (
              <Globe className="w-5 h-5 text-primary" />
            ) : (
              <Brain className="w-5 h-5 text-primary" />
            )}
            <div>
              <p className="font-medium">
                {webEnhanced ? 'Web Enhanced' : 'Internal Knowledge'}
              </p>
              <p className="text-xs text-muted-foreground">
                {webEnhanced ? 'Uses documents + web search' : 'Uses only uploaded documents'}
              </p>
            </div>
          </div>
          <Switch checked={webEnhanced} onCheckedChange={setWebEnhanced} />
        </div>

        <div className="flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <FileText className="w-4 h-4 mr-2" />
                Documents ({documents.length})
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Uploaded Documents</DialogTitle>
                <DialogDescription>
                  Documents in this thread
                </DialogDescription>
              </DialogHeader>
              <ScrollArea className="max-h-96">
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <div key={doc.docId} className="p-3 border rounded-lg">
                      <p className="font-medium">{doc.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {doc.type.toUpperCase()} • {new Date(doc.time_uploaded).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                  {documents.length === 0 && (
                    <p className="text-center text-muted-foreground py-4">No documents uploaded</p>
                  )}
                </div>
              </ScrollArea>
            </DialogContent>
          </Dialog>

          <Button variant="outline" size="sm" disabled>
            Mind Map
          </Button>
          <Button variant="outline" size="sm" disabled>
            Word Cloud
          </Button>
        </div>
      </div>

      {/* Chat Area */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {chats.map((chat, index) => (
            <div key={index}>
              <ChatMessage chat={chat} />
              {chat.type === 'agent' && index === chats.length - 1 && lastSources && (
                <div className="ml-11">
                  <SourcesDisplay 
                    docsUsed={lastSources.docsUsed} 
                    webUsed={lastSources.webUsed} 
                  />
                </div>
              )}
            </div>
          ))}
          {loading && chats[chats.length - 1]?.type === 'agent' && chats[chats.length - 1]?.content === '' && (
            <div className="flex gap-3 p-4">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Loader2 className="w-5 h-5 text-primary animate-spin" />
              </div>
              <div className="bg-muted rounded-2xl px-4 py-3">
                <p className="text-sm">Thinking...</p>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t p-4 bg-background">
        <div className="max-w-4xl mx-auto flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.docx,.rtf,.txt,.epub,.odt,.ppt,.pptx,.xls,.xlsx,.csv,.html,.xml,.md,.jpg,.jpeg,.png,.tiff,.bmp,.gif"
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            <Upload className="w-4 h-4" />
          </Button>
          <Input
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            className="flex-1"
          />
          <Button 
            onClick={handleSend} 
            disabled={loading || !input.trim()}
            className="bg-gradient-primary"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ThreadView;
