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
  ScanSearch,
  Cpu,
  Wrench,
  ShieldAlert,
  Layers,
  Rocket,
  TrendingUp,
  Eye,
  ArrowRight,
  RefreshCcw,
  CheckCircle2,
  Sparkles,
  Target,
} from 'lucide-react';
import { Document, TechnicalAnalysisLLMOutput, api } from '@/lib/api';
import { downloadTechnicalAnalysisPdf } from '@/lib/technical-analysis-pdf';
import { downloadTechnicalAnalysisPptx } from '@/lib/technical-analysis-pptx';
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

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; tone?: 'emerald' | 'amber' | 'violet' | 'sky' | 'rose' | 'indigo' | 'slate' }>
  = ({ icon, title, tone = 'indigo' }) => (
    <div className="flex items-center gap-2 mb-2">
      <div className={
        `p-2 rounded-md bg-${tone}-100 text-${tone}-700 dark:bg-${tone}-900/40 dark:text-${tone}-300`
      }>
        {icon}
      </div>
      <h4 className="font-semibold">{title}</h4>
    </div>
  );

const TechnicalAnalysisRenderer: React.FC<{ analysis: TechnicalAnalysisLLMOutput }> = ({ analysis }) => {
  return (
    <div className="space-y-6 animate-in fade-in-0 duration-300">
      {/* Header banner */}
      <div className="rounded-xl p-5 bg-gradient-to-r from-indigo-500 via-violet-500 to-purple-500 text-white shadow-md">
        <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
          <ScanSearch className="w-5 h-5" /> {analysis.analysis_title}
        </h3>
        <p className="text-xs/relaxed opacity-90">Technical content extraction and analytical assessment of the document.</p>
      </div>

      {/* Executive Overview */}
      <Card className="p-4">
        <SectionHeader icon={<Eye className="w-4 h-4" />} title="Executive Overview" tone="indigo" />
        <p className="text-sm whitespace-pre-wrap">{analysis.executive_overview}</p>
      </Card>

      {/* ─── PART 1: What's In The Document ─── */}
      <div className="rounded-lg border-2 border-indigo-200 dark:border-indigo-800/50 p-1">
        <div className="px-3 py-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-t-md">
          <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">Part 1 — Document Content Extraction</h3>
        </div>
        <div className="p-3 space-y-4">
          {/* Technical Scope */}
          <Card className="p-4">
            <SectionHeader icon={<Layers className="w-4 h-4" />} title="Technical Scope" tone="violet" />
            <div className="space-y-3 text-sm">
              <div>
                <div className="font-medium mb-2">Domains Covered</div>
                <PillList
                  items={analysis.technical_scope.domains_covered}
                  className="bg-violet-100 text-violet-700 border border-violet-200 hover:bg-violet-200 hover:border-violet-300 dark:bg-violet-900/40 dark:border-violet-800/50 dark:hover:bg-violet-800 dark:hover:border-violet-700/60 dark:text-violet-300"
                />
              </div>
              <div>
                <div className="font-medium mb-2">Technology Stack</div>
                <PillList
                  items={analysis.technical_scope.technology_stack}
                  className="bg-indigo-100 text-indigo-700 border border-indigo-200 hover:bg-indigo-200 hover:border-indigo-300 dark:bg-indigo-900/40 dark:border-indigo-800/50 dark:hover:bg-indigo-800 dark:hover:border-indigo-700/60 dark:text-indigo-300"
                />
              </div>
              <div>
                <div className="font-medium mb-1">Architecture Overview</div>
                <p className="text-muted-foreground whitespace-pre-wrap">{analysis.technical_scope.architecture_overview}</p>
              </div>
            </div>
          </Card>

          {/* Technical Decisions */}
          {analysis.technical_decisions && analysis.technical_decisions.length > 0 && (
            <Card className="p-4">
              <SectionHeader icon={<Wrench className="w-4 h-4" />} title="Technical Decisions" tone="amber" />
              <div className="space-y-2 text-sm">
                {analysis.technical_decisions.map((d, idx) => (
                  <Card key={idx} className="p-3 hover:shadow-sm transition-shadow">
                    <div className="font-medium">{d.decision}</div>
                    <div className="text-muted-foreground whitespace-pre-wrap mt-1">{d.rationale}</div>
                    <Separator className="my-2" />
                    <div className="text-xs"><span className="font-medium">Implications:</span> <span className="whitespace-pre-wrap">{d.implications}</span></div>
                  </Card>
                ))}
              </div>
            </Card>
          )}

          {/* Strengths & Concerns */}
          <div className="grid md:grid-cols-2 gap-4">
            {analysis.technical_strengths && analysis.technical_strengths.length > 0 && (
              <Card className="p-4">
                <SectionHeader icon={<CheckCircle2 className="w-4 h-4" />} title="Technical Strengths" tone="emerald" />
                <div className="space-y-2 text-sm">
                  {analysis.technical_strengths.map((s, idx) => (
                    <Card key={idx} className="p-3 border-emerald-200 dark:border-emerald-900/40">
                      <div className="font-medium">{s.aspect}</div>
                      <div className="text-muted-foreground whitespace-pre-wrap mt-1">{s.evidence}</div>
                    </Card>
                  ))}
                </div>
              </Card>
            )}
            {analysis.technical_concerns && analysis.technical_concerns.length > 0 && (
              <Card className="p-4">
                <SectionHeader icon={<ShieldAlert className="w-4 h-4" />} title="Technical Concerns" tone="rose" />
                <div className="space-y-2 text-sm">
                  {analysis.technical_concerns.map((c, idx) => (
                    <Card key={idx} className="p-3 border-rose-200 dark:border-rose-900/40">
                      <div className="font-medium">{c.concern}</div>
                      <div className="text-muted-foreground whitespace-pre-wrap mt-1">{c.evidence}</div>
                      <Separator className="my-2" />
                      <div className="text-xs"><span className="font-medium">Impact:</span> {c.impact}</div>
                    </Card>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Innovation Elements */}
          {analysis.innovation_elements && analysis.innovation_elements.length > 0 && (
            <Card className="p-4">
              <SectionHeader icon={<Sparkles className="w-4 h-4" />} title="Innovation Elements" tone="violet" />
              <div className="grid md:grid-cols-2 gap-3">
                {analysis.innovation_elements.map((i, idx) => (
                  <Card key={idx} className="p-3 hover:shadow-sm transition-shadow">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium">{i.element}</div>
                      <Badge variant="outline" className={
                        i.maturity?.toLowerCase() === 'production'
                          ? 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800/50'
                          : i.maturity?.toLowerCase() === 'prototype'
                            ? 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800/50'
                            : 'bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/40 dark:text-violet-300 dark:border-violet-800/50'
                      }>{i.maturity}</Badge>
                    </div>
                    <div className="text-sm whitespace-pre-wrap text-muted-foreground mt-1">{i.description}</div>
                  </Card>
                ))}
              </div>
            </Card>
          )}

          {/* Technical Aspirations */}
          <Card className="p-4">
            <SectionHeader icon={<Target className="w-4 h-4" />} title="Technical Aspirations" tone="sky" />
            <div className="space-y-3 text-sm">
              <div>
                <div className="font-medium mb-2">Stated Goals</div>
                <PillList
                  items={analysis.technical_aspirations.stated_goals}
                  className="bg-sky-100 text-sky-700 border border-sky-200 hover:bg-sky-200 hover:border-sky-300 dark:bg-sky-900/40 dark:border-sky-800/50 dark:hover:bg-sky-800 dark:hover:border-sky-700/60 dark:text-sky-300"
                />
              </div>
              <div>
                <div className="font-medium mb-1">Implied Direction</div>
                <p className="text-muted-foreground whitespace-pre-wrap">{analysis.technical_aspirations.implied_direction}</p>
              </div>
              <div>
                <div className="font-medium mb-1">Alignment Assessment</div>
                <p className="text-muted-foreground whitespace-pre-wrap">{analysis.technical_aspirations.alignment_assessment}</p>
              </div>
            </div>
          </Card>

          {/* Implementation Readiness */}
          <Card className="p-4">
            <SectionHeader icon={<Cpu className="w-4 h-4" />} title="Implementation Readiness" tone="indigo" />
            <div className="grid md:grid-cols-3 gap-3">
              <Card className="p-3 border-emerald-200 dark:border-emerald-900/40">
                <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><CheckCircle2 className="w-4 h-4" /> Ready Components</div>
                <PillList
                  items={analysis.implementation_readiness.ready_components}
                  className="bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 hover:border-emerald-300 dark:bg-emerald-900/40 dark:border-emerald-800/50 dark:hover:bg-emerald-800 dark:hover:border-emerald-700/60 dark:text-emerald-300"
                />
              </Card>
              <Card className="p-3 border-amber-200 dark:border-amber-900/40">
                <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><ArrowRight className="w-4 h-4" /> Gaps to Address</div>
                <PillList
                  items={analysis.implementation_readiness.gaps_to_address}
                  className="bg-amber-100 text-amber-700 border border-amber-200 hover:bg-amber-200 hover:border-amber-300 dark:bg-amber-900/40 dark:border-amber-800/50 dark:hover:bg-amber-800 dark:hover:border-amber-700/60 dark:text-amber-300"
                />
              </Card>
              <Card className="p-3 border-sky-200 dark:border-sky-900/40">
                <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><Layers className="w-4 h-4" /> Dependencies</div>
                <PillList
                  items={analysis.implementation_readiness.dependencies}
                  className="bg-sky-100 text-sky-700 border border-sky-200 hover:bg-sky-200 hover:border-sky-300 dark:bg-sky-900/40 dark:border-sky-800/50 dark:hover:bg-sky-800 dark:hover:border-sky-700/60 dark:text-sky-300"
                />
              </Card>
            </div>
          </Card>
        </div>
      </div>

      {/* ─── PART 2: Analytical Assessment ─── */}
      <div className="rounded-lg border-2 border-violet-200 dark:border-violet-800/50 p-1">
        <div className="px-3 py-2 bg-violet-50 dark:bg-violet-900/20 rounded-t-md">
          <h3 className="text-sm font-semibold text-violet-700 dark:text-violet-300">Part 2 — Analytical Assessment</h3>
        </div>
        <div className="p-3 space-y-4">
          <Card className="p-4">
            <SectionHeader icon={<Rocket className="w-4 h-4" />} title="Forward-Looking Assessment" tone="emerald" />
            <div className="space-y-4">
              <div className="grid md:grid-cols-2 gap-3">
                <Card className="p-3 border-sky-200 dark:border-sky-900/40">
                  <div className="font-medium text-sm mb-1">Scalability Outlook</div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{analysis.forward_looking_assessment.scalability_outlook}</p>
                </Card>
                <Card className="p-3 border-violet-200 dark:border-violet-900/40">
                  <div className="font-medium text-sm mb-1">Technology Evolution</div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{analysis.forward_looking_assessment.technology_evolution}</p>
                </Card>
              </div>
              <Card className="p-3 border-emerald-200 dark:border-emerald-900/40">
                <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><TrendingUp className="w-4 h-4" /> Recommended Focus Areas</div>
                <PillList
                  items={analysis.forward_looking_assessment.recommended_focus_areas}
                  className="bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 hover:border-emerald-300 dark:bg-emerald-900/40 dark:border-emerald-800/50 dark:hover:bg-emerald-800 dark:hover:border-emerald-700/60 dark:text-emerald-300"
                />
              </Card>
              <div>
                <div className="font-medium text-sm mb-1">Overall Assessment</div>
                <p className="text-sm whitespace-pre-wrap text-muted-foreground">{analysis.forward_looking_assessment.overall_assessment}</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Additional Insights */}
      {analysis.llm_inferred_additions && analysis.llm_inferred_additions.length > 0 && (
        <Card className="p-4">
          <h4 className="font-semibold mb-2">Additional Insights</h4>
          <div className="space-y-2 text-sm">
            {analysis.llm_inferred_additions.map((ad, idx) => (
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

const TechnicalAnalysisModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<TechnicalAnalysisLLMOutput | null>(null);
  const [view, setView] = useState<'select' | 'progress' | 'display' | 'error'>('select');
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const pollingActiveRef = useRef<boolean>(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPolledDocRef = useRef<string | null>(null);

  const handleToggle = (docId: string) => {
    setSelectedDoc(prev => (prev === docId ? null : docId));
  };

  const requestAnalysis = async (isRegenerate: boolean = false) => {
    if (loading) return;
    if (!selectedDoc) {
      toast.error('Please select a document');
      return;
    }
    setLoading(true);
    setMessage(null);
    setAnalysis(null);

    try {
      const isAll = selectedDoc === ALL_DOCS_ID;
      const res = isAll
        ? await api.technicalAnalysisGlobal(threadId, isRegenerate)
        : await api.technicalAnalysis(threadId, selectedDoc, isRegenerate);
      if (res?.status && res.technical_analysis) {
        setAnalysis(res.technical_analysis);
        toast.success('Technical analysis ready');
        pollingActiveRef.current = false;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setView('display');
      } else if (res?.error) {
        const err = typeof res.error === 'string' ? res.error : JSON.stringify(res.error);
        setMessage(err);
        setProgressMessages([]);
        toast.error(err);
        pollingActiveRef.current = false;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setView('error');
      } else if (res?.status === false && res.message) {
        setMessage(res.message);
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === res.message ? msgs : [...msgs, res.message!]));
        toast.info(res.message);
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      } else {
        setMessage('Generating technical analysis...');
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === 'Generating technical analysis...' ? msgs : [...msgs, 'Generating technical analysis...']));
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting technical analysis:', e);
      toast.error('Failed to request technical analysis');
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
        const res = isAll
          ? await api.technicalAnalysisGlobal(threadId)
          : await api.technicalAnalysis(threadId, docId);
        if (res?.status && res.technical_analysis) {
          setAnalysis(res.technical_analysis);
          setMessage(null);
          pollingActiveRef.current = false;
          setView('display');
          return;
        }
        if (res?.error) {
          const err = typeof res.error === 'string' ? res.error : JSON.stringify(res.error);
          setMessage(err);
          setProgressMessages([]);
          toast.error(err);
          pollingActiveRef.current = false;
          setView('error');
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
      setAnalysis(null);
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

  const selectedDocObj = selectedDoc ? documents.find(d => d.docId === selectedDoc) : null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Technical Analysis</DialogTitle>
          <DialogDescription>
            {view === 'select' && 'Select a document (or All Documents) to generate a technical analysis.'}
            {view === 'progress' && (
              <span>
                Generating for:{' '}
                <span className="font-medium">
                  {selectedDoc === ALL_DOCS_ID ? 'All Documents in Thread' : (selectedDocObj?.title || 'Selected Document')}
                </span>
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
                <div className="w-full overflow-hidden">
                  {documents.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">
                      No documents available in this thread
                    </p>
                  ) : (
                    <div className="space-y-3">
                      <div
                        key={ALL_DOCS_ID}
                        className={`flex items-start space-x-3 p-3 rounded-lg group hover:bg-accent/30 cursor-pointer transition-colors ${selectedDoc === ALL_DOCS_ID ? 'bg-accent/40' : ''}`}
                        onClick={() => handleToggle(ALL_DOCS_ID)}
                      >
                        <Checkbox
                          checked={selectedDoc === ALL_DOCS_ID}
                          onCheckedChange={() => handleToggle(ALL_DOCS_ID)}
                          className="mt-1 flex-shrink-0"
                        />
                        <div className="flex-1 min-w-0 overflow-hidden">
                          <p className="font-medium truncate block w-full group-hover:text-primary-foreground">All Documents in Thread</p>
                          <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/90">Generate a technical analysis using all uploaded documents.</p>
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
                            className="mt-1 flex-shrink-0"
                          />
                          <div className="flex-1 min-w-0 overflow-hidden">
                            <p className="font-medium truncate block w-full group-hover:text-primary-foreground" title={doc.title}>{doc.title}</p>
                            <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/90">
                              {doc.type.toUpperCase()} • {new Date(doc.time_uploaded).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </ScrollArea>

              <p className="text-sm text-muted-foreground">
                {selectedDoc ? (selectedDoc === ALL_DOCS_ID ? 'All documents selected' : '1 document selected') : 'No document selected'}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Button
                onClick={() => requestAnalysis(false)}
                disabled={loading || !selectedDoc}
                className="bg-gradient-primary"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Requesting...
                  </>
                ) : (
                  'Generate Technical Analysis'
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
                  <p className="text-sm text-muted-foreground">Generating technical analysis…</p>
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

        {view === 'error' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <div className="text-rose-600 font-semibold">An error occurred</div>
            <div className="max-w-xl">
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">{message || 'Unknown error'}</p>
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

        {view === 'display' && analysis && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <TechnicalAnalysisRenderer analysis={analysis} />
            </ScrollArea>

            <div className="flex gap-3">
              <Button
                variant="outline"
                className="mr-auto"
                onClick={() => requestAnalysis(true)}
                disabled={loading}
              >
                <RefreshCcw className="w-4 h-4 mr-2" />
                Regenerate
              </Button>
              <Button
                variant="outline"
                className="ml-auto"
                onClick={() => analysis && downloadTechnicalAnalysisPptx(analysis, `${analysis.analysis_title || 'Technical Analysis'}.pptx`)}
              >
                Export as PPT
              </Button>
              <Button
                onClick={() => analysis && downloadTechnicalAnalysisPdf(analysis, `${analysis.analysis_title || 'Technical Analysis'}.pdf`)}
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

export default TechnicalAnalysisModal;
