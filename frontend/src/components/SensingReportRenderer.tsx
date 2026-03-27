import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import SafeMarkdownRenderer from '@/components/SafeMarkdownRenderer';
import { ChevronDown, ChevronRight, ExternalLink, Clock, TrendingUp, Lightbulb, FileText } from 'lucide-react';

interface TrendItem {
  trend_name: string;
  description: string;
  evidence: string[];
  impact_level: string;
  time_horizon: string;
}

interface ReportSection {
  section_title: string;
  content: string;
}

interface Recommendation {
  title: string;
  description: string;
  priority: string;
  related_trends: string[];
}

interface ClassifiedArticle {
  title: string;
  source: string;
  url: string;
  published_date: string;
  summary: string;
  relevance_score: number;
  quadrant: string;
  ring: string;
  technology_name: string;
  reasoning: string;
}

interface SensingReport {
  report_title: string;
  executive_summary: string;
  domain: string;
  date_range: string;
  total_articles_analyzed: number;
  key_trends: TrendItem[];
  report_sections: ReportSection[];
  radar_items: unknown[];
  recommendations: Recommendation[];
  notable_articles: ClassifiedArticle[];
}

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

const SensingReportRenderer: React.FC<SensingReportRendererProps> = ({ report, meta }) => {
  const [expandedTrends, setExpandedTrends] = useState<Set<number>>(new Set());

  const toggleTrend = (idx: number) => {
    setExpandedTrends(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <ScrollArea className="h-full">
      <div className="space-y-6 p-1">
        {/* Meta bar */}
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <Badge variant="outline">{report.domain}</Badge>
          <Badge variant="outline">{report.date_range}</Badge>
          <Badge variant="outline">{report.total_articles_analyzed} articles analyzed</Badge>
          <Badge variant="outline">{meta.execution_time_seconds}s generation time</Badge>
        </div>

        {/* Executive Summary */}
        <Card className="border-l-4 border-l-primary">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{report.executive_summary}</p>
          </CardContent>
        </Card>

        {/* Key Trends */}
        {report.key_trends?.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-base font-semibold flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Key Trends ({report.key_trends.length})
            </h3>
            {report.key_trends.map((trend, idx) => (
              <Card key={idx} className="overflow-hidden">
                <button
                  onClick={() => toggleTrend(idx)}
                  className="w-full text-left p-4 flex items-start justify-between hover:bg-muted/50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">{trend.trend_name}</span>
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
                      <div className="mt-2">
                        <span className="text-xs font-medium">Evidence:</span>
                        <ul className="list-disc list-inside text-xs text-muted-foreground mt-1">
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

        {/* Report Sections */}
        {report.report_sections?.length > 0 && (
          <div className="space-y-4">
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
            <h3 className="text-base font-semibold flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
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
                    <h4 className="text-sm font-medium">{rec.title}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{rec.description}</p>
                    {rec.related_trends?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {rec.related_trends.map((t, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {t}
                          </Badge>
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
            <h3 className="text-base font-semibold">Notable Articles</h3>
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
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">{article.source}</Badge>
                        <Badge variant="outline" className="text-xs">{article.quadrant}</Badge>
                        <Badge variant="outline" className="text-xs">{article.ring}</Badge>
                        <span className="text-xs text-muted-foreground">
                          Score: {article.relevance_score.toFixed(2)}
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
