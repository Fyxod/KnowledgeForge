import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { DeepDiveReport } from '@/lib/api';

interface SensingDeepDiveProps {
  report: DeepDiveReport;
}

const SensingDeepDive: React.FC<SensingDeepDiveProps> = ({ report }) => {
  return (
    <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
      {/* Title */}
      <h2 className="text-xl font-bold">{report.technology_name} — Deep Dive</h2>

      {/* Comprehensive Analysis */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Comprehensive Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {report.comprehensive_analysis}
          </div>
        </CardContent>
      </Card>

      {/* Technical Architecture */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Technical Architecture</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {report.technical_architecture}
          </div>
        </CardContent>
      </Card>

      {/* Competitive Landscape */}
      {report.competitive_landscape?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Competitive Landscape</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {report.competitive_landscape.map((comp, i) => (
                <div key={i} className="border rounded p-3">
                  <div className="font-medium text-sm">{comp.name}</div>
                  <div className="text-xs text-muted-foreground mt-1">{comp.approach}</div>
                  <div className="flex gap-4 mt-2 text-xs">
                    <div>
                      <span className="text-emerald-600 font-medium">Strengths: </span>
                      <span className="text-muted-foreground">{comp.strengths}</span>
                    </div>
                    <div>
                      <span className="text-red-600 font-medium">Weaknesses: </span>
                      <span className="text-muted-foreground">{comp.weaknesses}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Adoption Roadmap */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Adoption Roadmap</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {report.adoption_roadmap}
          </div>
        </CardContent>
      </Card>

      {/* Risk Assessment */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Risk Assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {report.risk_assessment}
          </div>
        </CardContent>
      </Card>

      {/* Key Resources */}
      {report.key_resources?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Key Resources</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {report.key_resources.map((res, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <Badge variant="outline" className="text-[10px] shrink-0">{res.type}</Badge>
                  {res.url ? (
                    <a href={res.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate">
                      {res.title}
                    </a>
                  ) : (
                    <span className="text-muted-foreground">{res.title}</span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {report.recommendations.map((rec, i) => (
                <li key={i} className="text-sm text-muted-foreground flex gap-2">
                  <span className="text-primary font-bold shrink-0">{i + 1}.</span>
                  {rec}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SensingDeepDive;
