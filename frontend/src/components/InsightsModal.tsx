import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Loader2,
  Lightbulb,
  ListChecks,
  ArrowRight,
  Code2,
  Sparkles,
  ThumbsUp,
  AlertTriangle,
  Rocket,
} from 'lucide-react';
import { Document, InsightsLLMOutput, api } from '@/lib/api';
import { downloadInsightsPdf } from '@/lib/insights-pdf';
import { toast } from 'sonner';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const PillList: React.FC<{ items?: string[]; className?: string }> = ({ items = [], className }) => {
  if (!items || items.length === 0) return null;
  const baseClass = className
    ? `transition-colors ${className}`
    : 'transition-colors bg-muted/80 text-muted-foreground border border-muted/50 hover:bg-muted hover:border-primary/40 dark:bg-muted/30 dark:border-muted/40 dark:hover:bg-muted/40';
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it, idx) => (
        <Badge key={idx} variant="outline" className={baseClass}>{it}</Badge>
      ))}
    </div>
  );
};

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; tone?: 'emerald' | 'amber' | 'violet' | 'sky' | 'rose' | 'pink' }>
  = ({ icon, title, tone = 'violet' }) => (
  <div className="flex items-center gap-2 mb-2">
    <div className={
      `p-2 rounded-md bg-${tone}-100 text-${tone}-700 dark:bg-${tone}-900/40 dark:text-${tone}-300`
    }>
      {icon}
    </div>
    <h4 className="font-semibold">{title}</h4>
  </div>
);

