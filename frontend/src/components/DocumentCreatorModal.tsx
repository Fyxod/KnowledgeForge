import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Loader2,
  FileText,
  RefreshCcw,
  ShieldAlert,
  Download,
  CheckCircle2,
  ArrowLeft,
  ArrowRight,
} from 'lucide-react';
import {
  Document,
  api,
  type DocumentCreatorConfig,
  type DocumentType,
  type AudienceType,
  type ToneType,
  type ExportFormat,
  type OutlineSectionSpec,
  type SectionState,
  type ContentFormat,
} from '@/lib/api';
import OutlineEditor from '@/components/document-creator/OutlineEditor';
import DocumentPreview from '@/components/document-creator/DocumentPreview';
import { toast } from 'sonner';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
  documents: Document[];
};

const ALL_DOCS_ID = '__ALL_DOCS__';
const MAX_POLL_COUNT = 120; // 120 × 5s = 10 min

type View = 'configure' | 'outline' | 'progress' | 'preview' | 'error';

const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  presentation: 'Presentation',
  executive_summary: 'Executive Summary',
  technical_report: 'Technical Report',
  research_brief: 'Research Brief',
  project_proposal: 'Project Proposal',
  comparison_report: 'Comparison Report',
};

const AUDIENCE_LABELS: Record<AudienceType, string> = {
  executive: 'Executive',
  technical: 'Technical',
  general: 'General',
};

const TONE_LABELS: Record<ToneType, string> = {
  formal: 'Formal',
  professional: 'Professional',
  conversational: 'Conversational',
  academic: 'Academic',
};

