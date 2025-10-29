import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Clipboard } from 'lucide-react';
import { Document, StrategicRoadmapLLMOutput, api } from '@/lib/api';
import { toast } from 'sonner';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const SectionList: React.FC<{ title: string; items: string[] }> = ({ title, items }) => {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4 className="text-sm font-semibold mb-2">{title}</h4>
      <ul className="list-disc list-inside space-y-1 text-sm">
        {items.map((it, idx) => (
          <li key={idx} className="whitespace-pre-wrap">{it}</li>
        ))}
      </ul>
    </div>
  );
};

const RoadmapRenderer: React.FC<{ roadmap: StrategicRoadmapLLMOutput }> = ({ roadmap }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-bold mb-1">{roadmap.roadmap_title}</h3>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Vision & End Goal</h4>
          <p className="text-sm whitespace-pre-wrap mb-2">{roadmap.vision_and_end_goal.description}</p>
          <SectionList title="Success Criteria" items={roadmap.vision_and_end_goal.success_criteria} />
        </div>
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Current Baseline</h4>
          <p className="text-sm whitespace-pre-wrap mb-2">{roadmap.current_baseline.summary}</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <SectionList title="Strengths" items={roadmap.current_baseline.swot.strengths} />
            <SectionList title="Weaknesses" items={roadmap.current_baseline.swot.weaknesses} />
            <SectionList title="Opportunities" items={roadmap.current_baseline.swot.opportunities} />
            <SectionList title="Threats" items={roadmap.current_baseline.swot.threats} />
          </div>
        </div>
      </div>

      <div className="p-3 border rounded-lg">
        <h4 className="font-semibold mb-2">Strategic Pillars</h4>
        <div className="grid md:grid-cols-2 gap-3">
          {roadmap.strategic_pillars.map((p, idx) => (
            <div key={idx} className="p-2 rounded-md bg-muted/30">
              <div className="font-medium">{p.pillar_name}</div>
              <div className="text-sm whitespace-pre-wrap">{p.description}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="p-3 border rounded-lg">
        <h4 className="font-semibold mb-2">Phased Roadmap</h4>
        <div className="space-y-3">
          {roadmap.phased_roadmap.map((ph, idx) => (
            <div key={idx} className="p-3 rounded-md border">
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium">{ph.phase}</div>
                <div className="text-xs text-muted-foreground">{ph.time_frame}</div>
              </div>
              <div className="grid md:grid-cols-3 gap-3">
                <SectionList title="Key Objectives" items={ph.key_objectives} />
                <SectionList title="Key Initiatives" items={ph.key_initiatives} />
                <SectionList title="Expected Outcomes" items={ph.expected_outcomes} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Enabling Technologies</h4>
          <SectionList title="" items={roadmap.enablers_and_dependencies.technologies} />
        </div>
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Skills & Resources</h4>
          <SectionList title="" items={roadmap.enablers_and_dependencies.skills_and_resources} />
        </div>
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Stakeholders</h4>
          <SectionList title="" items={roadmap.enablers_and_dependencies.stakeholders} />
        </div>
      </div>

      <div className="p-3 border rounded-lg">
        <h4 className="font-semibold mb-2">Risks & Mitigation</h4>
        <div className="space-y-2 text-sm">
          {roadmap.risks_and_mitigation.map((r, idx) => (
            <div key={idx} className="flex md:items-center md:gap-2 md:flex-row flex-col">
              <span className="font-medium">Risk:</span>
              <span className="flex-1 whitespace-pre-wrap">{r.risk}</span>
              <span className="font-medium md:ml-4">Mitigation:</span>
              <span className="flex-1 whitespace-pre-wrap">{r.mitigation_strategy}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="p-3 border rounded-lg">
        <h4 className="font-semibold mb-2">Key Metrics & Milestones</h4>
        <div className="grid md:grid-cols-2 gap-3">
          {roadmap.key_metrics_and_milestones.map((km, idx) => (
            <div key={idx} className="p-2 rounded-md bg-muted/30">
              <div className="font-medium mb-1">{km.year_or_phase}</div>
              <SectionList title="" items={km.metrics} />
            </div>
          ))}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Future Opportunities</h4>
          <SectionList title="" items={roadmap.future_opportunities} />
        </div>
        <div className="p-3 border rounded-lg">
          <h4 className="font-semibold mb-2">Additional Insights</h4>
          <div className="space-y-2 text-sm">
            {roadmap.llm_inferred_additions.map((ad, idx) => (
              <div key={idx}>
                <div className="font-medium">{ad.section_title}</div>
                <div className="whitespace-pre-wrap">{ad.content}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const RoadmapModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState<StrategicRoadmapLLMOutput | null>(null);
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
      const res = await api.roadmap(threadId, selectedDoc);
      if (res?.status && res.roadmap) {
        setRoadmap(res.roadmap);
        toast.success('Roadmap ready');
        // Stop any polling if running
        pollingActiveRef.current = false;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
      } else if (res?.status === false && res.message) {
        // Backend returns status: false with a progress message; keep polling UX minimal: just show message
        setMessage(res.message);
        toast.info(res.message);
        // Start polling until ready
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      } else if (res?.error) {
        toast.error(res.error);
      } else {
        setMessage('Generating roadmap...');
        lastPolledDocRef.current = selectedDoc;
        pollingActiveRef.current = true;
        schedulePoll();
      }
    } catch (e) {
      console.error('Error requesting roadmap:', e);
      toast.error('Failed to request roadmap');
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
        const res = await api.roadmap(threadId, docId);
        if (res?.status && res.roadmap) {
          setRoadmap(res.roadmap);
          setMessage(null);
          pollingActiveRef.current = false;
          return;
        }
        if (res?.message) setMessage(res.message);
      } catch (e) {
        // non-fatal; keep polling a bit longer
      }
      // schedule next poll if still active
      if (pollingActiveRef.current) schedulePoll();
    }, 5000);
  };

  const handleCopy = async () => {
    if (!roadmap) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(roadmap, null, 2));
      toast.success('Roadmap JSON copied');
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setSelectedDoc(null);
      setRoadmap(null);
      setMessage(null);
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

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Strategic Roadmap</DialogTitle>
          <DialogDescription>
            Select a document to generate a strategic roadmap. If it's not ready yet, you'll see a progress message.
          </DialogDescription>
        </DialogHeader>

        {!roadmap ? (
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
                  'Generate Roadmap'
                )}
              </Button>
              {message && <span className="text-sm text-muted-foreground">{message}</span>}
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            {/* Roadmap Display */}
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <RoadmapRenderer roadmap={roadmap} />
            </ScrollArea>

            {/* Action Buttons */}
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

export default RoadmapModal;
