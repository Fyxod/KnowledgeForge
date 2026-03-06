import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  RefreshCcw,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Loader2,
  Pencil,
} from 'lucide-react';
import type { SectionState } from '@/lib/api';

interface SectionToolbarProps {
  section: SectionState;
  onApprove: () => void;
  onIterate: (feedback?: string) => void;
  onSelectVersion: (index: number) => void;
  onEdit: () => void;
  isIterating: boolean;
  isEditing: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-muted text-muted-foreground',
  generating: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  generated: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  approved: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  needs_revision: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
};

const SectionToolbar: React.FC<SectionToolbarProps> = ({
  section,
  onApprove,
  onIterate,
  onSelectVersion,
  onEdit,
  isIterating,
  isEditing,
}) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const versionCount = section.versions.length;
  const currentVersion = section.selected_version_index;

  const handleSubmitFeedback = () => {
    onIterate(feedback || undefined);
    setFeedback('');
    setShowFeedback(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge className={STATUS_COLORS[section.status] || STATUS_COLORS.pending}>
          {section.status.replace('_', ' ')}
        </Badge>

        {versionCount > 1 && (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => onSelectVersion(Math.max(0, currentVersion - 1))}
              disabled={currentVersion === 0}
            >
              <ChevronLeft className="w-3 h-3" />
            </Button>
            <span className="text-xs text-muted-foreground">
              v{currentVersion + 1}/{versionCount}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => onSelectVersion(Math.min(versionCount - 1, currentVersion + 1))}
              disabled={currentVersion === versionCount - 1}
            >
              <ChevronRight className="w-3 h-3" />
            </Button>
          </div>
        )}

        <div className="flex items-center gap-1 ml-auto">
          {section.status !== 'approved' && versionCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={onApprove}
            >
              <CheckCircle2 className="w-3 h-3 mr-1" /> Approve
            </Button>
          )}

          <Button
            variant={isEditing ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs"
            onClick={onEdit}
          >
            <Pencil className="w-3 h-3 mr-1" /> {isEditing ? 'Done' : 'Edit'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setShowFeedback(!showFeedback)}
            disabled={isIterating}
          >
            <MessageSquare className="w-3 h-3 mr-1" /> Feedback
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => onIterate()}
            disabled={isIterating}
          >
            {isIterating ? (
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            ) : (
              <RefreshCcw className="w-3 h-3 mr-1" />
            )}
            Regenerate
          </Button>
        </div>
      </div>

      {showFeedback && (
        <div className="flex gap-2">
          <Textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Describe what changes you'd like..."
            rows={2}
            className="text-sm flex-1"
          />
          <Button
            size="sm"
            onClick={handleSubmitFeedback}
            disabled={isIterating}
            className="self-end"
          >
            {isIterating ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Send'}
          </Button>
        </div>
      )}
    </div>
  );
};

export default SectionToolbar;
