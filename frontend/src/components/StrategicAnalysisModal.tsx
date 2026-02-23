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
  BookOpen,
  Target,
  Users,
  ShieldAlert,
  Layers,
  Rocket,
  TrendingUp,
  Eye,
  ArrowRight,
  RefreshCcw,
  Lightbulb,
} from 'lucide-react';
import { Document, StrategicAnalysisLLMOutput, api } from '@/lib/api';
import { downloadStrategicAnalysisPdf } from '@/lib/strategic-analysis-pdf';
import { downloadStrategicAnalysisPptx } from '@/lib/strategic-analysis-pptx';
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

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; tone?: 'emerald' | 'amber' | 'violet' | 'sky' | 'rose' | 'teal' | 'cyan' }>
  = ({ icon, title, tone = 'teal' }) => (
    <div className="flex items-center gap-2 mb-2">
      <div className={
        `p-2 rounded-md bg-${tone}-100 text-${tone}-700 dark:bg-${tone}-900/40 dark:text-${tone}-300`
      }>
        {icon}
      </div>
      <h4 className="font-semibold">{title}</h4>
    </div>
  );

const StrategicAnalysisRenderer: React.FC<{ analysis: StrategicAnalysisLLMOutput }> = ({ analysis }) => {
  return (
    <div className="space-y-6 animate-in fade-in-0 duration-300">
      {/* Header banner */}
      <div className="rounded-xl p-5 bg-gradient-to-r from-teal-500 via-cyan-500 to-emerald-500 text-white shadow-md">
        <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
          <BookOpen className="w-5 h-5" /> {analysis.analysis_title}
        </h3>
        <p className="text-xs/relaxed opacity-90">Strategic content extraction and analytical assessment of the document.</p>
      </div>

      {/* Executive Overview */}
      <Card className="p-4">
        <SectionHeader icon={<Eye className="w-4 h-4" />} title="Executive Overview" tone="teal" />
        <p className="text-sm whitespace-pre-wrap">{analysis.executive_overview}</p>
      </Card>

      {/* ─── PART 1: What's In The Document ─── */}
      <div className="rounded-lg border-2 border-teal-200 dark:border-teal-800/50 p-1">
        <div className="px-3 py-2 bg-teal-50 dark:bg-teal-900/20 rounded-t-md">
          <h3 className="text-sm font-semibold text-teal-700 dark:text-teal-300">Part 1 — Document Content Extraction</h3>
        </div>
        <div className="p-3 space-y-4">
          {/* Strategic Intent */}
          <Card className="p-4">
            <SectionHeader icon={<Target className="w-4 h-4" />} title="Strategic Intent" tone="emerald" />
            <div className="space-y-3 text-sm">
              <div>
                <div className="font-medium mb-1">Vision Statement</div>
                <p className="text-muted-foreground whitespace-pre-wrap">{analysis.strategic_intent.vision_statement}</p>
              </div>
              <div>
                <div className="font-medium mb-2">Stated Objectives</div>
                <PillList
                  items={analysis.strategic_intent.stated_objectives}
                  className="bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 hover:border-emerald-300 dark:bg-emerald-900/40 dark:border-emerald-800/50 dark:hover:bg-emerald-800 dark:hover:border-emerald-700/60 dark:text-emerald-300"
                />
              </div>
              <div>
                <div className="font-medium mb-2">Implicit Aspirations</div>
                <PillList
                  items={analysis.strategic_intent.implicit_aspirations}
                  className="bg-teal-100 text-teal-700 border border-teal-200 hover:bg-teal-200 hover:border-teal-300 dark:bg-teal-900/40 dark:border-teal-800/50 dark:hover:bg-teal-800 dark:hover:border-teal-700/60 dark:text-teal-300"
                />
              </div>
            </div>
          </Card>

          {/* Strategic Positioning */}
          <Card className="p-4">
            <SectionHeader icon={<Layers className="w-4 h-4" />} title="Strategic Positioning" tone="cyan" />
            <div className="grid md:grid-cols-3 gap-3 text-sm">
              <Card className="p-3 border-cyan-200 dark:border-cyan-900/40">
                <div className="font-medium mb-1">Current Position</div>
                <div className="text-muted-foreground whitespace-pre-wrap">{analysis.strategic_positioning.current_position}</div>
              </Card>
              <Card className="p-3 border-emerald-200 dark:border-emerald-900/40">
                <div className="font-medium mb-1">Target Position</div>
                <div className="text-muted-foreground whitespace-pre-wrap">{analysis.strategic_positioning.target_position}</div>
              </Card>
              <Card className="p-3 border-teal-200 dark:border-teal-900/40">
                <div className="font-medium mb-1">Competitive Landscape</div>
                <div className="text-muted-foreground whitespace-pre-wrap">{analysis.strategic_positioning.competitive_landscape}</div>
              </Card>
            </div>
          </Card>

          {/* Key Strategic Themes */}
          {analysis.key_strategic_themes && analysis.key_strategic_themes.length > 0 && (
            <Card className="p-4">
              <SectionHeader icon={<Lightbulb className="w-4 h-4" />} title="Key Strategic Themes" tone="amber" />
              <div className="space-y-2 text-sm">
                {analysis.key_strategic_themes.map((t, idx) => (
                  <Card key={idx} className="p-3 hover:shadow-sm transition-shadow">
                    <div className="font-medium">{t.theme}</div>
                    <div className="text-muted-foreground whitespace-pre-wrap mt-1">{t.description}</div>
                    <Separator className="my-2" />
                    <div className="text-xs"><span className="font-medium">Evidence:</span> <span className="whitespace-pre-wrap">{t.evidence_from_document}</span></div>
                  </Card>
                ))}
              </div>
            </Card>
          )}

          {/* Stakeholders & Resources */}
          <div className="grid md:grid-cols-2 gap-4">
            {analysis.stakeholder_insights && analysis.stakeholder_insights.length > 0 && (
              <Card className="p-4">
                <SectionHeader icon={<Users className="w-4 h-4" />} title="Stakeholder Insights" tone="violet" />
                <div className="space-y-2 text-sm">
                  {analysis.stakeholder_insights.map((s, idx) => (
                    <Card key={idx} className="p-3">
                      <div className="flex items-center justify-between mb-1">
                        <div className="font-medium">{s.stakeholder}</div>
                        <Badge variant="outline" className={
                          s.influence_level?.toLowerCase() === 'high'
                            ? 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/40 dark:text-rose-300 dark:border-rose-800/50'
                            : s.influence_level?.toLowerCase() === 'medium'
                              ? 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800/50'
                              : 'bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/40 dark:text-sky-300 dark:border-sky-800/50'
                        }>{s.influence_level}</Badge>
                      </div>
                      <div className="text-muted-foreground whitespace-pre-wrap">{s.role_or_interest}</div>
                    </Card>
                  ))}
                </div>
              </Card>
            )}
            {analysis.resources_and_capabilities && analysis.resources_and_capabilities.length > 0 && (
              <Card className="p-4">
                <SectionHeader icon={<Layers className="w-4 h-4" />} title="Resources & Capabilities" tone="sky" />
                <div className="space-y-2 text-sm">
                  {analysis.resources_and_capabilities.map((r, idx) => (
                    <Card key={idx} className="p-3">
                      <div className="font-medium">{r.resource}</div>
                      <div className="text-muted-foreground whitespace-pre-wrap mt-1">{r.current_state}</div>
                      <Separator className="my-2" />
                      <div className="text-xs"><span className="font-medium">Strategic Relevance:</span> {r.strategic_relevance}</div>
                    </Card>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Identified Risks */}
          {analysis.identified_risks && analysis.identified_risks.length > 0 && (
            <Card className="p-4">
              <SectionHeader icon={<ShieldAlert className="w-4 h-4" />} title="Identified Risks" tone="rose" />
              <div className="space-y-2 text-sm">
                {analysis.identified_risks.map((r, idx) => (
                  <Card key={idx} className="p-3">
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-medium">{r.risk}</div>
                      <Badge variant="outline" className={
                        r.severity?.toLowerCase() === 'high'
                          ? 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/40 dark:text-rose-300 dark:border-rose-800/50'
                          : r.severity?.toLowerCase() === 'medium'
                            ? 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800/50'
                            : 'bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/40 dark:text-sky-300 dark:border-sky-800/50'
                      }>{r.severity}</Badge>
                    </div>
                    <div className="text-muted-foreground whitespace-pre-wrap">{r.context}</div>
                  </Card>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* ─── PART 2: Analytical Assessment ─── */}
      <div className="rounded-lg border-2 border-cyan-200 dark:border-cyan-800/50 p-1">
        <div className="px-3 py-2 bg-cyan-50 dark:bg-cyan-900/20 rounded-t-md">
          <h3 className="text-sm font-semibold text-cyan-700 dark:text-cyan-300">Part 2 — Analytical Assessment</h3>
        </div>
        <div className="p-3 space-y-4">
          {/* Strategic Gaps & Observations */}
          {analysis.strategic_gaps_and_observations && analysis.strategic_gaps_and_observations.length > 0 && (
            <Card className="p-4">
              <SectionHeader icon={<Eye className="w-4 h-4" />} title="Strategic Gaps & Observations" tone="amber" />
              <PillList
                items={analysis.strategic_gaps_and_observations}
                className="bg-amber-100 text-amber-700 border border-amber-200 hover:bg-amber-200 hover:border-amber-300 dark:bg-amber-900/40 dark:border-amber-800/50 dark:hover:bg-amber-800 dark:hover:border-amber-700/60 dark:text-amber-300"
              />
            </Card>
          )}

          {/* Forward Looking Assessment */}
          <Card className="p-4">
            <SectionHeader icon={<Rocket className="w-4 h-4" />} title="Forward-Looking Assessment" tone="emerald" />
            <div className="space-y-4">
              <div className="grid md:grid-cols-3 gap-3">
                <Card className="p-3 border-emerald-200 dark:border-emerald-900/40">
                  <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><TrendingUp className="w-4 h-4" /> Opportunities</div>
                  <PillList
                    items={analysis.forward_looking_assessment.opportunities}
                    className="bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 hover:border-emerald-300 dark:bg-emerald-900/40 dark:border-emerald-800/50 dark:hover:bg-emerald-800 dark:hover:border-emerald-700/60 dark:text-emerald-300"
                  />
                </Card>
                <Card className="p-3 border-sky-200 dark:border-sky-900/40">
                  <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><ArrowRight className="w-4 h-4" /> Recommended Next Steps</div>
                  <PillList
                    items={analysis.forward_looking_assessment.recommended_next_steps}
                    className="bg-sky-100 text-sky-700 border border-sky-200 hover:bg-sky-200 hover:border-sky-300 dark:bg-sky-900/40 dark:border-sky-800/50 dark:hover:bg-sky-800 dark:hover:border-sky-700/60 dark:text-sky-300"
                  />
                </Card>
                <Card className="p-3 border-rose-200 dark:border-rose-900/40">
                  <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><ShieldAlert className="w-4 h-4" /> Potential Challenges</div>
                  <PillList
                    items={analysis.forward_looking_assessment.potential_challenges}
                    className="bg-rose-100 text-rose-700 border border-rose-200 hover:bg-rose-200 hover:border-rose-300 dark:bg-rose-900/40 dark:border-rose-800/50 dark:hover:bg-rose-800 dark:hover:border-rose-700/60 dark:text-rose-300"
                  />
                </Card>
              </div>
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

const StrategicAnalysisModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<StrategicAnalysisLLMOutput | null>(null);
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
        ? await api.strategicAnalysisGlobal(threadId, isRegenerate)
        : await api.strategicAnalysis(threadId, selectedDoc, isRegenerate);
      if (res?.status && res.strategic_analysis) {
        setAnalysis(res.strategic_analysis);
        toast.success('Strategic analysis ready');
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
        setMessage('Generating strategic analysis...');
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === 'Generating strategic analysis...' ? msgs : [...msgs, 'Generating strategic analysis...']));
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting strategic analysis:', e);
      toast.error('Failed to request strategic analysis');
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
          ? await api.strategicAnalysisGlobal(threadId)
          : await api.strategicAnalysis(threadId, docId);
        if (res?.status && res.strategic_analysis) {
          setAnalysis(res.strategic_analysis);
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
          <DialogTitle>Strategic Analysis</DialogTitle>
          <DialogDescription>
            {view === 'select' && 'Select a document (or All Documents) to generate a strategic analysis.'}
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
                          <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/90">Generate a strategic analysis using all uploaded documents.</p>
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
                  'Generate Strategic Analysis'
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
                  <p className="text-sm text-muted-foreground">Generating strategic analysis…</p>
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
              <StrategicAnalysisRenderer analysis={analysis} />
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
                onClick={() => analysis && downloadStrategicAnalysisPptx(analysis, `${analysis.analysis_title || 'Strategic Analysis'}.pptx`)}
              >
                Export as PPT
              </Button>
              <Button
                onClick={() => analysis && downloadStrategicAnalysisPdf(analysis, `${analysis.analysis_title || 'Strategic Analysis'}.pdf`)}
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

export default StrategicAnalysisModal;
