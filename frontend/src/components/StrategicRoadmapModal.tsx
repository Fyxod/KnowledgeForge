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
  Target,
  ShieldAlert,
  BarChart3,
  Rocket,
  Cpu,
  Wrench,
  Users,
  Layers,
  TrendingUp,
  MapPin,
  ListChecks,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import { Document, StrategicRoadmapLLMOutput, api } from '@/lib/api';
import { downloadStrategicRoadmapPdf } from '@/lib/strategic-roadmap-pdf';
import { toast } from 'sonner';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const SectionList: React.FC<{ title: string; items: string[]; badgeStyle?: string }> = ({ title, items, badgeStyle }) => {
  if (!items || items.length === 0) return null;
  const baseClass = badgeStyle
    ? `transition-colors ${badgeStyle}`
    : 'transition-colors bg-muted/80 text-muted-foreground border border-muted/50 hover:bg-muted hover:border-primary/40 dark:bg-muted/30 dark:border-muted/40 dark:hover:bg-muted/40';
  return (
    <div>
      {title && <h4 className="text-sm font-semibold mb-2">{title}</h4>}
      <div className="flex flex-wrap gap-2">
        {items.map((it, idx) => (
          <Badge key={idx} variant="outline" className={baseClass}>{it}</Badge>
        ))}
      </div>
    </div>
  );
};

