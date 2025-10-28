import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Upload, Send, FileText, Brain, Globe, Loader2, X, Edit2, Check } from 'lucide-react';
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
import MindMapModal from '@/components/MindMapModal';
import WordCloudModal from '@/components/WordCloudModal';

const ThreadView = () => {
  const { threadId } = useParams();
  const { user } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [webEnhanced, setWebEnhanced] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);
  const [lastSources, setLastSources] = useState<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [fileNames, setFileNames] = useState<Record<number, string>>({});
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [progressMap, setProgressMap] = useState<Record<number, number>>({});
  const [mindMapOpen, setMindMapOpen] = useState(false);
  const [wordCloudOpen, setWordCloudOpen] = useState(false);

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
      const rootEl = scrollRef.current as HTMLElement;
      const viewport = rootEl.querySelector('[data-radix-scroll-area-viewport]') as HTMLElement | null;
      if (viewport) {
        try {
          viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' });
        } catch {
          viewport.scrollTop = viewport.scrollHeight;
        }
      } else {
        try {
          rootEl.scrollTo({ top: rootEl.scrollHeight, behavior: 'smooth' });
        } catch {
          rootEl.scrollTop = rootEl.scrollHeight;
        }
      }
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    setPendingFiles(prev => [...prev, ...files]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removePendingFile = (index: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== index));
    setFileNames(prev => {
      const updated = { ...prev };
      delete updated[index];
      return updated;
    });
    setProgressMap(prev => {
      const updated = { ...prev };
      delete updated[index];
      return updated;
    });
    if (editingIndex === index) setEditingIndex(null);
  };

  const updateFileName = (index: number, newName: string) => {
    setFileNames(prev => ({ ...prev, [index]: newName }));
  };

  const uploadPendingFiles = async () => {
    if (!threadId || pendingFiles.length === 0) return;

    const processed = pendingFiles.map((file, idx) => {
      const name = fileNames[idx];
      return name ? new File([file], name, { type: file.type }) : file;
    });

    setUploading(true);
    setProgressMap({});

    try {
      const response = await api.uploadFilesWithProgress({
        thread_id: threadId,
        files: processed,
        onProgress: ({ fileIndex, percent }) => {
          setProgressMap(prev => ({ ...prev, [fileIndex]: percent }));
        },
      });
      setDocuments(prev => [...prev, ...response.documents]);
      toast.success('Files uploaded successfully!');
      
      setPendingFiles([]);
      setFileNames({});
      setProgressMap({});
      setEditingIndex(null);
    } catch (error) {
      toast.error('Failed to upload files');
    } finally {
      setUploading(false);
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

      // Support both legacy shape and new `sources` wrapper; default to empty arrays
      const docsUsed = response.sources?.documents_used ?? response.docs_used ?? [];
      const webUsed = response.sources?.web_used ?? response.web_used ?? [];
      
      setChats(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: response.answer,
          sources: {
            documents_used: docsUsed,
            web_used: webUsed,
          },
        };
        return updated;
      });

      setLastSources({
        docsUsed,
        webUsed,
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

        {/* <div className="flex items-center gap-2">
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
          <Button variant="outline" size="sm" onClick={() => setMindMapOpen(true)} disabled={!threadId}>
            Mind Map
          </Button>
          <Button variant="outline" size="sm" onClick={() => setWordCloudOpen(true)} disabled={!threadId}>
            Word Cloud
          </Button>
        </div> */}
      </div>

      {/* Chat Area */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {chats.map((chat, index) => {
            // Check if this agent message has sources and at least one source array is non-empty
            const shouldShowSources =
              chat.type === 'agent' &&
              chat.sources &&
              (chat.sources.documents_used.length > 0 || chat.sources.web_used.length > 0);

            return (
              <div key={index}>
                <ChatMessage chat={chat} />
                {shouldShowSources && (
                  <div className="ml-11">
                    <SourcesDisplay
                      docsUsed={chat.sources!.documents_used}
                      webUsed={chat.sources!.web_used}
                    />
                  </div>
                )}
              </div>
            );
          })}
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
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.doc,.docx,.rtf,.txt,.epub,.odt,.ppt,.pptx,.xls,.xlsx,.csv,.html,.xml,.md,.jpg,.jpeg,.png,.tiff,.bmp,.gif"
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            <Upload className="w-4 h-4" />
          </Button>
          {/* Pending attachments list with rename/remove and progress */}
          {pendingFiles.length > 0 && (
            <div className="flex-1 flex flex-col gap-2 max-h-40 overflow-y-auto p-2 border rounded-md">
              <p className="text-xs text-muted-foreground">Attachments ready to upload:</p>
              {pendingFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-2 bg-muted/50 p-2 rounded">
                  {editingIndex === index ? (
                    <Input
                      value={fileNames[index] || file.name}
                      onChange={(e) => updateFileName(index, e.target.value)}
                      className="flex-1 h-8"
                      autoFocus
                    />
                  ) : (
                    <span className="flex-1 text-sm truncate">{fileNames[index] || file.name}</span>
                  )}
                  {typeof progressMap[index] === 'number' && (
                    <span className="text-xs text-muted-foreground w-12 text-right">{progressMap[index]}%</span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setEditingIndex(editingIndex === index ? null : index)}
                    disabled={uploading}
                  >
                    {editingIndex === index ? <Check className="w-4 h-4" /> : <Edit2 className="w-4 h-4" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removePendingFile(index)}
                    disabled={uploading}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
          <Input
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            className="flex-1"
          />
          <div className="flex items-center gap-2">
            {pendingFiles.length > 0 && (
              <Button
                onClick={uploadPendingFiles}
                disabled={uploading}
                variant="secondary"
              >
                {uploading ? 'Uploading…' : 'Upload'}
              </Button>
            )}
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
      {/* Mind Map Modal */}
      {threadId && (
        <MindMapModal open={mindMapOpen} onOpenChange={setMindMapOpen} threadId={threadId} />
      )}
      {/* Word Cloud Modal */}
      {threadId && (
        <WordCloudModal 
          open={wordCloudOpen} 
          onOpenChange={setWordCloudOpen} 
          threadId={threadId}
          documents={documents}
        />
      )}
    </div>
  );
};

export default ThreadView;
