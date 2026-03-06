import React from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { GripVertical, Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import type { OutlineSectionSpec, ContentFormat } from '@/lib/api';

interface OutlineEditorProps {
  sections: OutlineSectionSpec[];
  documentTitle: string;
  documentSubtitle: string;
  onSectionsChange: (sections: OutlineSectionSpec[]) => void;
  onTitleChange: (title: string) => void;
  onSubtitleChange: (subtitle: string) => void;
}

const FORMAT_LABELS: Record<ContentFormat, string> = {
  prose: 'Prose',
  bullets: 'Bullet Points',
  table: 'Table',
  mixed: 'Mixed',
};

const OutlineEditor: React.FC<OutlineEditorProps> = ({
  sections,
  documentTitle,
  documentSubtitle,
  onSectionsChange,
  onTitleChange,
  onSubtitleChange,
}) => {
  const updateSection = (index: number, updates: Partial<OutlineSectionSpec>) => {
    const updated = sections.map((s, i) => (i === index ? { ...s, ...updates } : s));
    onSectionsChange(updated);
  };

  const removeSection = (index: number) => {
    const updated = sections.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i }));
    onSectionsChange(updated);
  };

  const moveSection = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === sections.length - 1) return;
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    const updated = [...sections];
    [updated[index], updated[swapIdx]] = [updated[swapIdx], updated[index]];
    onSectionsChange(updated.map((s, i) => ({ ...s, order: i })));
  };

  const addSection = () => {
    const newSection: OutlineSectionSpec = {
      section_id: `section_${Date.now()}`,
      title: 'New Section',
      description: '',
      content_format: 'mixed',
      heading_level: 1,
      guidance: null,
      source_document_ids: [],
      order: sections.length,
    };
    onSectionsChange([...sections, newSection]);
  };

  return (
    <div className="space-y-4">
      {/* Document title & subtitle */}
      <div className="space-y-3">
        <div>
          <label className="text-sm font-medium mb-1 block">Document Title</label>
          <Input
            value={documentTitle}
            onChange={(e) => onTitleChange(e.target.value)}
            placeholder="Enter document title"
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">Subtitle (optional)</label>
          <Input
            value={documentSubtitle}
            onChange={(e) => onSubtitleChange(e.target.value)}
            placeholder="Enter subtitle"
          />
        </div>
      </div>

      {/* Section list */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">Sections ({sections.length})</label>
          <Button variant="outline" size="sm" onClick={addSection}>
            <Plus className="w-3 h-3 mr-1" /> Add Section
          </Button>
        </div>

        {sections.map((section, index) => (
          <Card key={section.section_id} className="p-3 space-y-2">
            <div className="flex items-start gap-2">
              <div className="flex flex-col items-center gap-0.5 pt-1">
                <GripVertical className="w-4 h-4 text-muted-foreground" />
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5"
                  onClick={() => moveSection(index, 'up')}
                  disabled={index === 0}
                >
                  <ChevronUp className="w-3 h-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5"
                  onClick={() => moveSection(index, 'down')}
                  disabled={index === sections.length - 1}
                >
                  <ChevronDown className="w-3 h-3" />
                </Button>
              </div>
              <div className="flex-1 space-y-2">
                <Input
                  value={section.title}
                  onChange={(e) => updateSection(index, { title: e.target.value })}
                  placeholder="Section title"
                  className="font-medium"
                />
                <Textarea
                  value={section.description}
                  onChange={(e) => updateSection(index, { description: e.target.value })}
                  placeholder="What should this section cover?"
                  rows={2}
                  className="text-sm"
                />
                <div className="flex gap-2">
                  <Select
                    value={section.content_format}
                    onValueChange={(v) => updateSection(index, { content_format: v as ContentFormat })}
                  >
                    <SelectTrigger className="w-36 h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(FORMAT_LABELS) as ContentFormat[]).map((fmt) => (
                        <SelectItem key={fmt} value={fmt}>{FORMAT_LABELS[fmt]}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={String(section.heading_level)}
                    onValueChange={(v) => updateSection(index, { heading_level: Number(v) })}
                  >
                    <SelectTrigger className="w-24 h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">H1</SelectItem>
                      <SelectItem value="2">H2</SelectItem>
                      <SelectItem value="3">H3</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input
                    value={section.guidance || ''}
                    onChange={(e) => updateSection(index, { guidance: e.target.value || null })}
                    placeholder="Additional guidance (optional)"
                    className="flex-1 h-8 text-xs"
                  />
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={() => removeSection(index)}
                disabled={sections.length <= 1}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default OutlineEditor;
