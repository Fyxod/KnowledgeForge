import React from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import { Map as MapIcon, Cloud, FileText, MapPin, Sparkles, Lightbulb, Cpu } from 'lucide-react';
import MindMapModal from './MindMapModal';
import WordCloudModal from './WordCloudModal';
import SummaryModal from './SummaryModal';
import StrategicRoadmapModal from './StrategicRoadmapModal';
import TechnicalRoadmapModal from './TechnicalRoadmapModal';
import InsightsModal from './InsightsModal';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Label } from '@/components/ui/label';
import { Thread } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

interface Props {
  threadId?: string;
  threads?: Record<string, Thread>;
  // controlled collapsed state from parent (true = collapsed)
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

const RightSidebar: React.FC<Props> = ({ threadId, threads = {}, collapsed = false, onToggleCollapse }) => {
  const { refreshUser } = useAuth();
  // internal open state for modals
  const [mindOpen, setMindOpen] = React.useState(false);
  const [wordOpen, setWordOpen] = React.useState(false);
  const [docsOpen, setDocsOpen] = React.useState(false);
  const [roadmapOpen, setRoadmapOpen] = React.useState(false);
  const [techRoadmapOpen, setTechRoadmapOpen] = React.useState(false);
  const [summaryOpen, setSummaryOpen] = React.useState(false);
  const [insightsOpen, setInsightsOpen] = React.useState(false);

  const documents = React.useMemo(() => {
    if (!threadId) return [];
    const t = threads[threadId];
    return t?.documents || [];
  }, [threadId, threads]);

  const openAfterRefresh = async (setter: (v: boolean) => void) => {
    try {
      // Fetch latest user/threads so documents reflect recent uploads
      await refreshUser();
    } catch (e) {
      // Non-blocking: if refresh fails, still open with current data
      console.debug('RightSidebar refreshUser failed (non-blocking):', e);
    } finally {
      setter(true);
    }
  };

  return (
    <div className="h-full min-h-0 min-w-0 flex flex-col">
      {/* Match the header sizing/style used in `ThreadSidebar` so the collapse control lines up visually */}
      <div
        className="w-full flex items-center justify-center border-l bg-sidebar p-4 border-b cursor-pointer"
        role="button"
        tabIndex={0}
        aria-label={collapsed ? 'Expand right sidebar' : 'Collapse right sidebar'}
        onClick={() => onToggleCollapse && onToggleCollapse()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onToggleCollapse && onToggleCollapse();
          }
        }}
      >
        <Button variant="ghost" className="h-10 w-10" onClick={(e) => { e.stopPropagation(); onToggleCollapse && onToggleCollapse(); }} aria-label={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 5l7 7-7 7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg> : <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M15 19l-7-7 7-7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
        </Button>
      </div>

      <div className="flex-1 w-full flex flex-col items-start pt-4 px-3 border-l bg-background">
        {/* Studio buttons moved up here. When collapsed, show icon-only column; when expanded show labeled buttons */}
        {collapsed ? (
          <div className="flex flex-col items-center w-full space-y-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setDocsOpen)} disabled={!threadId} aria-label="Documents">
                  <FileText className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Documents</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setSummaryOpen)} disabled={!threadId} aria-label="Summary">
                  <Sparkles className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Summary</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setInsightsOpen)} disabled={!threadId} aria-label="Insights">
                  <Lightbulb className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Insights</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setMindOpen)} disabled={!threadId} aria-label="Mind Map">
                  <MapIcon className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Mind Map</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setWordOpen)} disabled={!threadId} aria-label="Word Cloud">
                  <Cloud className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Word Cloud</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setRoadmapOpen)} disabled={!threadId} aria-label="Strategic Roadmap">
                  <MapPin className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Strategic Roadmap</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={() => openAfterRefresh(setTechRoadmapOpen)} disabled={!threadId} aria-label="Technical Roadmap">
                  <Cpu className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Technical Roadmap</TooltipContent>
            </Tooltip>
          </div>
        ) : (
          <div className="w-full">
            <div className="mb-2 font-semibold">Studio</div>
            <div className="space-y-2">
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setDocsOpen)} disabled={!threadId}>
                <FileText className="w-4 h-4 mr-2" /> Documents
              </Button>
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setSummaryOpen)} disabled={!threadId}>
                <Sparkles className="w-4 h-4 mr-2" /> Summary
              </Button>
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setInsightsOpen)} disabled={!threadId}>
                <Lightbulb className="w-4 h-4 mr-2" /> Insights
              </Button>
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setMindOpen)} disabled={!threadId}>
                <MapIcon className="w-4 h-4 mr-2" /> Mind Map
              </Button>
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setWordOpen)} disabled={!threadId}>
                <Cloud className="w-4 h-4 mr-2" /> Word Cloud
              </Button>
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setRoadmapOpen)} disabled={!threadId}>
                <MapPin className="w-4 h-4 mr-2" /> Strategic Roadmap
              </Button>
              <Button className="w-full justify-start" variant="ghost" onClick={() => openAfterRefresh(setTechRoadmapOpen)} disabled={!threadId}>
                <Cpu className="w-4 h-4 mr-2" /> Technical Roadmap
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
  <MindMapModal open={mindOpen} onOpenChange={setMindOpen} threadId={threadId ?? ''} />
  <WordCloudModal open={wordOpen} onOpenChange={setWordOpen} threadId={threadId ?? ''} documents={documents} />
  <SummaryModal open={summaryOpen} onOpenChange={setSummaryOpen} threadId={threadId ?? ''} documents={documents} />
  <InsightsModal open={insightsOpen} onOpenChange={setInsightsOpen} threadId={threadId ?? ''} documents={documents} />

      {/* Summary handled by SummaryModal above */}

      <Dialog open={docsOpen} onOpenChange={setDocsOpen}>
        <DialogContent className="max-w-lg max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Documents</DialogTitle>
            <DialogDescription>Documents in this thread</DialogDescription>
          </DialogHeader>
          <div className="mt-2">
            <ScrollArea className="h-64 border rounded-md p-2">
              {documents.length === 0 ? (
                <p className="text-sm text-muted-foreground p-4">No documents in this thread.</p>
              ) : (
                <div className="space-y-2">
                  {documents.map((d: any) => (
                    <div key={d.docId} className="p-2 rounded hover:bg-accent flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{d.title}</div>
                        <div className="text-sm text-muted-foreground">{d.type} • {new Date(d.time_uploaded).toLocaleDateString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </DialogContent>
      </Dialog>
  <StrategicRoadmapModal open={roadmapOpen} onOpenChange={setRoadmapOpen} threadId={threadId ?? ''} documents={documents} />
  <TechnicalRoadmapModal open={techRoadmapOpen} onOpenChange={setTechRoadmapOpen} threadId={threadId ?? ''} documents={documents} />
    </div>
    );
};

export default RightSidebar;