const StrategicRoadmapRenderer: React.FC<{ roadmap: StrategicRoadmapLLMOutput }> = ({ roadmap }) => {
  return (
    <div className="space-y-6">
      {/* Header banner */}
      <div className="rounded-xl p-5 bg-gradient-to-r from-violet-600 via-fuchsia-500 to-sky-500 text-white shadow-md">
        <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
          <MapPin className="w-5 h-5" /> {roadmap.roadmap_title}
        </h3>
        <p className="text-xs/relaxed opacity-90">A strategic, phased plan with goals, enablers, risks, and measurable milestones.</p>
      </div>

      {/* Vision & Baseline */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 rounded-md bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
              <Target className="w-4 h-4" />
            </div>
            <h4 className="font-semibold">Vision & End Goal</h4>
          </div>
          <p className="text-sm whitespace-pre-wrap mb-3">{roadmap.vision_and_end_goal.description}</p>
          <SectionList
            title="Success Criteria"
            items={roadmap.vision_and_end_goal.success_criteria}
            badgeStyle="bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 hover:border-emerald-300 dark:bg-emerald-900/40 dark:border-emerald-800/50 dark:hover:bg-emerald-800 dark:hover:border-emerald-700/60 dark:text-emerald-300"
          />
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 rounded-md bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
              <Layers className="w-4 h-4" />
            </div>
            <h4 className="font-semibold">Current Baseline</h4>
          </div>
          <p className="text-sm whitespace-pre-wrap mb-3">{roadmap.current_baseline.summary}</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Card className="p-3 border-emerald-200 dark:border-emerald-900/40">
              <div className="font-medium mb-1">Strengths</div>
              <SectionList
                title=""
                items={roadmap.current_baseline.swot.strengths}
                badgeStyle="bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 hover:border-emerald-300 dark:bg-emerald-900/40 dark:border-emerald-800/50 dark:hover:bg-emerald-800 dark:hover:border-emerald-700/60 dark:text-emerald-300"
              />
            </Card>
            <Card className="p-3 border-amber-200 dark:border-amber-900/40">
              <div className="font-medium mb-1">Weaknesses</div>
              <SectionList
                title=""
                items={roadmap.current_baseline.swot.weaknesses}
                badgeStyle="bg-amber-100 text-amber-800 border border-amber-200 hover:bg-amber-200 hover:border-amber-300 dark:bg-amber-900/40 dark:border-amber-800/50 dark:hover:bg-amber-800 dark:hover:border-amber-700/60 dark:text-amber-300"
              />
            </Card>
            <Card className="p-3 border-sky-200 dark:border-sky-900/40">
              <div className="font-medium mb-1">Opportunities</div>
              <SectionList
                title=""
                items={roadmap.current_baseline.swot.opportunities}
                badgeStyle="bg-sky-100 text-sky-800 border border-sky-200 hover:bg-sky-200 hover:border-sky-300 dark:bg-sky-900/40 dark:border-sky-800/50 dark:hover:bg-sky-800 dark:hover:border-sky-700/60 dark:text-sky-300"
              />
            </Card>
            <Card className="p-3 border-rose-200 dark:border-rose-900/40">
              <div className="font-medium mb-1">Threats</div>
              <SectionList
                title=""
                items={roadmap.current_baseline.swot.threats}
                badgeStyle="bg-rose-100 text-rose-800 border border-rose-200 hover:bg-rose-200 hover:border-rose-300 dark:bg-rose-900/40 dark:border-rose-800/50 dark:hover:bg-rose-800 dark:hover:border-rose-700/60 dark:text-rose-300"
              />
            </Card>
          </div>
        </Card>
      </div>

      {/* Strategic pillars */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="p-2 rounded-md bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
            <Layers className="w-4 h-4" />
          </div>
          <h4 className="font-semibold">Strategic Pillars</h4>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          {roadmap.strategic_pillars.map((p, idx) => (
            <Card key={idx} className="p-3">
              <div className="font-medium">{p.pillar_name}</div>
              <div className="text-sm whitespace-pre-wrap mt-1 text-muted-foreground">{p.description}</div>
            </Card>
          ))}
        </div>
      </Card>

      {/* Phased timeline */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="p-2 rounded-md bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/40 dark:text-fuchsia-300">
            <Rocket className="w-4 h-4" />
          </div>
          <h4 className="font-semibold">Phased Strategic Roadmap</h4>
        </div>
        <div className="relative pl-5">
          <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-border" />
          <div className="space-y-4">
            {roadmap.phased_roadmap.map((ph, idx) => (
              <div key={idx} className="relative">
                <div className="absolute -left-[7px] top-2 w-3.5 h-3.5 rounded-full bg-gradient-to-br from-fuchsia-500 to-sky-500 shadow" />
                <Card className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-fuchsia-600" />
                      <div className="font-medium">{ph.phase}</div>
                    </div>
                    <Badge variant="outline">{ph.time_frame}</Badge>
                  </div>
                  <Separator className="my-2" />
                  <div className="grid md:grid-cols-3 gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><ListChecks className="w-4 h-4" /> Objectives</div>
                      <SectionList title="" items={ph.key_objectives} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><Rocket className="w-4 h-4" /> Initiatives</div>
                      <SectionList title="" items={ph.key_initiatives} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-2 text-sm font-semibold"><CheckCircle2 className="w-4 h-4" /> Outcomes</div>
                      <SectionList title="" items={ph.expected_outcomes} />
                    </div>
                  </div>
                </Card>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Enablers & dependencies */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><Cpu className="w-4 h-4 text-sky-600" /><h4 className="font-semibold">Enabling Technologies</h4></div>
          <SectionList title="" items={roadmap.enablers_and_dependencies.technologies} />
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><Wrench className="w-4 h-4 text-amber-600" /><h4 className="font-semibold">Skills & Resources</h4></div>
          <SectionList title="" items={roadmap.enablers_and_dependencies.skills_and_resources} />
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><Users className="w-4 h-4 text-emerald-600" /><h4 className="font-semibold">Stakeholders</h4></div>
          <SectionList title="" items={roadmap.enablers_and_dependencies.stakeholders} />
        </Card>
      </div>

      {/* Risks & mitigation */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2"><ShieldAlert className="w-4 h-4 text-rose-600" /><h4 className="font-semibold">Risks & Mitigation</h4></div>
        <div className="space-y-2 text-sm">
          {roadmap.risks_and_mitigation.map((r, idx) => (
            <Card key={idx} className="p-3">
              <div className="flex flex-col md:flex-row md:items-center md:gap-3">
                <div className="flex-1"><span className="font-medium">Risk:</span> <span className="whitespace-pre-wrap">{r.risk}</span></div>
                <ArrowRight className="hidden md:block w-4 h-4 text-muted-foreground" />
                <div className="flex-1 md:text-right"><span className="font-medium">Mitigation:</span> <span className="whitespace-pre-wrap">{r.mitigation_strategy}</span></div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      {/* Metrics & milestones */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2"><BarChart3 className="w-4 h-4 text-violet-600" /><h4 className="font-semibold">Key Metrics & Milestones</h4></div>
        <div className="grid md:grid-cols-2 gap-3">
          {roadmap.key_metrics_and_milestones.map((km, idx) => (
            <Card key={idx} className="p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium">{km.year_or_phase}</div>
                <Badge variant="outline">Milestone</Badge>
              </div>
              <SectionList title="" items={km.metrics} />
            </Card>
          ))}
        </div>
      </Card>

      {/* Future & additions */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><TrendingUp className="w-4 h-4 text-sky-600" /><h4 className="font-semibold">Future Opportunities</h4></div>
          <SectionList title="" items={roadmap.future_opportunities} />
        </Card>
        <Card className="p-4">
          <h4 className="font-semibold mb-2">Additional Insights</h4>
          <div className="space-y-2 text-sm">
            {roadmap.llm_inferred_additions.map((ad, idx) => (
              <Card key={idx} className="p-3">
                <div className="font-medium">{ad.section_title}</div>
                <div className="whitespace-pre-wrap text-muted-foreground mt-1">{ad.content}</div>
              </Card>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

const ALL_DOCS_ID = '__ALL_DOCS__';

const StrategicRoadmapModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState<StrategicRoadmapLLMOutput | null>(null);
  const [view, setView] = useState<'select' | 'progress' | 'display' | 'error'>('select');
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const pollingActiveRef = useRef<boolean>(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPolledDocRef = useRef<string | null>(null);

  const handleToggle = (docId: string) => {
    setSelectedDoc(prev => (prev === docId ? null : docId));
  };

  const requestRoadmap = async () => {
    if (!selectedDoc) {
      toast.error('Please select a document');
      return;
    }
    setLoading(true);
    setMessage(null);
    setRoadmap(null);

    try {
      const isAll = selectedDoc === ALL_DOCS_ID;
      const res = isAll
        ? await api.strategicRoadmapGlobal(threadId)
        : await api.strategicRoadmap(threadId, selectedDoc);
      if (res?.status && res.strategic_roadmap) {
        setRoadmap(res.strategic_roadmap);
        toast.success('Strategic roadmap ready');
        // Stop any polling if running
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
        // Backend returns status: false with a progress message; keep polling UX minimal: just show message
        setMessage(res.message);
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === res.message ? msgs : [...msgs, res.message!]));
        toast.info(res.message);
        setView('progress');
        // Start polling until ready
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      } else {
        setMessage('Generating strategic roadmap...');
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === 'Generating strategic roadmap...' ? msgs : [...msgs, 'Generating strategic roadmap...']));
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting strategic roadmap:', e);
      toast.error('Failed to request strategic roadmap');
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
          ? await api.strategicRoadmapGlobal(threadId)
          : await api.strategicRoadmap(threadId, docId);
        if (res?.status && res.strategic_roadmap) {
          setRoadmap(res.strategic_roadmap);
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
        // non-fatal; keep polling a bit longer
      }
      // schedule next poll if still active
      if (pollingActiveRef.current) schedulePoll();
    }, 5000);
  };


  const handleClose = (open: boolean) => {
    if (!open) {
      setSelectedDoc(null);
      setRoadmap(null);
      setMessage(null);
      setProgressMessages([]);
      setView('select');
      setLoading(false);
      // stop polling
      pollingActiveRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      lastPolledDocRef.current = null;
    }
    onOpenChange(open);
  };

  // If modal is closed externally, ensure timers are cleared
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
          <DialogTitle>Strategic Roadmap</DialogTitle>
          <DialogDescription>
            {view === 'select' && 'Select a document (or All Documents) to generate a strategic roadmap.'}
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
                        <p className="text-sm text-muted-foreground group-hover:text-primary-foreground/90">Generate a strategic roadmap using all uploaded documents.</p>
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
                onClick={requestRoadmap}
                disabled={loading || !selectedDoc}
                className="bg-gradient-primary"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Requesting...
                  </>
                ) : (
                  'Generate Strategic Roadmap'
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
                  <p className="text-sm text-muted-foreground">Generating strategic roadmap…</p>
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
                  // stop polling and return to selection
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

        {view === 'display' && roadmap && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            {/* Roadmap Display */}
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <StrategicRoadmapRenderer roadmap={roadmap} />
            </ScrollArea>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                className="ml-auto"
                onClick={() => roadmap && downloadStrategicRoadmapPdf(roadmap, `${roadmap.roadmap_title || 'Strategic Roadmap'}.pdf`)}
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

export default StrategicRoadmapModal;