const DocumentCreatorModal: React.FC<Props> = ({ open, onOpenChange, threadId, documents }) => {
  // View state
  const [view, setView] = useState<View>('configure');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Configure view
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [documentType, setDocumentType] = useState<DocumentType>('technical_report');
  const [audience, setAudience] = useState<AudienceType>('technical');
  const [tone, setTone] = useState<ToneType>('professional');
  const [lengthPref, setLengthPref] = useState('medium');
  const [customInstructions, setCustomInstructions] = useState('');

  // Outline view
  const [docGenId, setDocGenId] = useState<string | null>(null);
  const [outlineSections, setOutlineSections] = useState<OutlineSectionSpec[]>([]);
  const [documentTitle, setDocumentTitle] = useState('');
  const [documentSubtitle, setDocumentSubtitle] = useState('');

  // Progress view
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const pollingActiveRef = useRef(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef(0);

  // Preview view
  const [sections, setSections] = useState<SectionState[]>([]);
  const [iteratingSection, setIteratingSection] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('docx');
  const [exporting, setExporting] = useState(false);

  // ── Helpers ──

  const stopPolling = () => {
    pollingActiveRef.current = false;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  const resetState = () => {
    setView('configure');
    setLoading(false);
    setErrorMessage(null);
    setSelectedDocs([]);
    setDocumentType('technical_report');
    setAudience('technical');
    setTone('professional');
    setLengthPref('medium');
    setCustomInstructions('');
    setDocGenId(null);
    setOutlineSections([]);
    setDocumentTitle('');
    setDocumentSubtitle('');
    setProgressMessages([]);
    setSections([]);
    setIteratingSection(null);
    setExportFormat('docx');
    setExporting(false);
    stopPolling();
    pollCountRef.current = 0;
  };

  const handleClose = (open: boolean) => {
    if (!open) resetState();
    onOpenChange(open);
  };

  useEffect(() => {
    if (!open) stopPolling();
  }, [open]);

  // ── Document selection ──

  const toggleDoc = (docId: string) => {
    if (docId === ALL_DOCS_ID) {
      setSelectedDocs((prev) =>
        prev.includes(ALL_DOCS_ID) ? [] : [ALL_DOCS_ID],
      );
    } else {
      setSelectedDocs((prev) => {
        const without = prev.filter((d) => d !== ALL_DOCS_ID && d !== docId);
        return prev.includes(docId) ? without : [...without, docId];
      });
    }
  };

  // ── Step 1: Generate Outline ──

  const handleGenerateOutline = async () => {
    if (loading) return;
    if (selectedDocs.length === 0) {
      toast.error('Please select at least one document');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const config: DocumentCreatorConfig = {
        document_type: documentType,
        audience,
        tone,
        source_document_ids: selectedDocs.includes(ALL_DOCS_ID) ? null : selectedDocs,
        custom_instructions: customInstructions || null,
        length_preference: lengthPref,
      };

      const res = await api.documentCreatorOutline(threadId, config);
      if (res.tracking_id) {
        // Background generation — start polling
        setView('progress');
        setProgressMessages(['Generating document outline...']);
        pollingActiveRef.current = true;
        pollCountRef.current = 0;
        pollOutlineStatus(res.tracking_id);
      }
    } catch (e: any) {
      toast.error(e.message || 'Failed to generate outline');
      setErrorMessage(e.message);
      setView('error');
    } finally {
      setLoading(false);
    }
  };

  const pollOutlineStatus = (trackingId: string) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(async () => {
      if (!pollingActiveRef.current) return;
      pollCountRef.current += 1;

      if (pollCountRef.current >= MAX_POLL_COUNT) {
        stopPolling();
        setErrorMessage('Outline generation timed out. Please try again.');
        setView('error');
        return;
      }

      try {
        const res = await api.documentCreatorOutlineStatus(trackingId);
        if (res.status && res.outline) {
          // Completed — outline is ready
          stopPolling();
          setDocGenId(res.outline.doc_gen_id);
          setDocumentTitle(res.outline.document_title || 'Untitled Document');
          setDocumentSubtitle(res.outline.document_subtitle || '');
          setOutlineSections(
            res.outline.sections.map((s) => ({
              section_id: s.section_id,
              title: s.title,
              description: s.description,
              content_format: s.content_format as ContentFormat,
              heading_level: 1,
              guidance: null,
              source_document_ids: [],
              order: s.order,
            })),
          );
          setView('outline');
          toast.success('Outline generated');
          return;
        }
        if (res.failed) {
          stopPolling();
          setErrorMessage(res.error || 'Outline generation failed');
          setView('error');
          return;
        }
        // Still pending
        setProgressMessages((prev) => {
          const msg = `Generating outline... (${pollCountRef.current * 5}s)`;
          return prev[prev.length - 1] === msg ? prev : [...prev, msg];
        });
      } catch {
        // non-fatal
      }

      if (pollingActiveRef.current) pollOutlineStatus(trackingId);
    }, 5000);
  };

  // ── Step 2: Save outline & generate content ──

  const handleStartGeneration = async () => {
    if (!docGenId || loading) return;
    setLoading(true);

    try {
      // Save any outline edits
      await api.documentCreatorUpdateOutline(
        docGenId,
        outlineSections,
        documentTitle,
        documentSubtitle,
      );

      // Start content generation
      await api.documentCreatorGenerate(docGenId);

      setView('progress');
      setProgressMessages(['Starting section generation...']);
      pollingActiveRef.current = true;
      pollCountRef.current = 0;
      pollGenerationStatus();
    } catch (e: any) {
      toast.error(e.message || 'Failed to start generation');
      setErrorMessage(e.message);
      setView('error');
    } finally {
      setLoading(false);
    }
  };

  const pollGenerationStatus = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(async () => {
      if (!pollingActiveRef.current || !docGenId) return;
      pollCountRef.current += 1;

      if (pollCountRef.current >= MAX_POLL_COUNT) {
        stopPolling();
        setErrorMessage('Content generation timed out. Please try again.');
        setView('error');
        return;
      }

      try {
        const res = await api.documentCreatorStatus(docGenId);

        if (res.phase === 'ready' || res.phase === 'completed') {
          // All sections done — load full preview
          stopPolling();
          try {
            const preview = await api.documentCreatorPreview(docGenId);
            setSections(preview.sections);
            setDocumentTitle(preview.document_title || documentTitle);
            setDocumentSubtitle(preview.document_subtitle || documentSubtitle);
          } catch {
            // Preview load failed, but generation succeeded
          }
          setView('preview');
          toast.success('Document generated');
          return;
        }
        if (res.phase === 'failed') {
          stopPolling();
          setErrorMessage('Content generation failed');
          setView('error');
          return;
        }

        // Update progress from section statuses
        if (res.sections) {
          const msg = `Generating sections... (${res.completed_count}/${res.total_count} complete)`;
          setProgressMessages((prev) =>
            prev[prev.length - 1] === msg ? prev : [...prev, msg],
          );
        }
      } catch {
        // non-fatal
      }

      if (pollingActiveRef.current) pollGenerationStatus();
    }, 5000);
  };

  // ── Section actions ──

  const handleApprove = async (sectionId: string) => {
    if (!docGenId) return;
    try {
      await api.documentCreatorApprove(docGenId, sectionId);
      setSections((prev) =>
        prev.map((s) =>
          s.spec.section_id === sectionId ? { ...s, status: 'approved' } : s,
        ),
      );
      toast.success('Section approved');
    } catch (e: any) {
      toast.error(e.message || 'Failed to approve section');
    }
  };

  const handleIterate = async (sectionId: string, feedback?: string) => {
    if (!docGenId) return;
    setIteratingSection(sectionId);
    try {
      await api.documentCreatorIterate(docGenId, sectionId, feedback);
      // Refresh preview
      const preview = await api.documentCreatorPreview(docGenId);
      setSections(preview.sections);
      toast.success('Section regenerated');
    } catch (e: any) {
      toast.error(e.message || 'Failed to regenerate section');
    } finally {
      setIteratingSection(null);
    }
  };

  const handleSelectVersion = async (sectionId: string, index: number) => {
    if (!docGenId) return;
    try {
      await api.documentCreatorSelectVersion(docGenId, sectionId, index);
      setSections((prev) =>
        prev.map((s) =>
          s.spec.section_id === sectionId
            ? { ...s, selected_version_index: index }
            : s,
        ),
      );
    } catch (e: any) {
      toast.error(e.message || 'Failed to select version');
    }
  };

  // ── Export ──

  const handleExport = async () => {
    if (!docGenId || exporting) return;
    setExporting(true);
    try {
      const res = await api.documentCreatorExport(docGenId, exportFormat);
      if (res.filename) {
        const blob = await api.documentCreatorDownload(docGenId, res.filename);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = res.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success(`Downloaded ${res.filename}`);
      }
    } catch (e: any) {
      toast.error(e.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  // ── Render ──

  const allApproved = sections.length > 0 && sections.every((s) => s.status === 'approved');

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Document Creator
          </DialogTitle>
          <DialogDescription>
            {view === 'configure' && 'Configure your document and select source materials.'}
            {view === 'outline' && 'Review and edit the document outline before generation.'}
            {view === 'progress' && 'Generating your document...'}
            {view === 'preview' && 'Review, iterate, and export your document.'}
            {view === 'error' && 'An error occurred during generation.'}
          </DialogDescription>
        </DialogHeader>

        {/* ── Configure View ── */}
        {view === 'configure' && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            <ScrollArea className="flex-1 h-[60vh]">
              <div className="space-y-5 pr-4">
                {/* Document type & audience */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <Label className="text-xs mb-1 block">Document Type</Label>
                    <Select value={documentType} onValueChange={(v) => setDocumentType(v as DocumentType)}>
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(DOC_TYPE_LABELS) as DocumentType[]).map((t) => (
                          <SelectItem key={t} value={t}>{DOC_TYPE_LABELS[t]}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Audience</Label>
                    <Select value={audience} onValueChange={(v) => setAudience(v as AudienceType)}>
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(AUDIENCE_LABELS) as AudienceType[]).map((a) => (
                          <SelectItem key={a} value={a}>{AUDIENCE_LABELS[a]}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Tone</Label>
                    <Select value={tone} onValueChange={(v) => setTone(v as ToneType)}>
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(TONE_LABELS) as ToneType[]).map((t) => (
                          <SelectItem key={t} value={t}>{TONE_LABELS[t]}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs mb-1 block">Length</Label>
                    <Select value={lengthPref} onValueChange={setLengthPref}>
                      <SelectTrigger className="h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="short">Short</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="long">Long</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Source documents */}
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Source Documents</Label>
                  <ScrollArea className="h-48 border rounded-lg p-3">
                    <div className="space-y-2">
                      <div
                        className={`flex items-start space-x-3 p-2 rounded-lg cursor-pointer hover:bg-accent/30 transition-colors ${selectedDocs.includes(ALL_DOCS_ID) ? 'bg-accent/40' : ''}`}
                        onClick={() => toggleDoc(ALL_DOCS_ID)}
                      >
                        <Checkbox
                          checked={selectedDocs.includes(ALL_DOCS_ID)}
                          onCheckedChange={() => toggleDoc(ALL_DOCS_ID)}
                          className="mt-0.5"
                        />
                        <div>
                          <p className="font-medium text-sm">All Documents</p>
                          <p className="text-xs text-muted-foreground">Use all uploaded documents as source</p>
                        </div>
                      </div>
                      {documents.map((doc) => (
                        <div
                          key={doc.docId}
                          className={`flex items-start space-x-3 p-2 rounded-lg cursor-pointer hover:bg-accent/30 transition-colors ${selectedDocs.includes(doc.docId) ? 'bg-accent/40' : ''}`}
                          onClick={() => toggleDoc(doc.docId)}
                        >
                          <Checkbox
                            checked={selectedDocs.includes(doc.docId) || selectedDocs.includes(ALL_DOCS_ID)}
                            onCheckedChange={() => toggleDoc(doc.docId)}
                            className="mt-0.5"
                            disabled={selectedDocs.includes(ALL_DOCS_ID)}
                          />
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate" title={doc.title}>{doc.title}</p>
                            <p className="text-xs text-muted-foreground">
                              {doc.type.toUpperCase()} &bull; {new Date(doc.time_uploaded).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                {/* Custom instructions */}
                <div>
                  <Label className="text-sm font-semibold mb-1 block">Custom Instructions (optional)</Label>
                  <Textarea
                    value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    placeholder="Any specific requirements, focus areas, or constraints..."
                    rows={3}
                  />
                </div>
              </div>
            </ScrollArea>

            <Button
              onClick={handleGenerateOutline}
              disabled={loading || selectedDocs.length === 0}
              className="bg-gradient-primary"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating Outline...</>
              ) : (
                <><ArrowRight className="w-4 h-4 mr-2" /> Generate Outline</>
              )}
            </Button>
          </div>
        )}

        {/* ── Outline Editor View ── */}
        {view === 'outline' && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            <ScrollArea className="flex-1 h-[60vh]">
              <div className="pr-4">
                <OutlineEditor
                  sections={outlineSections}
                  documentTitle={documentTitle}
                  documentSubtitle={documentSubtitle}
                  onSectionsChange={setOutlineSections}
                  onTitleChange={setDocumentTitle}
                  onSubtitleChange={setDocumentSubtitle}
                />
              </div>
            </ScrollArea>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setView('configure')}
              >
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
              <Button
                onClick={handleStartGeneration}
                disabled={loading || outlineSections.length === 0}
                className="ml-auto bg-gradient-primary"
              >
                {loading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Starting...</>
                ) : (
                  <><ArrowRight className="w-4 h-4 mr-2" /> Generate Content</>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* ── Progress View ── */}
        {view === 'progress' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">Generating Document</h3>
              <div className="space-y-2">
                {progressMessages.length > 0 ? (
                  progressMessages.slice(-5).map((m, idx) => (
                    <p key={idx} className="text-sm text-muted-foreground">{m}</p>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Working on it...</p>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => {
                stopPolling();
                setView('configure');
                setProgressMessages([]);
              }}
            >
              Cancel
            </Button>
          </div>
        )}

        {/* ── Preview & Export View ── */}
        {view === 'preview' && (
          <div className="flex-1 overflow-hidden flex flex-col gap-4">
            <ScrollArea className="flex-1 border rounded-lg p-4 bg-muted/30 h-[60vh] overflow-auto">
              <DocumentPreview
                documentTitle={documentTitle}
                documentSubtitle={documentSubtitle}
                sections={sections}
                onApprove={handleApprove}
                onIterate={handleIterate}
                onSelectVersion={handleSelectVersion}
                iteratingSection={iteratingSection}
              />
            </ScrollArea>

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                onClick={() => setView('outline')}
              >
                <ArrowLeft className="w-4 h-4 mr-2" /> Edit Outline
              </Button>

              {allApproved && (
                <div className="flex items-center gap-1 text-sm text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" />
                  All sections approved
                </div>
              )}

              <div className="ml-auto flex items-center gap-2">
                <Select value={exportFormat} onValueChange={(v) => setExportFormat(v as ExportFormat)}>
                  <SelectTrigger className="w-28 h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="docx">DOCX</SelectItem>
                    <SelectItem value="pptx">PPTX</SelectItem>
                    <SelectItem value="pdf">PDF</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={handleExport} disabled={exporting}>
                  {exporting ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Exporting...</>
                  ) : (
                    <><Download className="w-4 h-4 mr-2" /> Export</>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ── Error View ── */}
        {view === 'error' && (
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
              <ShieldAlert className="w-6 h-6 text-destructive" />
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">Generation Failed</h3>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {errorMessage || 'An unexpected error occurred.'}
              </p>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" onClick={() => { setView('configure'); setErrorMessage(null); setProgressMessages([]); }}>
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
              <Button onClick={handleGenerateOutline} disabled={loading}>
                {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Retrying...</> : <><RefreshCcw className="w-4 h-4 mr-2" />Retry</>}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default DocumentCreatorModal;
