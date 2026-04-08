import React, { useState, useRef, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Send, Loader2, MessageCircle } from 'lucide-react';
import SafeMarkdownRenderer from '@/components/SafeMarkdownRenderer';
import type { DeepDiveReport } from '@/lib/api';

interface SensingDeepDiveProps {
  report: DeepDiveReport;
  trackingId?: string;
  domain?: string;
  onFollowUp?: (question: string) => void;
  followUpMessages?: { role: string; content: string }[];
  followUpLoading?: boolean;
  suggestedQuestions?: string[];
}

const SensingDeepDive: React.FC<SensingDeepDiveProps> = ({
  report,
  trackingId,
  domain,
  onFollowUp,
  followUpMessages = [],
  followUpLoading = false,
  suggestedQuestions = [],
}) => {
  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [followUpMessages]);

  const handleSend = () => {
    if (inputValue.trim() && onFollowUp) {
      onFollowUp(inputValue.trim());
      setInputValue('');
    }
  };

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

      {/* Follow-Up Chat Section */}
      {trackingId && onFollowUp && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <MessageCircle className="w-4 h-4" />
              Follow-Up Questions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Conversation Messages */}
            {followUpMessages.length > 0 && (
              <div className="space-y-3 max-h-[300px] overflow-y-auto">
                {followUpMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      {msg.role === 'assistant' ? (
                        <SafeMarkdownRenderer content={msg.content} />
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}
                {followUpLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2 text-sm flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Thinking...
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}

            {/* Suggested Questions */}
            {suggestedQuestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => onFollowUp(q)}
                    disabled={followUpLoading}
                    className="text-xs bg-muted hover:bg-muted/80 rounded-full px-3 py-1.5 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* Chat Input */}
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={`Ask about ${report.technology_name}...`}
                disabled={followUpLoading}
                className="flex-1"
              />
              <Button
                size="sm"
                onClick={handleSend}
                disabled={!inputValue.trim() || followUpLoading}
              >
                {followUpLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SensingDeepDive;
