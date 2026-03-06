import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import SectionToolbar from './SectionToolbar';
import type { SectionState } from '@/lib/api';

interface DocumentPreviewProps {
  documentTitle: string;
  documentSubtitle?: string;
  sections: SectionState[];
  onApprove: (sectionId: string) => void;
  onIterate: (sectionId: string, feedback?: string) => void;
  onSelectVersion: (sectionId: string, index: number) => void;
  onEditSection: (sectionId: string, edits: { content?: string; bullet_points?: string[] }) => void;
  iteratingSection: string | null;
}

const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  documentTitle,
  documentSubtitle,
  sections,
  onApprove,
  onIterate,
  onSelectVersion,
  onEditSection,
  iteratingSection,
}) => {
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [editBullets, setEditBullets] = useState('');

  const startEditing = (sectionId: string, version: any) => {
    if (editingSectionId === sectionId) {
      // Save and stop editing
      const edits: { content?: string; bullet_points?: string[] } = {};
      if (version.content !== undefined) {
        edits.content = editContent;
      }
      if (version.bullet_points && version.bullet_points.length > 0) {
        edits.bullet_points = editBullets.split('\n').filter((l: string) => l.trim());
      }
      onEditSection(sectionId, edits);
      setEditingSectionId(null);
    } else {
      // Start editing
      setEditingSectionId(sectionId);
      setEditContent(version.content || '');
      setEditBullets(version.bullet_points ? version.bullet_points.join('\n') : '');
    }
  };
  return (
    <div className="space-y-6">
      {/* Document header */}
      <div className="text-center pb-4">
        <h2 className="text-2xl font-bold text-foreground">{documentTitle}</h2>
        {documentSubtitle && (
          <p className="text-sm text-muted-foreground mt-1">{documentSubtitle}</p>
        )}
        <Separator className="mt-4" />
      </div>

      {/* Sections */}
      {sections.map((section) => {
        const version = section.versions[section.selected_version_index];
        if (!version && section.status === 'pending') {
          return (
            <Card key={section.spec.section_id} className="p-4 opacity-50">
              <h3 className="font-semibold text-lg">{section.spec.title}</h3>
              <p className="text-sm text-muted-foreground italic">Pending generation...</p>
            </Card>
          );
        }
        if (!version) return null;

        const headingLevel = section.spec.heading_level;

        return (
          <Card key={section.spec.section_id} className="p-4 space-y-3">
            {/* Section toolbar */}
            <SectionToolbar
              section={section}
              onApprove={() => onApprove(section.spec.section_id)}
              onIterate={(fb) => onIterate(section.spec.section_id, fb)}
              onSelectVersion={(idx) => onSelectVersion(section.spec.section_id, idx)}
              onEdit={() => startEditing(section.spec.section_id, version)}
              isIterating={iteratingSection === section.spec.section_id}
              isEditing={editingSectionId === section.spec.section_id}
            />

            <Separator />

            {/* Heading */}
            {headingLevel === 1 && (
              <h3 className="text-xl font-bold text-foreground">{section.spec.title}</h3>
            )}
            {headingLevel === 2 && (
              <h4 className="text-lg font-semibold text-foreground">{section.spec.title}</h4>
            )}
            {headingLevel >= 3 && (
              <h5 className="text-base font-medium text-foreground">{section.spec.title}</h5>
            )}

            {/* Key takeaway */}
            {version.key_takeaway && (
              <p className="text-sm italic text-orange-600 dark:text-orange-400">
                Key Takeaway: {version.key_takeaway}
              </p>
            )}

            {/* Content */}
            {editingSectionId === section.spec.section_id ? (
              <div className="space-y-3">
                {version.content !== undefined && (
                  <Textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={Math.max(5, editContent.split('\n').length + 1)}
                    className="text-sm font-mono"
                    placeholder="Section content..."
                  />
                )}
                {version.bullet_points && version.bullet_points.length > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Bullet points (one per line):</p>
                    <Textarea
                      value={editBullets}
                      onChange={(e) => setEditBullets(e.target.value)}
                      rows={Math.max(3, editBullets.split('\n').length + 1)}
                      className="text-sm font-mono"
                      placeholder="One bullet point per line..."
                    />
                  </div>
                )}
              </div>
            ) : (
              <>
                {version.content && (
                  <div className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                    {version.content}
                  </div>
                )}
                {version.bullet_points && version.bullet_points.length > 0 && (
                  <ul className="list-disc list-inside space-y-1 text-sm text-foreground/90">
                    {version.bullet_points.map((bp, idx) => (
                      <li key={idx}>{bp}</li>
                    ))}
                  </ul>
                )}
              </>
            )}

            {/* Table */}
            {version.table_data && version.table_data.headers && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-muted/50">
                      {version.table_data.headers.map((h, idx) => (
                        <th key={idx} className="border px-3 py-2 text-left font-medium">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {version.table_data.rows?.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-muted/30">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="border px-3 py-2">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Speaker notes */}
            {version.speaker_notes && (
              <details className="text-xs text-muted-foreground">
                <summary className="cursor-pointer hover:text-foreground">Speaker Notes</summary>
                <p className="mt-1 pl-4 whitespace-pre-wrap">{version.speaker_notes}</p>
              </details>
            )}
          </Card>
        );
      })}
    </div>
  );
};

export default DocumentPreview;
