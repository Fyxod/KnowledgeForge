import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Download } from 'lucide-react';
import { Document, getAuthToken } from '@/lib/api';
import { API_URL } from '../../config';
import { toast } from 'sonner';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const WordCloudModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [maxWords, setMaxWords] = useState<number>(1000);
  const [loading, setLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const handleDocToggle = (docId: string) => {
    setSelectedDocs(prev => 
      prev.includes(docId) 
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    if (selectedDocs.length === documents.length) {
      setSelectedDocs([]);
    } else {
      setSelectedDocs(documents.map(doc => doc.docId));
    }
  };

  const generateWordCloud = async () => {
    if (selectedDocs.length === 0) {
      toast.error('Please select at least one document');
      return;
    }

    setLoading(true);
    setImageUrl(null);

    try {
      const token = getAuthToken();
      const response = await fetch(`${API_URL}/wordcloud/${threadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          document_ids: selectedDocs,
          max_words: maxWords,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate word cloud');
      }

      // Get the image blob and create a URL for it
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setImageUrl(url);
      toast.success('Word cloud generated successfully!');
    } catch (error) {
      console.error('Error generating word cloud:', error);
      toast.error('Failed to generate word cloud');
    } finally {
      setLoading(false);
    }
  };

  const downloadWordCloud = () => {
    if (!imageUrl) return;

    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `wordcloud-${threadId}-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Word cloud downloaded!');
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      // Clean up the blob URL when closing
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
      setImageUrl(null);
      setSelectedDocs([]);
      setMaxWords(1000);
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Generate Word Cloud</DialogTitle>
          <DialogDescription>
            Select documents and configure word cloud settings
          </DialogDescription>
        </DialogHeader>

        {!imageUrl ? (
          <div className="flex-1 overflow-hidden flex flex-col gap-6">
            {/* Document Selection */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">Select Documents</Label>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSelectAll}
                  disabled={documents.length === 0}
                >
                  {selectedDocs.length === documents.length ? 'Deselect All' : 'Select All'}
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
                          className="flex items-start space-x-3 p-3 rounded-lg group hover:bg-accent/30 cursor-pointer transition-colors"
                          onClick={() => handleDocToggle(doc.docId)}
                        >
                        <Checkbox
                          checked={selectedDocs.includes(doc.docId)}
                          onCheckedChange={() => handleDocToggle(doc.docId)}
                          className="mt-1"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate group-hover:text-primary-foreground">{doc.title}</p>
                          <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/90">
                            {doc.type.toUpperCase()} • {new Date(doc.time_uploaded).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>

              <p className="text-sm text-muted-foreground">
                {selectedDocs.length} document{selectedDocs.length !== 1 ? 's' : ''} selected
              </p>
            </div>

            {/* Max Words Input */}
            <div className="space-y-2">
              <Label htmlFor="maxWords" className="text-base font-semibold">
                Maximum Words
              </Label>
              <Input
                id="maxWords"
                type="number"
                min={10}
                max={100000}
                value={maxWords}
                onChange={(e) => {
                  const value = parseInt(e.target.value) || 1000;
                  setMaxWords(Math.min(100000, Math.max(10, value)));
                }}
                className="w-full"
              />
              <p className="text-sm text-muted-foreground">
                Number of words to display in the word cloud (10-100000)
              </p>
            </div>

            {/* Generate Button */}
            <Button
              onClick={generateWordCloud}
              disabled={loading || selectedDocs.length === 0}
              className="w-full bg-gradient-primary"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Word Cloud'
              )}
            </Button>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            {/* Image Display */}
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30">
              <div className="flex items-center justify-center min-h-[400px]">
                <img
                  src={imageUrl}
                  alt="Word Cloud"
                  className="max-w-full h-auto rounded-lg shadow-lg"
                />
              </div>
            </ScrollArea>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                onClick={downloadWordCloud}
                className="flex-1"
                variant="default"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Image
              </Button>
              <Button
                onClick={() => {
                  if (imageUrl) {
                    URL.revokeObjectURL(imageUrl);
                  }
                  setImageUrl(null);
                }}
                className="flex-1"
                variant="outline"
              >
                Generate New
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default WordCloudModal;
