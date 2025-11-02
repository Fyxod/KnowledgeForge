import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';
import { Document, api } from '@/lib/api';
import { toast } from 'sonner';
import SafeMarkdownRenderer from './SafeMarkdownRenderer';
import { downloadSummaryPdf } from '@/lib/summary-pdf';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const ALL_DOCS_ID = '__ALL_DOCS__';

const SummaryModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);

  const handleToggle = (docId: string) => {
    setSelectedDoc(prev => (prev === docId ? null : docId));
  };

  const generateSummary = async () => {
    if (!selectedDoc) {
      toast.error('Please select a document');
      return;
    }

    setLoading(true);
    setSummary(null);

    try {
      const isAll = selectedDoc === ALL_DOCS_ID;
      const res = isAll ? await api.summaryGlobal(threadId) : await api.summary(threadId, selectedDoc);
      if (res?.status && res.summary) {
        setSummary(res.summary);
        toast.success('Summary generated');
      } else if (typeof res?.error === 'string' && res.error) {
        toast.error(res.error);
      } else if (typeof res?.message === 'string' && res.message) {
        // Treat informational messages from backend (e.g., disabled or generating) as info
        const msg = res.message;
        if (/disable|not enabled|generating/i.test(msg)) {
          toast.info(msg);
        } else {
          toast.error(msg);
        }
      } else {
        toast.error('Summary not yet generated. Generating...');
      }
    } catch (e) {
      console.error('Error generating summary:', e);
      toast.error('Failed to generate summary');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setSelectedDoc(null);
      setSummary(null);
      setLoading(false);
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Generate Summary</DialogTitle>
          <DialogDescription>
            Select a document (or All Documents) and generate its summary
          </DialogDescription>
        </DialogHeader>

        {!summary ? (
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

              <ScrollArea className="h-64 border rounded-lg p-3">
                {documents.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No documents available in this thread
                  </p>
                ) : (
                  <div className="space-y-3">
                    {/* All Documents option */}
                    <div
                      key={ALL_DOCS_ID}
                      className={`flex items-start space-x-3 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors ${selectedDoc === ALL_DOCS_ID ? 'bg-accent' : ''}`}
                      onClick={() => handleToggle(ALL_DOCS_ID)}
                    >
                      <Checkbox
                        checked={selectedDoc === ALL_DOCS_ID}
                        onCheckedChange={() => handleToggle(ALL_DOCS_ID)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">All Documents in Thread</p>
                        <p className="text-sm text-muted-foreground">Generate a summary using all uploaded documents.</p>
                      </div>
                    </div>
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
                {selectedDoc ? (selectedDoc === ALL_DOCS_ID ? 'All documents selected' : '1 document selected') : 'No document selected'}
              </p>
            </div>

            {/* Generate Button */}
            <Button
              onClick={generateSummary}
              disabled={loading || !selectedDoc}
              className="w-full bg-gradient-primary"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Summary'
              )}
            </Button>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            {/* Summary Display */}
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[50vh] md:h-[60vh] overflow-auto">
              <SafeMarkdownRenderer content={summary} enableMarkdown />
            </ScrollArea>

            {/* Action Button */}
            <div className="flex">
              <Button
                onClick={() => {
                  const title = documents.find((d) => d.docId === selectedDoc)?.title || 'Summary';
                  downloadSummaryPdf(summary, `${title}.pdf`, { title });
                }}
                className="ml-auto"
              >
                Export as PDF
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default SummaryModal;
