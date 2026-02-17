/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { InsightsLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, CW, FONT,
    s, SlideWriter,
} from './pptx-slide-writer';

const colors = {
    primary: '6d56f1',
    accent1: 'F59E0B',
    accent2: '5341c8',
    success: '10B981',
    danger: 'EF4444',
    slate600: '475569',
    slate800: '1F2937',
    headerBg: 'e3defc',
    border: 'c4bcf0',
};

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadInsightsPptx(insights: InsightsLLMOutput, filename?: string) {
    const title = insights?.document_summary?.title || 'Insights';
    const purpose = insights?.document_summary?.purpose || '';

    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'LETTER_PORTRAIT', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'LETTER_PORTRAIT';
    pptx.author = 'NotebookLM';
    pptx.subject = 'Insights';
    pptx.title = s(title);

    const w = new SlideWriter(pptx);
    w.newSlide();

    // ── Title & Summary ────────────────────────────────────────────────────
    w.addTitle(title);
    if (purpose) w.addSubtitle(purpose);

    if (insights.document_summary?.key_themes?.length > 0) {
        w.addBullets(insights.document_summary.key_themes);
    }

    // ── Key Discussion Points ──────────────────────────────────────────────
    if (insights.key_discussion_points?.length > 0) {
        w.addSectionHeader('Key Discussion Points', colors.primary);
        for (const p of insights.key_discussion_points) {
            w.addSubheading(p.topic);
            w.addText(p.details);
        }
    }

    // ── Strengths ──────────────────────────────────────────────────────────
    if (insights.strengths?.length > 0) {
        w.addSectionHeader('Strengths', colors.success);
        for (const st of insights.strengths) {
            w.addSubheading(st.aspect);
            w.addText(st.evidence_or_example);
        }
    }

    // ── Gaps & Improvements ────────────────────────────────────────────────
    if (insights.improvement_or_missing_areas?.length > 0) {
        w.addSectionHeader('Gaps & Improvements', colors.danger);
        const gapRows: any[][] = [[
            { text: 'Gap', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
            { text: 'Suggested Improvement', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
        ]];
        insights.improvement_or_missing_areas.forEach((g) => {
            gapRows.push([{ text: s(g.gap) }, { text: s(g.suggested_improvement) }]);
        });
        w.addTable(gapRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.border });
    }

    // ── Innovation Aspects ─────────────────────────────────────────────────
    if (insights.innovation_aspects?.length > 0) {
        w.addSectionHeader('Innovation Aspects', colors.accent1);
        for (const inn of insights.innovation_aspects) {
            w.addSubheading(inn.innovation_title);
            w.addText(inn.description);
            w.addText(`Potential Impact: ${inn.potential_impact}`, { color: colors.slate600 });
        }
    }

    // ── Future Considerations ──────────────────────────────────────────────
    if (insights.future_considerations?.length > 0) {
        w.addSectionHeader('Future Considerations', colors.accent2);
        for (const f of insights.future_considerations) {
            w.addSubheading(f.focus_area);
            w.addText(f.recommendation);
        }
    }

    // ── Pseudocode / Technical Outline ─────────────────────────────────────
    if (insights.pseudocode_or_technical_outline && insights.pseudocode_or_technical_outline.length > 0) {
        w.addSectionHeader('Pseudocode / Technical Outline', colors.primary);
        for (const p of insights.pseudocode_or_technical_outline) {
            if (p.section) w.addSubheading(p.section);
            if (p.pseudocode) w.addText(p.pseudocode, { fontSize: FONT.code });
        }
    }

    // ── Additional Insights ────────────────────────────────────────────────
    if (insights.llm_inferred_additions && insights.llm_inferred_additions.length > 0) {
        w.addSectionHeader('Additional Insights', colors.slate600);
        for (const a of insights.llm_inferred_additions) {
            w.addSubheading(a.section_title);
            w.addText(a.content);
        }
    }

    w.finalize();

    const safe = (title || 'insights').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'insights';
    const name = filename || `${safe} - Insights.pptx`;
    pptx.writeFile({ fileName: name });
}
