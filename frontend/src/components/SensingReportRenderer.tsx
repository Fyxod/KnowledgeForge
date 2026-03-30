import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import SafeMarkdownRenderer from '@/components/SafeMarkdownRenderer';
import {
  ChevronDown, ChevronRight, ExternalLink, Clock, TrendingUp,
  Lightbulb, FileText, Building2, Cpu, Target, Newspaper,
} from 'lucide-react';
import type {
  SensingReport, SensingRadarItem, SensingRadarItemDetail, SensingMarketSignal,
} from '@/lib/api';

interface Meta {
  tracking_id: string;
  domain: string;
  raw_article_count: number;
  deduped_article_count: number;
  classified_article_count: number;
  execution_time_seconds: number;
  generated_at: string;
}

interface SensingReportRendererProps {
  report: SensingReport;
  meta: Meta;
  highlightTechnology?: string;
  onDeepDive?: (technologyName: string) => void;
}

const impactColors: Record<string, string> = {
  'High': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  'Medium': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  'Low': 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
};

const priorityColors: Record<string, string> = {
  'Critical': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  'High': 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  'Medium': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  'Low': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
};

const ringColors: Record<string, string> = {
  'Adopt': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  'Trial': 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  'Assess': 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  'Hold': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const RING_ORDER = ['Adopt', 'Trial', 'Assess', 'Hold'];

const SensingReportRenderer: React.FC<SensingReportRendererProps> = ({ report, meta, highlightTechnology, onDeepDive }) => {
  const [expandedTrends, setExpandedTrends] = useState<Set<number>>(new Set());
  const [expandedRadarDetails, setExpandedRadarDetails] = useState<Set<number>>(new Set());
  const [expandedSignals, setExpandedSignals] = useState<Set<number>>(new Set());
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-expand and scroll to highlighted technology
  useEffect(() => {
    if (!highlightTechnology || !report.radar_item_details) return;
    const idx = report.radar_item_details.findIndex(
      d => d.technology_name.toLowerCase() === highlightTechnology.toLowerCase()
    );
    if (idx >= 0) {
      setExpandedRadarDetails(prev => new Set(prev).add(idx));
      // Delay scroll to allow expansion render
      setTimeout(() => {
        const el = document.getElementById(`radar-detail-${idx}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [highlightTechnology, report.radar_item_details]);

  const toggleSet = (setter: React.Dispatch<React.SetStateAction<Set<number>>>, idx: number) => {
    setter(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <ScrollArea className="h-full">
      <div className="space-y-8 py-2 px-1 max-w-5xl mx-auto">
        {/* Report Title + Meta */}
        <div>
          <h2 className="text-xl font-bold mb-2">{report.report_title}</h2>
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">{report.domain}</Badge>
            <Badge variant="outline">{report.date_range}</Badge>
            <Badge variant="outline">{report.total_articles_analyzed} articles analyzed</Badge>
            <Badge variant="outline">{Math.round(meta.execution_time_seconds / 60)}m generation time</Badge>
          </div>
        </div>

        {/* Executive Summary */}
        <Card className="border-l-4 border-l-blue-600">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="prose prose-sm dark:prose-invert max-w-none">
            <SafeMarkdownRenderer content={report.executive_summary} />
          </CardContent>
        </Card>

        {/* Key Trends */}
        {report.key_trends?.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-amber-600" />
              Key Trends ({report.key_trends.length})
            </h3>
            {report.key_trends.map((trend, idx) => (
              <Card key={idx} className="overflow-hidden">
                <button
                  onClick={() => toggleSet(setExpandedTrends, idx)}
                  className="w-full text-left p-4 flex items-start justify-between hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium">{trend.trend_name}</span>
                      <Badge className={impactColors[trend.impact_level] || 'bg-gray-100'} variant="secondary">
                        {trend.impact_level}
                      </Badge>
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {trend.time_horizon}
                      </span>
                    </div>
                  </div>
                  {expandedTrends.has(idx) ? (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                  )}
                </button>
                {expandedTrends.has(idx) && (
                  <div className="px-4 pb-4 border-t">
                    <p className="text-sm mt-3 text-muted-foreground">{trend.description}</p>
                    {trend.evidence?.length > 0 && (
                      <div className="mt-3">
                        <span className="text-xs font-medium">Evidence:</span>
                        <ul className="list-disc list-inside text-xs text-muted-foreground mt-1 space-y-0.5">
                          {trend.evidence.map((e, i) => (
                            <li key={i}>{e}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* Market Signals */}
        {report.market_signals?.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Building2 className="w-5 h-5 text-violet-600" />
              Market Signals ({report.market_signals.length})
            </h3>
            <p className="text-sm text-muted-foreground -mt-1">
              What prominent players are doing and where the industry is heading.
            </p>
            {report.market_signals.map((signal: SensingMarketSignal, idx: number) => (
              <Card key={idx} className="overflow-hidden border-l-4 border-l-violet-400">
                <button
                  onClick={() => toggleSet(setExpandedSignals, idx)}
                  className="w-full text-left p-4 flex items-start justify-between hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-violet-700 dark:text-violet-300">
                        {signal.company_or_player}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{signal.signal}</p>
                  </div>
                  {expandedSignals.has(idx) ? (
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                  )}
                </button>
                {expandedSignals.has(idx) && (
                  <div className="px-4 pb-4 border-t space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                      <div className="bg-violet-50 dark:bg-violet-900/20 rounded-lg p-3">
                        <h5 className="text-xs font-semibold text-violet-700 dark:text-violet-300 mb-1">
                          Strategic Intent
                        </h5>
                        <p className="text-sm text-muted-foreground">{signal.strategic_intent}</p>
                      </div>
                      <div className="bg-violet-50 dark:bg-violet-900/20 rounded-lg p-3">
                        <h5 className="text-xs font-semibold text-violet-700 dark:text-violet-300 mb-1">
                          Industry Impact
                        </h5>
                        <p className="text-sm text-muted-foreground">{signal.industry_impact}</p>
                      </div>
                    </div>
                    {signal.related_technologies?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        <span className="text-xs font-medium text-muted-foreground">Related:</span>
                        {signal.related_technologies.map((t, i) => (
                          <Badge key={i} variant="outline" className="text-xs">{t}</Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* Technology Deep Dives (Radar Item Details) */}
        {report.radar_item_details?.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Cpu className="w-5 h-5 text-emerald-600" />
              Technology Deep Dives ({report.radar_item_details.length})
            </h3>
            <p className="text-sm text-muted-foreground -mt-1">
              Detailed analysis of each technology on the radar.
            </p>
            {report.radar_item_details.map((item: SensingRadarItemDetail, idx: number) => {
              const radarItem = report.radar_items?.find(r => r.name === item.technology_name);
              return (
                <Card key={idx} id={`radar-detail-${idx}`} className={`overflow-hidden border-l-4 border-l-emerald-400${highlightTechnology?.toLowerCase() === item.technology_name.toLowerCase() ? ' ring-2 ring-emerald-400' : ''}`}>
                  <button
                    onClick={() => toggleSet(setExpandedRadarDetails, idx)}
                    className="w-full text-left p-4 flex items-start justify-between hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold">{item.technology_name}</span>
                        {radarItem && (
                          <>
                            <Badge className={ringColors[radarItem.ring] || 'bg-gray-100'} variant="secondary">
                              {radarItem.ring}
                            </Badge>
                            <Badge variant="outline" className="text-xs">{radarItem.quadrant}</Badge>
                            {radarItem.moved_in && (
                              <Badge className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300" variant="secondary">
                                {RING_ORDER.indexOf(radarItem.ring) < RING_ORDER.indexOf(radarItem.moved_in) ? '\u2191' : '\u2193'} Moved from {radarItem.moved_in}
                              </Badge>
                            )}
                          </>
                        )}
                      </div>
                      {!expandedRadarDetails.has(idx) && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{item.what_it_is}</p>
                      )}
                    </div>
                    {expandedRadarDetails.has(idx) ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
                    )}
                  </button>
                  {expandedRadarDetails.has(idx) && (
                    <div className="px-4 pb-4 border-t space-y-4 mt-3">
                      <div>
                        <h5 className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 mb-1">What It Is</h5>
                        <p className="text-sm text-muted-foreground">{item.what_it_is}</p>
                      </div>
                      <div>
                        <h5 className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 mb-1">Why It Matters</h5>
                        <p className="text-sm text-muted-foreground">{item.why_it_matters}</p>
                      </div>
                      <div>
                        <h5 className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 mb-1">Current State</h5>
                        <p className="text-sm text-muted-foreground">{item.current_state}</p>
                      </div>
                      {item.key_players?.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 mb-1">Key Players</h5>
                          <div className="flex flex-wrap gap-1.5">
                            {item.key_players.map((p, i) => (
                              <Badge key={i} variant="outline" className="text-xs">{p}</Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {item.practical_applications?.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 mb-1">
                            Practical Applications
                          </h5>
                          <ul className="list-disc list-inside text-sm text-muted-foreground space-y-0.5">
                            {item.practical_applications.map((a, i) => (
                              <li key={i}>{a}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {onDeepDive && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onDeepDive(item.technology_name); }}
                          className="text-xs text-emerald-600 hover:text-emerald-700 font-medium mt-2 flex items-center gap-1"
                        >
                          <Target className="w-3 h-3" />
                          Deep Dive Analysis
                        </button>
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Report Sections (Detailed Analysis) */}
        {report.report_sections?.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Target className="w-5 h-5 text-sky-600" />
              Detailed Analysis
            </h3>
            {report.report_sections.map((section, idx) => (
              <Card key={idx}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{section.section_title}</CardTitle>
                </CardHeader>
                <CardContent className="prose prose-sm dark:prose-invert max-w-none">
                  <SafeMarkdownRenderer content={section.content} />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Recommendations */}
        {report.recommendations?.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-orange-500" />
              Recommendations
            </h3>
            {report.recommendations.map((rec, idx) => (
              <Card key={idx} className="p-4">
                <div className="flex items-start gap-3">
                  <Badge
                    className={priorityColors[rec.priority] || 'bg-gray-100'}
                    variant="secondary"
                  >
                    {rec.priority}
                  </Badge>
                  <div className="flex-1">
                    <h4 className="font-medium">{rec.title}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{rec.description}</p>
                    {rec.related_trends?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {rec.related_trends.map((t, i) => (
                          <Badge key={i} variant="outline" className="text-xs">{t}</Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Notable Articles */}
        {report.notable_articles?.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Newspaper className="w-5 h-5 text-slate-600" />
              Notable Articles
            </h3>
            <div className="space-y-2">
              {report.notable_articles.map((article, idx) => (
                <Card key={idx} className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium hover:underline flex items-center gap-1"
                      >
                        {article.title}
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <Badge variant="outline" className="text-xs">{article.source}</Badge>
                        <Badge variant="outline" className="text-xs">{article.quadrant}</Badge>
                        <Badge className={ringColors[article.ring] || 'bg-gray-100'} variant="secondary">
                          {article.ring}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Score: {article.relevance_score?.toFixed(2)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{article.summary}</p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  );
};

export default SensingReportRenderer;
