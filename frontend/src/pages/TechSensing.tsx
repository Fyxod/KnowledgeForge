import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Radar, Loader2, History, Trash2, RefreshCw, Download,
  Maximize2, Minimize2, X, Plus, XCircle,
} from 'lucide-react';
import { io, Socket } from 'socket.io-client';
import { api, getAuthToken } from '@/lib/api';
import type { SensingReportData, SensingHistoryItem } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { API_URL } from '../../config';
import TechRadar from '@/components/TechRadar';
import SensingReportRenderer from '@/components/SensingReportRenderer';
import { toast } from '@/components/ui/use-toast';
import { downloadSensingReportPdf } from '@/lib/sensing-report-pdf';

const POLL_INTERVAL_MS = 10_000;
const MAX_POLL_COUNT = 360; // 1 hour max

type DateRangePreset = 'last_week' | 'last_month' | 'custom';

const TechSensing: React.FC = () => {
  const { user } = useAuth();

  // Config state
  const [domain, setDomain] = useState('Generative AI');
  const [customReqs, setCustomReqs] = useState('');
  const [mustInclude, setMustInclude] = useState<string[]>([]);
  const [dontInclude, setDontInclude] = useState<string[]>([]);
  const [mustIncludeInput, setMustIncludeInput] = useState('');
  const [dontIncludeInput, setDontIncludeInput] = useState('');
  const [dateRange, setDateRange] = useState<DateRangePreset>('last_week');
  const [customDays, setCustomDays] = useState(14);

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [trackingId, setTrackingId] = useState<string | null>(null);

  // Report state
  const [reportData, setReportData] = useState<SensingReportData | null>(null);
  const [activeTab, setActiveTab] = useState('report');

  // History state
  const [history, setHistory] = useState<SensingHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Full-screen state
  const [isFullScreen, setIsFullScreen] = useState(false);

  // Refs
  const socketRef = useRef<Socket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollCountRef = useRef(0);

  const lookbackDays = dateRange === 'last_week' ? 7 : dateRange === 'last_month' ? 30 : customDays;

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  // Socket.IO for progress events
  useEffect(() => {
    if (!isGenerating || !trackingId || !user) return;

    const token = getAuthToken();
    const socket = io(API_URL, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      auth: token ? { token } : undefined,
    });
    socketRef.current = socket;

    const eventName = `${user.userId}/sensing_progress`;
    socket.on(eventName, (payload: { tracking_id: string; stage: string; progress: number; message: string }) => {
      if (payload.tracking_id !== trackingId) return;

      setProgress(payload.progress);
      setProgressMessage(payload.message);

      if (payload.stage === 'complete') {
        fetchReport(trackingId);
      } else if (payload.stage === 'error') {
        setIsGenerating(false);
        toast({ title: 'Generation Failed', description: payload.message, variant: 'destructive' });
      }
    });

    socket.on('connect_error', () => {
      startPolling(trackingId);
    });

    return () => {
      socket.off(eventName);
      socket.disconnect();
      socketRef.current = null;
    };
  }, [isGenerating, trackingId, user]);

  // ESC to exit full-screen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullScreen) setIsFullScreen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullScreen]);

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await api.sensingHistory();
      setHistory(res.reports || []);
    } catch {
      // Silently handle
    } finally {
      setHistoryLoading(false);
    }
  };

  const startPolling = useCallback((tid: string) => {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    pollCountRef.current = 0;

    const poll = async () => {
      if (pollCountRef.current >= MAX_POLL_COUNT) {
        setIsGenerating(false);
        toast({ title: 'Timeout', description: 'Report generation timed out.', variant: 'destructive' });
        return;
      }
      pollCountRef.current++;

      try {
        const res = await api.sensingStatus(tid);
        if (res.status === 'completed' && res.data) {
          setReportData(res.data);
          setIsGenerating(false);
          setProgress(100);
          setProgressMessage('Report ready');
          loadHistory();
          return;
        } else if (res.status === 'failed') {
          setIsGenerating(false);
          toast({ title: 'Generation Failed', description: res.error || 'Unknown error', variant: 'destructive' });
          return;
        }
      } catch {
        // Continue polling
      }

      pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
    };

    pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
  }, []);

  const fetchReport = async (tid: string) => {
    try {
      const res = await api.sensingStatus(tid);
      if (res.status === 'completed' && res.data) {
        setReportData(res.data);
        setIsGenerating(false);
        setProgress(100);
        loadHistory();
      } else if (res.status === 'pending') {
        startPolling(tid);
      } else {
        setIsGenerating(false);
        toast({ title: 'Error', description: res.error || 'Failed to load report', variant: 'destructive' });
      }
    } catch {
      startPolling(tid);
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setProgress(0);
    setProgressMessage('Starting...');
    setReportData(null);

    try {
      const res = await api.sensingGenerate(
        domain,
        customReqs,
        mustInclude.length > 0 ? mustInclude : undefined,
        dontInclude.length > 0 ? dontInclude : undefined,
        lookbackDays,
      );
      setTrackingId(res.tracking_id);
      startPolling(res.tracking_id);
    } catch (err) {
      setIsGenerating(false);
      toast({
        title: 'Failed to start',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleLoadReport = async (tid: string) => {
    setIsGenerating(true);
    setProgress(50);
    setProgressMessage('Loading report...');
    setTrackingId(tid);
    await fetchReport(tid);
  };

  const handleDeleteReport = async (tid: string) => {
    try {
      await api.sensingDelete(tid);
      setHistory(prev => prev.filter(r => r.tracking_id !== tid));
      if (reportData?.meta.tracking_id === tid) setReportData(null);
      toast({ title: 'Report deleted' });
    } catch {
      toast({ title: 'Failed to delete', variant: 'destructive' });
    }
  };

  const handleDownloadPdf = () => {
    if (!reportData) return;
    try {
      downloadSensingReportPdf(reportData);
      toast({ title: 'PDF download started' });
    } catch {
      toast({ title: 'PDF generation failed', variant: 'destructive' });
    }
  };

  const addKeyword = (
    list: string[],
    setter: React.Dispatch<React.SetStateAction<string[]>>,
    inputValue: string,
    inputSetter: React.Dispatch<React.SetStateAction<string>>,
  ) => {
    const trimmed = inputValue.trim();
    if (trimmed && !list.includes(trimmed)) {
      setter([...list, trimmed]);
    }
    inputSetter('');
  };

  const removeKeyword = (
    list: string[],
    setter: React.Dispatch<React.SetStateAction<string[]>>,
    keyword: string,
  ) => {
    setter(list.filter(k => k !== keyword));
  };

  const handleKeywordKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
    list: string[],
    setter: React.Dispatch<React.SetStateAction<string[]>>,
    inputValue: string,
    inputSetter: React.Dispatch<React.SetStateAction<string>>,
  ) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addKeyword(list, setter, inputValue, inputSetter);
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, []);

  // Full-screen report view
  if (isFullScreen && reportData) {
    return (
      <div className="fixed inset-0 z-50 bg-background flex flex-col">
        <div className="flex items-center justify-between px-6 py-3 border-b shrink-0 bg-background">
          <div className="flex items-center gap-3">
            <Radar className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-bold truncate">{reportData.report.report_title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleDownloadPdf}>
              <Download className="w-4 h-4 mr-1.5" />
              PDF
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setIsFullScreen(false)}>
              <Minimize2 className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setIsFullScreen(false)}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <div className="px-6 pt-2 shrink-0">
            <TabsList>
              <TabsTrigger value="report">Report</TabsTrigger>
              <TabsTrigger value="radar">Technology Radar</TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="report" className="flex-1 min-h-0 px-6 pb-4 mt-2">
            <SensingReportRenderer report={reportData.report} meta={reportData.meta} />
          </TabsContent>
          <TabsContent value="radar" className="flex-1 min-h-0 px-6 pb-4 mt-2 overflow-auto">
            <TechRadar items={reportData.report.radar_items || []} />
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Radar className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-bold">Tech Sensing</h2>
        </div>
        {reportData && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleDownloadPdf}>
              <Download className="w-4 h-4 mr-1.5" />
              Download PDF
            </Button>
            <Button variant="outline" size="sm" onClick={() => setIsFullScreen(true)}>
              <Maximize2 className="w-4 h-4 mr-1.5" />
              Full Screen
            </Button>
          </div>
        )}
      </div>

      {/* Configuration + History row */}
      <div className="flex gap-4 shrink-0">
        {/* Config card */}
        <Card className="flex-1">
          <CardContent className="p-4 space-y-3">
            {/* Row 1: Domain + Date Range */}
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Domain / Topic
                </label>
                <Input
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="e.g., Generative AI, Robotics, Quantum Computing, Cybersecurity"
                  disabled={isGenerating}
                />
              </div>
              <div className="w-40">
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Date Range
                </label>
                <Select
                  value={dateRange}
                  onValueChange={(v) => setDateRange(v as DateRangePreset)}
                  disabled={isGenerating}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="last_week">Last Week</SelectItem>
                    <SelectItem value="last_month">Last Month</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {dateRange === 'custom' && (
                <div className="w-28">
                  <label className="text-xs font-medium text-muted-foreground mb-1 block">
                    Days
                  </label>
                  <Input
                    type="number"
                    min={1}
                    max={365}
                    value={customDays}
                    onChange={(e) => setCustomDays(Math.max(1, Math.min(365, parseInt(e.target.value) || 7)))}
                    disabled={isGenerating}
                  />
                </div>
              )}
            </div>

            {/* Row 2: Must Include / Don't Include */}
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Must Include Keywords
                </label>
                <div className="flex gap-1.5">
                  <Input
                    value={mustIncludeInput}
                    onChange={(e) => setMustIncludeInput(e.target.value)}
                    onKeyDown={(e) => handleKeywordKeyDown(e, mustInclude, setMustInclude, mustIncludeInput, setMustIncludeInput)}
                    placeholder="Type keyword and press Enter"
                    disabled={isGenerating}
                    className="text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    className="shrink-0 h-9 w-9"
                    onClick={() => addKeyword(mustInclude, setMustInclude, mustIncludeInput, setMustIncludeInput)}
                    disabled={isGenerating || !mustIncludeInput.trim()}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </Button>
                </div>
                {mustInclude.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {mustInclude.map((kw) => (
                      <Badge key={kw} variant="secondary" className="text-xs gap-1 bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                        {kw}
                        <button onClick={() => removeKeyword(mustInclude, setMustInclude, kw)} disabled={isGenerating}>
                          <XCircle className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex-1">
                <label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Don't Include Keywords
                </label>
                <div className="flex gap-1.5">
                  <Input
                    value={dontIncludeInput}
                    onChange={(e) => setDontIncludeInput(e.target.value)}
                    onKeyDown={(e) => handleKeywordKeyDown(e, dontInclude, setDontInclude, dontIncludeInput, setDontIncludeInput)}
                    placeholder="Type keyword and press Enter"
                    disabled={isGenerating}
                    className="text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    className="shrink-0 h-9 w-9"
                    onClick={() => addKeyword(dontInclude, setDontInclude, dontIncludeInput, setDontIncludeInput)}
                    disabled={isGenerating || !dontIncludeInput.trim()}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </Button>
                </div>
                {dontInclude.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {dontInclude.map((kw) => (
                      <Badge key={kw} variant="secondary" className="text-xs gap-1 bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                        {kw}
                        <button onClick={() => removeKeyword(dontInclude, setDontInclude, kw)} disabled={isGenerating}>
                          <XCircle className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Row 3: Custom Requirements */}
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Custom Requirements (optional)
              </label>
              <Textarea
                value={customReqs}
                onChange={(e) => setCustomReqs(e.target.value)}
                placeholder="e.g., Focus on enterprise adoption, compare with previous trends..."
                rows={2}
                disabled={isGenerating}
              />
            </div>

            {/* Generate button + progress */}
            <div className="flex items-center gap-3">
              <Button onClick={handleGenerate} disabled={isGenerating || !domain.trim()}>
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Generate Report
                  </>
                )}
              </Button>
              {isGenerating && (
                <div className="flex-1 space-y-1">
                  <Progress value={progress} className="h-2" />
                  <p className="text-xs text-muted-foreground">{progressMessage}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* History card */}
        <Card className="w-72 shrink-0">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                <History className="w-3 h-3" />
                Report History
              </span>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={loadHistory}>
                <RefreshCw className={`w-3 h-3 ${historyLoading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <ScrollArea className="h-48">
              {history.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">No reports yet</p>
              ) : (
                <div className="space-y-1.5">
                  {history.map((item) => (
                    <div
                      key={item.tracking_id}
                      className={`flex items-center gap-1.5 p-1.5 rounded text-xs hover:bg-muted/50 cursor-pointer group ${
                        reportData?.meta.tracking_id === item.tracking_id ? 'bg-muted' : ''
                      }`}
                    >
                      <button
                        className="flex-1 text-left truncate"
                        onClick={() => handleLoadReport(item.tracking_id)}
                        disabled={isGenerating}
                      >
                        <span className="font-medium block truncate">{item.report_title || item.domain}</span>
                        <span className="text-muted-foreground">
                          {item.generated_at ? new Date(item.generated_at).toLocaleDateString() : ''}
                          {' · '}
                          {item.total_articles} articles
                        </span>
                      </button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5 opacity-0 group-hover:opacity-100"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteReport(item.tracking_id);
                        }}
                      >
                        <Trash2 className="w-3 h-3 text-destructive" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Report display */}
      {reportData ? (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="shrink-0">
            <TabsTrigger value="report">Report</TabsTrigger>
            <TabsTrigger value="radar">Technology Radar</TabsTrigger>
          </TabsList>
          <TabsContent value="report" className="flex-1 min-h-0 mt-2">
            <SensingReportRenderer report={reportData.report} meta={reportData.meta} />
          </TabsContent>
          <TabsContent value="radar" className="flex-1 min-h-0 mt-2 overflow-auto">
            <TechRadar items={reportData.report.radar_items || []} />
          </TabsContent>
        </Tabs>
      ) : !isGenerating ? (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center space-y-2">
            <Radar className="w-12 h-12 mx-auto opacity-20" />
            <p className="text-sm">Generate a report or select one from history</p>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default TechSensing;