const InsightsRenderer: React.FC<{ insights: InsightsLLMOutput }> = ({ insights }) => {
  const doc = insights.document_summary;
  return (
    <div className="space-y-6 animate-in fade-in-0 duration-300">
      {/* Header */}
      <div className="rounded-xl p-5 bg-gradient-to-r from-amber-500 via-orange-500 to-pink-500 text-white shadow-md">
        <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
          <Lightbulb className="w-5 h-5" /> Insights
        </h3>
        <p className="text-xs/relaxed opacity-90">Synthesis of discussion points, strengths, gaps, innovations, and next steps.</p>
      </div>

      {/* Document summary */}
      <Card className="p-4">
        <SectionHeader icon={<Lightbulb className="w-4 h-4" />} title="Document Summary" tone="amber" />
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <div className="text-sm text-muted-foreground">Purpose</div>
          <Badge variant="outline" className="truncate max-w-[60%]" title={doc.title}>{doc.title}</Badge>
        </div>
        <p className="text-sm whitespace-pre-wrap mb-3">{doc.purpose}</p>
        <div>
          <div className="text-xs font-medium mb-2 text-muted-foreground">Key Themes</div>
          <PillList
            items={doc.key_themes}
            className="bg-amber-100 text-amber-700 border border-amber-200 hover:bg-amber-200 hover:border-amber-300 dark:bg-amber-900/40 dark:border-amber-800/50 dark:hover:bg-amber-800 dark:hover:border-amber-700/60 dark:text-amber-300"
          />
        </div>
      </Card>

      {/* Key discussion points */}
      {insights.key_discussion_points && insights.key_discussion_points.length > 0 && (
        <Card className="p-4">
          <SectionHeader icon={<ListChecks className="w-4 h-4" />} title="Key Discussion Points" tone="violet" />
          <div className="space-y-2 text-sm">
            {insights.key_discussion_points.map((p, idx) => (
              <Card
                key={idx}
                className="group p-3 transition-colors border border-border hover:border-primary/40 hover:bg-primary/5 dark:hover:bg-primary/20"
              >
                <div className="font-medium group-hover:text-foreground">{p.topic}</div>
                <div className="text-muted-foreground whitespace-pre-wrap mt-1 group-hover:text-foreground/80">{p.details}</div>
              </Card>
            ))}
          </div>
        </Card>
      )}

      {/* Strengths and gaps */}
      <div className="grid md:grid-cols-2 gap-4">
        {insights.strengths && insights.strengths.length > 0 && (
          <Card className="p-4">
            <SectionHeader icon={<ThumbsUp className="w-4 h-4" />} title="Strengths" tone="emerald" />
            <div className="space-y-2 text-sm">
              {insights.strengths.map((s, idx) => (
                <Card key={idx} className="p-3 border-emerald-200 dark:border-emerald-900/40">
                  <div className="font-medium">{s.aspect}</div>
                  <div className="text-muted-foreground whitespace-pre-wrap mt-1">{s.evidence_or_example}</div>
                </Card>
              ))}
            </div>
          </Card>
        )}
        {insights.improvement_or_missing_areas && insights.improvement_or_missing_areas.length > 0 && (
          <Card className="p-4">
            <SectionHeader icon={<AlertTriangle className="w-4 h-4" />} title="Gaps & Improvements" tone="rose" />
            <div className="space-y-2 text-sm">
              {insights.improvement_or_missing_areas.map((g, idx) => (
                <Card key={idx} className="p-3 border-rose-200 dark:border-rose-900/40">
                  <div className="flex flex-col md:flex-row md:items-center md:gap-3">
                    <div className="flex-1"><span className="font-medium">Gap:</span> <span className="whitespace-pre-wrap">{g.gap}</span></div>
                    <ArrowRight className="hidden md:block w-4 h-4 text-muted-foreground" />
                    <div className="flex-1 md:text-right"><span className="font-medium">Improve:</span> <span className="whitespace-pre-wrap">{g.suggested_improvement}</span></div>
                  </div>
                </Card>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Innovation aspects */}
      {insights.innovation_aspects && insights.innovation_aspects.length > 0 && (
        <Card className="p-4">
          <SectionHeader icon={<Sparkles className="w-4 h-4" />} title="Innovation Aspects" tone="pink" />
          <div className="grid md:grid-cols-2 gap-3">
            {insights.innovation_aspects.map((i, idx) => (
              <Card key={idx} className="p-3 hover:shadow-sm transition-shadow">
                <div className="font-medium">{i.innovation_title}</div>
                <div className="text-sm whitespace-pre-wrap text-muted-foreground mt-1">{i.description}</div>
                <Separator className="my-2" />
                <div className="text-xs"><span className="font-medium">Potential Impact:</span> {i.potential_impact}</div>
              </Card>
            ))}
          </div>
        </Card>
      )}

      {/* Future considerations */}
      {insights.future_considerations && insights.future_considerations.length > 0 && (
        <Card className="p-4">
          <SectionHeader icon={<Rocket className="w-4 h-4" />} title="Future Considerations" tone="sky" />
          <div className="space-y-2 text-sm">
            {insights.future_considerations.map((f, idx) => (
              <Card key={idx} className="p-3 border-sky-200 dark:border-sky-900/40">
                <div className="font-medium">{f.focus_area}</div>
                <div className="text-muted-foreground whitespace-pre-wrap mt-1">{f.recommendation}</div>
              </Card>
            ))}
          </div>
        </Card>
      )}

      {/* Pseudocode / Technical Outline */}
      {insights.pseudocode_or_technical_outline && insights.pseudocode_or_technical_outline.length > 0 && (
        <Card className="p-4">
          <SectionHeader icon={<Code2 className="w-4 h-4" />} title="Pseudocode / Technical Outline" tone="violet" />
          <div className="space-y-3">
            {insights.pseudocode_or_technical_outline!.map((p, idx) => (
              <Card key={idx} className="p-3">
                {p.section && <div className="font-medium mb-1">{p.section}</div>}
                {p.pseudocode && (
                  <pre className="text-xs bg-muted rounded-md p-3 overflow-auto whitespace-pre-wrap">
                    <code>{p.pseudocode}</code>
                  </pre>
                )}
              </Card>
            ))}
          </div>
        </Card>
      )}

      {/* Additional insights */}
      {insights.llm_inferred_additions && insights.llm_inferred_additions.length > 0 && (
        <Card className="p-4">
          <h4 className="font-semibold mb-2">Additional Insights</h4>
          <div className="space-y-2 text-sm">
            {insights.llm_inferred_additions.map((ad, idx) => (
              <Card key={idx} className="p-3">
                <div className="font-medium">{ad.section_title}</div>
                <div className="whitespace-pre-wrap text-muted-foreground mt-1">{ad.content}</div>
              </Card>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

const ALL_DOCS_ID = '__ALL_DOCS__';

const InsightsModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [insights, setInsights] = useState<InsightsLLMOutput | null>(null);
  const [view, setView] = useState<'select' | 'progress' | 'display'>('select');
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const pollingActiveRef = useRef<boolean>(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPolledDocRef = useRef<string | null>(null);

  const handleToggle = (docId: string) => {
    setSelectedDoc(prev => (prev === docId ? null : docId));
  };

  const requestInsights = async () => {
    if (!selectedDoc) {
      toast.error('Please select a document');
      return;
    }
    setLoading(true);
    setMessage(null);
    setInsights(null);

    try {
      const isAll = selectedDoc === ALL_DOCS_ID;
      const res = isAll ? await api.insightsGlobal(threadId) : await api.insights(threadId, selectedDoc);
      if (res?.status && res.insights) {
        setInsights(res.insights);
        toast.success('Insights ready');
        pollingActiveRef.current = false;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setView('display');
      } else if (res?.status === false && res.message) {
        setMessage(res.message);
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === res.message ? msgs : [...msgs, res.message!]));
        toast.info(res.message);
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      } else if (res?.error) {
        toast.error(res.error);
      } else {
        setMessage('Generating insights...');
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === 'Generating insights...' ? msgs : [...msgs, 'Generating insights...']));
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting insights:', e);
      toast.error('Failed to request insights');
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
        const isAll = docId === ALL_DOCS_ID;
        const res = isAll ? await api.insightsGlobal(threadId) : await api.insights(threadId, docId);
        if (res?.status && res.insights) {
          setInsights(res.insights);
          setMessage(null);
          pollingActiveRef.current = false;
          setView('display');
          return;
        }
        if (res?.message) {
          setMessage(res.message);
          setProgressMessages((msgs) => (msgs[msgs.length - 1] === res.message ? msgs : [...msgs, res.message!]));
          setView('progress');
        }
      } catch (e) {
        // non-fatal; keep polling
      }
      if (pollingActiveRef.current) schedulePoll();
    }, 5000);
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setSelectedDoc(null);
      setInsights(null);
      setMessage(null);
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

  const selectedDocObj = selectedDoc && selectedDoc !== ALL_DOCS_ID ? documents.find(d => d.docId === selectedDoc) : null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Insights</DialogTitle>
          <DialogDescription>
            {view === 'select' && 'Select a document (or All Documents) to generate insights.'}
            {view === 'progress' && (
              <span>
                Generating for: <span className="font-medium">{selectedDoc === ALL_DOCS_ID ? 'All Documents in Thread' : (selectedDocObj?.title || 'Selected Document')}</span>
              </span>
            )}
            {view === 'display' && (
              <span>
                {selectedDoc === ALL_DOCS_ID ? (
                  <>Scope: <span className="font-medium">All Documents in Thread</span></>
                ) : selectedDocObj ? (
                  <>Document: <span className="font-medium">{selectedDocObj.title}</span></>
                ) : null}
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
                      className={`flex items-start space-x-3 p-3 rounded-lg group hover:bg-accent/30 cursor-pointer transition-colors ${selectedDoc === ALL_DOCS_ID ? 'bg-accent/40' : ''}`}
                      onClick={() => handleToggle(ALL_DOCS_ID)}
                    >
                      <Checkbox
                        checked={selectedDoc === ALL_DOCS_ID}
                        onCheckedChange={() => handleToggle(ALL_DOCS_ID)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate group-hover:text-primary-foreground">All Documents in Thread</p>
                        <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/90">Generate insights using all uploaded documents.</p>
                      </div>
                    </div>
                    {documents.map((doc) => (
                      <div
                        key={doc.docId}
                        className={`flex items-start space-x-3 p-3 rounded-lg group hover:bg-accent/30 cursor-pointer transition-colors ${selectedDoc === doc.docId ? 'bg-accent/40' : ''}`}
                        onClick={() => handleToggle(doc.docId)}
                      >
                        <Checkbox
                          checked={selectedDoc === doc.docId}
                          onCheckedChange={() => handleToggle(doc.docId)}
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
                {selectedDoc ? (selectedDoc === ALL_DOCS_ID ? 'All documents selected' : '1 document selected') : 'No document selected'}
              </p>
            </div>

            {/* Generate Button */}
            <div className="flex items-center gap-3">
              <Button
                onClick={requestInsights}
                disabled={loading || !selectedDoc}
                className="bg-gradient-primary"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Requesting...
                  </>
                ) : (
                  'Generate Insights'
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
              <h3 className="text-lg font-semibold mb-2">{selectedDoc === ALL_DOCS_ID ? 'All Documents in Thread' : (selectedDocObj?.title || 'Selected Document')}</h3>
              <div className="space-y-2">
                {progressMessages.length > 0 ? (
                  progressMessages.map((m, idx) => (
                    <p key={idx} className="text-sm text-muted-foreground whitespace-pre-wrap">{m}</p>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Generating insights…</p>
                )}
              </div>
            </div>
            <div className="mt-4">
              <Button
                variant="outline"
                onClick={() => {
                  pollingActiveRef.current = false;
                  if (timeoutRef.current) {
                    clearTimeout(timeoutRef.current);
                    timeoutRef.current = null;
                  }
                  setView('select');
                  setProgressMessages([]);
                  setMessage(null);
                  setSelectedDoc(null);
                }}
              >
                Back to documents
              </Button>
            </div>
          </div>
        )}

        {view === 'display' && insights && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <InsightsRenderer insights={insights} />
            </ScrollArea>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                className="ml-auto"
                onClick={() => {
                  const title = insights?.document_summary?.title || 'Insights';
                  downloadInsightsPdf(insights, `${title}.pdf`);
                }}
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

export default InsightsModal;
