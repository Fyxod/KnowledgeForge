import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Download, FileSpreadsheet, Loader2 } from 'lucide-react';
import { api, Document } from '@/lib/api';
import { toast } from 'sonner';
import { API_URL } from '../../config';
import { getAuthToken } from '@/lib/api';

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
}

const QUICK_ACTIONS = [
  { label: 'Export all data', prompt: 'Export all spreadsheet data to Excel with proper formatting' },
  { label: 'Pivot table', prompt: 'Create a pivot table summarizing the data with key aggregations' },
  { label: 'Summary report', prompt: 'Create a summary report with key metrics and a chart' },
  { label: 'Filtered view', prompt: 'Create a filtered and sorted view of the most important data' },
];

const ExcelSkillModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [requestText, setRequestText] = React.useState('');
  const [selectedDocIds, setSelectedDocIds] = React.useState<string[]>([]);
  const [generating, setGenerating] = React.useState(false);
  const [trackingId, setTrackingId] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<{
    file_name: string;
    download_url: string;
    description: string;
    sheet_count: number;
    total_rows: number;
  } | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const pollRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  React.useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const toggleDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleGenerate = async () => {
    if (!requestText.trim()) {
      toast.error('Please describe what Excel file you want to create');
      return;
    }

    setGenerating(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.excelSkillGenerate(
        threadId,
        requestText.trim(),
        selectedDocIds.length > 0 ? selectedDocIds : undefined
      );

      if (response.tracking_id) {
        setTrackingId(response.tracking_id);
        // Start polling
        pollRef.current = setInterval(async () => {
          try {
            const status = await api.excelSkillStatus(response.tracking_id!);
            if (status.status && status.result) {
              // Done
              setResult(status.result);
              setGenerating(false);
              if (pollRef.current) clearInterval(pollRef.current);
            } else if (status.failed) {
              setError(status.error || 'Generation failed');
              setGenerating(false);
              if (pollRef.current) clearInterval(pollRef.current);
            }
          } catch (e) {
            console.error('Polling error:', e);
          }
        }, 2000);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start generation');
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    const token = getAuthToken();
    const url = `${API_URL}${result.download_url}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    window.open(url, '_blank');
  };

  const handleReset = () => {
    setRequestText('');
    setResult(null);
    setError(null);
    setTrackingId(null);
    setGenerating(false);
    if (pollRef.current) clearInterval(pollRef.current);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleReset(); onOpenChange(v); }}>
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-green-600" />
            Excel Builder
          </DialogTitle>
          <DialogDescription>
            Describe the Excel file you want to create from your documents.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 pr-2">
          <div className="space-y-4 py-2">
            {/* Quick action chips */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">Quick Actions</label>
              <div className="flex flex-wrap gap-2">
                {QUICK_ACTIONS.map((action) => (
                  <Button
                    key={action.label}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => setRequestText(action.prompt)}
                    disabled={generating}
                  >
                    {action.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Request text */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">What do you want to create?</label>
              <Textarea
                placeholder="e.g., Create a pivot table of sales by region with a bar chart and totals row..."
                value={requestText}
                onChange={(e) => setRequestText(e.target.value)}
                rows={4}
                disabled={generating}
                className="resize-none"
              />
            </div>

            {/* Document selection */}
            {documents.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-1.5 block">
                  Source Documents <span className="text-muted-foreground font-normal">(optional — all docs used if none selected)</span>
                </label>
                <div className="border rounded-md p-2 space-y-1.5 max-h-32 overflow-y-auto">
                  {documents.map((doc) => (
                    <label
                      key={doc.docId}
                      className="flex items-center gap-2 text-sm cursor-pointer hover:bg-accent/40 rounded px-1 py-0.5"
                    >
                      <Checkbox
                        checked={selectedDocIds.includes(doc.docId)}
                        onCheckedChange={() => toggleDoc(doc.docId)}
                        disabled={generating}
                      />
                      <span className="truncate" title={doc.title}>{doc.title}</span>
                      <span className="text-xs text-muted-foreground ml-auto flex-none">{doc.type}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Generate button */}
            {!result && (
              <Button
                className="w-full"
                onClick={handleGenerate}
                disabled={generating || !requestText.trim()}
              >
                {generating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating Excel...
                  </>
                ) : (
                  <>
                    <FileSpreadsheet className="w-4 h-4 mr-2" />
                    Generate Excel
                  </>
                )}
              </Button>
            )}

            {/* Error */}
            {error && (
              <div className="bg-destructive/10 text-destructive text-sm rounded-md p-3">
                {error}
                <Button variant="ghost" size="sm" className="mt-2" onClick={handleReset}>
                  Try Again
                </Button>
              </div>
            )}

            {/* Result */}
            {result && (
              <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900 rounded-md p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-green-600" />
                  <span className="font-medium">{result.file_name}</span>
                </div>
                <p className="text-sm text-muted-foreground">{result.description}</p>
                <div className="flex gap-4 text-sm">
                  <span><strong>{result.sheet_count}</strong> sheet(s)</span>
                  <span><strong>{result.total_rows}</strong> rows</span>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleDownload} className="flex-1">
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                  <Button variant="outline" onClick={handleReset}>
                    Create Another
                  </Button>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};

export default ExcelSkillModal;
