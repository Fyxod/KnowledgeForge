import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Loader2, Clipboard, ThumbsUp, ThumbsDown, Scale } from 'lucide-react';
import { Document, ProsConsOutput, ProsConsResponse, api } from '@/lib/api';
import { toast } from 'sonner';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const ListBadges: React.FC<{ items: string[]; variant?: 'pro' | 'con' }> = ({ items, variant = 'pro' }) => {
  if (!items || items.length === 0) return null;
  const base = variant === 'pro'
    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
    : 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300';
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it, idx) => (
        <Badge key={idx} variant="secondary" className={base}>{it}</Badge>
      ))}
    </div>
  );
};

const ProsConsView: React.FC<{ data: ProsConsOutput }> = ({ data }) => {
  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
            <ThumbsUp className="w-4 h-4" />
          </div>
          <h4 className="font-semibold">Pros</h4>
        </div>
        <ListBadges items={data.pros} variant="pro" />
      </Card>

      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 rounded-md bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300">
            <ThumbsDown className="w-4 h-4" />
          </div>
          <h4 className="font-semibold">Cons</h4>
        </div>
        <ListBadges items={data.cons} variant="con" />
      </Card>
    </div>
  );
};

const ProsConsModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [prosCons, setProsCons] = useState<ProsConsOutput | null>(null);
  const [view, setView] = useState<'select' | 'progress' | 'display'>('select');
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const pollingActiveRef = useRef<boolean>(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPolledDocRef = useRef<string | null>(null);

  const handleToggle = (docId: string) => {
    setSelectedDoc(prev => (prev === docId ? null : docId));
  };

  const requestProsCons = async () => {
    if (!selectedDoc) {
      toast.error('Please select a document');
      return;
    }

    setLoading(true);
    setProsCons(null);
    try {
      const res: ProsConsResponse = await api.prosCons(threadId, selectedDoc);
      if (res?.status && res.pros_cons) {
        setProsCons(res.pros_cons);
        toast.success('Pros & Cons ready');
        // stop polling if was active
        pollingActiveRef.current = false;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setView('display');
      } else if (res?.status === false && res.message) {
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === res.message ? msgs : [...msgs, res.message!]));
        setView('progress');
        toast.info(res.message);
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      } else if (res?.error) {
        toast.error(res.error);
      } else {
        const fallback = 'Generating pros & cons...';
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === fallback ? msgs : [...msgs, fallback]));
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting pros/cons:', e);
      toast.error('Failed to request pros/cons');
    } finally {
      setLoading(false);
    }
  };

  const schedulePoll = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    timeoutRef.current = setTimeout(async () => {
      if (!pollingActiveRef.current) return;
      const docId = lastPolledDocRef.current;
      if (!docId) return;
      try {
        const res = await api.prosCons(threadId, docId);
        if (res?.status && res.pros_cons) {
          setProsCons(res.pros_cons);
          pollingActiveRef.current = false;
          setView('display');
          return;
        }
        if (res?.message) {
          setProgressMessages((msgs) => (msgs[msgs.length - 1] === res.message ? msgs : [...msgs, res.message!]));
          setView('progress');
        }
      } catch (e) {
        // ignore and keep polling a bit more
      }
      if (pollingActiveRef.current) schedulePoll();
    }, 5000);
  };

  const handleCopy = async () => {
    if (!prosCons) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(prosCons, null, 2));
      toast.success('Pros & Cons JSON copied');
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setSelectedDoc(null);
      setProsCons(null);
      setProgressMessages([]);
      setView('select');
      setLoading(false);
      pollingActiveRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      lastPolledDocRef.current = null;
    }
    onOpenChange(open);
  };

  useEffect(() => {
    if (!open) {
      pollingActiveRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    }
  }, [open]);

  const selectedDocObj = selectedDoc ? documents.find(d => d.docId === selectedDoc) : null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Scale className="w-4 h-4" /> Pros & Cons</DialogTitle>
          <DialogDescription>
            {view === 'select' && 'Select a document to extract pros and cons.'}
            {view === 'progress' && (
              <span>
                Generating for: <span className="font-medium">{selectedDocObj?.title || 'Selected Document'}</span>
              </span>
            )}
            {view === 'display' && selectedDocObj && (
              <span>
                Document: <span className="font-medium">{selectedDocObj.title}</span>
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        {view === 'select' && (
          <div className="flex-1 overflow-hidden flex flex-col gap-6">
            {/* Document Selection */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Select Document</Label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedDoc(null)}
                  disabled={!selectedDoc}
                >
                  Clear Selection
                </Button>
              </div>

              <ScrollArea className="h-48 border rounded-lg p-3">
                {documents.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No documents available in this thread
                  </p>
                ) : (
                  <div className="space-y-3">
                    {documents.map((doc) => (
                      <div
                        key={doc.docId}
                        className={`flex items-start space-x-3 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors ${selectedDoc === doc.docId ? 'bg-accent' : ''}`}
                        onClick={() => handleToggle(doc.docId)}
                      >
                        <Checkbox
                          checked={selectedDoc === doc.docId}
                          onCheckedChange={() => handleToggle(doc.docId)}
                          className="mt-1"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{doc.title}</p>
                          <p className="text-sm text-muted-foreground">
                            {doc.type.toUpperCase()} • {new Date(doc.time_uploaded).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>

              <p className="text-sm text-muted-foreground">
                {selectedDoc ? '1 document selected' : 'No document selected'}
              </p>
            </div>

            {/* Generate Button */}
            <div className="flex items-center gap-3">
              <Button
                onClick={requestProsCons}
                disabled={loading || !selectedDoc}
                className="bg-gradient-primary"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Requesting...
                  </>
                ) : (
                  'Generate Pros & Cons'
                )}
              </Button>
            </div>
          </div>
        )}

        {view === 'progress' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">{selectedDocObj?.title || 'Selected Document'}</h3>
              <div className="space-y-2">
                {progressMessages.length > 0 ? (
                  progressMessages.map((m, idx) => (
                    <p key={idx} className="text-sm text-muted-foreground whitespace-pre-wrap">{m}</p>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Generating pros & cons…</p>
                )}
              </div>
            </div>
            <div className="mt-4">
              <Button
                variant="outline"
                onClick={() => {
                  // Go back to selection
                  pollingActiveRef.current = false;
                  if (timeoutRef.current) {
                    clearTimeout(timeoutRef.current);
                    timeoutRef.current = null;
                  }
                  setView('select');
                  setProgressMessages([]);
                  setSelectedDoc(null);
                }}
              >
                Back to documents
              </Button>
            </div>
          </div>
        )}

        {view === 'display' && prosCons && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <div className="grid md:grid-cols-2 gap-4">
                <Card className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <ThumbsUp className="w-4 h-4 text-emerald-600" />
                    <h4 className="font-semibold">Pros</h4>
                  </div>
                  <Separator className="my-2" />
                  <ListBadges items={prosCons.pros} variant="pro" />
                </Card>
                <Card className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <ThumbsDown className="w-4 h-4 text-rose-600" />
                    <h4 className="font-semibold">Cons</h4>
                  </div>
                  <Separator className="my-2" />
                  <ListBadges items={prosCons.cons} variant="con" />
                </Card>
              </div>
            </ScrollArea>

            <div className="flex gap-3">
              <Button onClick={handleCopy} className="ml-auto" variant="default">
                <Clipboard className="w-4 h-4 mr-2" />
                Copy JSON
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ProsConsModal;
