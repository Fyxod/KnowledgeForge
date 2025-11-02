import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Loader2, Cpu, Wrench, ShieldAlert, Rocket, MapPin, TrendingUp, BarChart3 } from 'lucide-react';
import { Document, TechnicalRoadmapLLMOutput, api } from '@/lib/api';
import { toast } from 'sonner';
import { downloadTechnicalRoadmapPdf } from '@/lib/technical-roadmap-pdf';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const SectionList: React.FC<{ title?: string; items?: string[] }> = ({ title, items }) => {
  if (!items || items.length === 0) return null;
  return (
    <div>
      {title && <h4 className="text-sm font-semibold mb-2">{title}</h4>}
      <div className="flex flex-wrap gap-2">
        {items.map((it, idx) => (
          <div key={idx} className="px-2 py-1 bg-muted/40 rounded text-sm">{it}</div>
        ))}
      </div>
    </div>
  );
};

const TechnicalRoadmapRenderer: React.FC<{ roadmap: TechnicalRoadmapLLMOutput }> = ({ roadmap }) => {
  return (
    <div className="space-y-6">
      <div className="rounded-xl p-4 bg-gradient-to-r from-sky-600 to-violet-600 text-white shadow-md">
        <h3 className="text-lg font-bold flex items-center gap-2"><Cpu className="w-5 h-5" /> {roadmap.roadmap_title}</h3>
        <p className="text-xs/relaxed opacity-90">Technical roadmap summarizing vision, domains, phased plan, enablers, and risks.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><MapPin className="w-4 h-4 text-sky-600" /><h4 className="font-semibold">Overall Vision</h4></div>
          <div className="text-sm whitespace-pre-wrap mb-2">{roadmap.overall_vision.goal}</div>
          <SectionList title="Success Metrics" items={roadmap.overall_vision.success_metrics} />
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><Wrench className="w-4 h-4 text-amber-600" /><h4 className="font-semibold">Current State</h4></div>
          <div className="text-sm whitespace-pre-wrap mb-2">{roadmap.current_state_analysis.summary}</div>
          <SectionList title="Key Challenges" items={roadmap.current_state_analysis.key_challenges} />
          <SectionList title="Existing Capabilities" items={roadmap.current_state_analysis.existing_capabilities} />
        </Card>
      </div>

      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2"><TrendingUp className="w-4 h-4 text-emerald-600" /><h4 className="font-semibold">Technology Domains</h4></div>
        <div className="grid md:grid-cols-2 gap-3">
          {roadmap.technology_domains.map((d, idx) => (
            <Card key={idx} className="p-3">
              <div className="font-medium">{d.domain_name}</div>
              <div className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">{d.description}</div>
            </Card>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2"><Rocket className="w-4 h-4 text-fuchsia-600" /><h4 className="font-semibold">Phased Roadmap</h4></div>
        <div className="grid md:grid-cols-3 gap-3">
          {[
            { label: 'Short term', phase: roadmap.phased_roadmap.short_term },
            { label: 'Mid term', phase: roadmap.phased_roadmap.mid_term },
            { label: 'Long term', phase: roadmap.phased_roadmap.long_term },
          ].map(({ label, phase }, idx) => (
            <Card key={idx} className="p-3">
              <div className="flex items-baseline justify-between mb-1">
                <div className="font-semibold">{label}</div>
                <div className="text-xs text-muted-foreground">{phase.time_frame}</div>
              </div>
              <SectionList title="Focus Areas" items={phase.focus_areas} />
              <div className="mt-2 text-sm font-semibold">Initiatives</div>
              <div className="space-y-2 mt-1">
                {phase.key_initiatives.map((it: any, i: number) => (
                  <Card key={i} className="p-2">
                    <div className="font-medium">{it.initiative}</div>
                    <div className="text-xs text-muted-foreground">{it.objective}</div>
                    <div className="text-xs text-muted-foreground">Outcome: {it.expected_outcome}</div>
                  </Card>
                ))}
              </div>
              <div className="mt-2">
                <SectionList title="Dependencies" items={phase.dependencies} />
              </div>
            </Card>
          ))}
        </div>
      </Card>

      <div className="grid md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><BarChart3 className="w-4 h-4 text-violet-600" /><h4 className="font-semibold">Key Enablers</h4></div>
          <SectionList items={roadmap.key_technology_enablers.map(e => `${e.enabler} — ${e.impact}`)} />
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><ShieldAlert className="w-4 h-4 text-rose-600" /><h4 className="font-semibold">Risks & Mitigation</h4></div>
          <div className="space-y-2 text-sm">
            {roadmap.risks_and_mitigations.map((r, idx) => (
              <Card key={idx} className="p-2">
                <div className="font-medium">Risk</div>
                <div className="text-sm whitespace-pre-wrap">{r.risk}</div>
                <div className="font-medium mt-1">Mitigation</div>
                <div className="text-sm whitespace-pre-wrap">{r.mitigation}</div>
              </Card>
            ))}
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2"><TrendingUp className="w-4 h-4 text-sky-600" /><h4 className="font-semibold">Innovation Opportunities</h4></div>
          <div className="space-y-2">
            {roadmap.innovation_opportunities.map((iop, idx) => (
              <Card key={idx} className="p-2">
                <div className="font-medium">{iop.idea} <span className="text-xs text-muted-foreground">({iop.maturity_level})</span></div>
                <div className="text-sm text-muted-foreground">{iop.description}</div>
              </Card>
            ))}
          </div>
        </Card>
      </div>

      {/* Tabular summary */}
      <Card className="p-4">
        <h4 className="font-semibold mb-2">Tabular Summary</h4>
        <div className="grid md:grid-cols-3 gap-3">
          {roadmap.tabular_summary.map((row, idx) => (
            <Card key={idx} className="p-3">
              <div className="font-medium">{row.time_frame}</div>
              <SectionList items={row.key_points} />
            </Card>
          ))}
        </div>
      </Card>

      {roadmap.llm_inferred_additions && (
        <Card className="p-4">
          <h4 className="font-semibold mb-2">LLM Inferred Additions</h4>
          <div className="space-y-2">
            {roadmap.llm_inferred_additions.map((ad, idx) => (
              <Card key={idx} className="p-2">
                <div className="font-medium">{ad.section_title}</div>
                <div className="text-sm text-muted-foreground">{ad.content}</div>
              </Card>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

const ALL_DOCS_ID = '__ALL_DOCS__';

const TechnicalRoadmapModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState<TechnicalRoadmapLLMOutput | null>(null);
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
      const res = isAll ? await api.technicalRoadmapGlobal(threadId) : await api.technicalRoadmap(threadId, selectedDoc);
      if (res?.status && res.technical_roadmap) {
        setRoadmap(res.technical_roadmap);
        toast.success('Technical roadmap ready');
        pollingActiveRef.current = false;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        setView('display');
      } else if (res?.error) {
        // Backend returned an explicit error
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
        setMessage('Generating technical roadmap...');
        setProgressMessages((msgs) => (msgs[msgs.length - 1] === 'Generating technical roadmap...' ? msgs : [...msgs, 'Generating technical roadmap...']));
        setView('progress');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting technical roadmap:', e);
      toast.error('Failed to request technical roadmap');
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
        const res = isAll ? await api.technicalRoadmapGlobal(threadId) : await api.technicalRoadmap(threadId, docId);
        if (res?.status && res.technical_roadmap) {
          setRoadmap(res.technical_roadmap);
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
        // ignore and retry
      }
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
          <DialogTitle>Technical Roadmap</DialogTitle>
          <DialogDescription>
            {view === 'select' && 'Select a document (or All Documents) to generate a technical roadmap.'}
            {view === 'progress' && (
              <span>Generating for: <span className="font-medium">{selectedDoc === ALL_DOCS_ID ? 'All Documents in Thread' : (selectedDocObj?.title || 'Selected Document')}</span></span>
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
                <Button variant="outline" size="sm" onClick={() => setSelectedDoc(null)} disabled={!selectedDoc}>Clear Selection</Button>
              </div>

              <ScrollArea className="h-64 border rounded-lg p-3">
                {documents.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No documents available in this thread</p>
                ) : (
                  <div className="space-y-3">
                    {/* All Documents option */}
                    <div key={ALL_DOCS_ID} className={`flex items-start space-x-3 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors ${selectedDoc === ALL_DOCS_ID ? 'bg-accent' : ''}`} onClick={() => handleToggle(ALL_DOCS_ID)}>
                      <Checkbox checked={selectedDoc === ALL_DOCS_ID} onCheckedChange={() => handleToggle(ALL_DOCS_ID)} className="mt-1" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">All Documents in Thread</p>
                        <p className="text-sm text-muted-foreground">Generate a technical roadmap using all uploaded documents.</p>
                      </div>
                    </div>
                    {documents.map((doc) => (
                      <div key={doc.docId} className={`flex items-start space-x-3 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors ${selectedDoc === doc.docId ? 'bg-accent' : ''}`} onClick={() => handleToggle(doc.docId)}>
                        <Checkbox checked={selectedDoc === doc.docId} onCheckedChange={() => handleToggle(doc.docId)} className="mt-1" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{doc.title}</p>
                          <p className="text-sm text-muted-foreground">{doc.type.toUpperCase()} • {new Date(doc.time_uploaded).toLocaleDateString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>

              <p className="text-sm text-muted-foreground">{selectedDoc ? (selectedDoc === ALL_DOCS_ID ? 'All documents selected' : '1 document selected') : 'No document selected'}</p>
            </div>

            <div className="flex items-center gap-3">
              <Button onClick={requestRoadmap} disabled={loading || !selectedDoc} className="bg-gradient-primary">
                {loading ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" />Requesting...</>) : 'Generate Technical Roadmap'}
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
                {progressMessages.length > 0 ? progressMessages.map((m, idx) => (<p key={idx} className="text-sm text-muted-foreground whitespace-pre-wrap">{m}</p>)) : (<p className="text-sm text-muted-foreground">Generating technical roadmap…</p>)}
              </div>
            </div>
            <div className="mt-4">
              <Button variant="outline" onClick={() => { pollingActiveRef.current = false; if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; } setView('select'); setProgressMessages([]); setMessage(null); setSelectedDoc(null); }}>Back to documents</Button>
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
                  setView('select');
                  setMessage(null);
                  setProgressMessages([]);
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
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <TechnicalRoadmapRenderer roadmap={roadmap} />
            </ScrollArea>

            <div className="flex gap-3">
              <Button
                className="ml-auto"
                onClick={() => roadmap && downloadTechnicalRoadmapPdf(roadmap, `${roadmap.roadmap_title || 'Technical Roadmap'}.pdf`)}
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

export default TechnicalRoadmapModal;
