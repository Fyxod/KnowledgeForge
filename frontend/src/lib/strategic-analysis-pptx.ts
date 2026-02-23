/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { StrategicAnalysisLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, CW, FONT,
    s, estimateTextHeight, SlideWriter,
} from './pptx-slide-writer';

// ── Color palette (no # prefix for pptxgenjs) ─────────────────────────────
const colors = {
    bannerBg: '0D9488',       // teal-600
    teal:    { bg: 'CCFBF1', text: '0F766E' },
    cyan:    { bg: 'CFFAFE', text: '0E7490' },
    emerald: { bg: 'D1FAE5', text: '047857' },
    amber:   { bg: 'FEF3C7', text: 'B45309' },
    violet:  { bg: 'EDE9FE', text: '6D28D9' },
    sky:     { bg: 'E0F2FE', text: '0369A1' },
    rose:    { bg: 'FFE4E6', text: 'BE123C' },
    muted:   { bg: 'F1F5F9', text: '475569' },
    slate600: '475569',
    slate800: '1F2937',
    border: 'E2E8F0',
};

function renderTitleDetail(
    slide: any, title: string, detail: string,
    x: number, y: number, w: number,
    opts?: { extraLine?: string; extraColor?: string },
): number {
    const titleH = estimateTextHeight(title, FONT.subheading, w);
    slide.addText(s(title), {
        x, y, w, h: titleH,
        fontSize: FONT.subheading, bold: true, color: colors.slate800,
        valign: 'top',
    } as any);
    const detailH = estimateTextHeight(detail, FONT.body, w);
    slide.addText(s(detail), {
        x, y: y + titleH + 0.04, w, h: detailH,
        fontSize: FONT.body, color: colors.slate600,
        valign: 'top',
    } as any);
    let endY = y + titleH + 0.04 + detailH;
    if (opts?.extraLine) {
        const exH = 0.2;
        slide.addText(s(opts.extraLine), {
            x, y: endY + 0.04, w, h: exH,
            fontSize: 9, color: opts.extraColor ?? colors.amber.text, italic: true,
            valign: 'top',
        } as any);
        endY += 0.04 + exH;
    }
    return endY;
}

function renderCardPairs<T>(
    w: SlideWriter,
    items: T[],
    renderFn: (item: T, x: number, y: number, cw: number) => number,
    borderColor: string,
): void {
    for (let i = 0; i < items.length; i += 2) {
        if (i + 1 < items.length) {
            w.addCardPair(
                (x, y, cw) => renderFn(items[i], x, y, cw),
                (x, y, cw) => renderFn(items[i + 1], x, y, cw),
                { borderColor },
            );
        } else {
            w.addCard(
                (x, y, cw) => renderFn(items[i], x, y, cw),
                { borderColor },
            );
        }
    }
}

// ── Build slides ───────────────────────────────────────────────────────────
export function downloadStrategicAnalysisPptx(analysis: StrategicAnalysisLLMOutput, filename?: string) {
    const title = analysis?.analysis_title || 'Strategic Analysis';

    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'WIDE', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'WIDE';
    pptx.author = 'Knowledge Synthesis Platform';
    pptx.subject = 'Strategic Analysis';
    pptx.title = s(title);

    const w = new SlideWriter(pptx);

    // ── Title Slide ──
    w.addBanner(title, 'Strategic content extraction and analytical assessment.', colors.bannerBg);

    // ── Executive Overview ──
    w.addSectionBlock('Executive Overview', colors.teal.bg, colors.teal.text);
    w.addText(analysis.executive_overview, { color: colors.slate600 });

    // ── PART 1 ──
    w.addSectionBlock('Part 1 — Document Content Extraction', colors.teal.bg, colors.teal.text);

    // Strategic Intent
    w.addSectionBlock('Strategic Intent', colors.emerald.bg, colors.emerald.text);
    w.addSubheading('Vision Statement');
    w.addText(analysis.strategic_intent.vision_statement, { color: colors.slate600 });
    if (analysis.strategic_intent.stated_objectives?.length > 0) {
        w.addSubheading('Stated Objectives');
        w.addPills(analysis.strategic_intent.stated_objectives, colors.emerald.bg, colors.emerald.text);
    }
    if (analysis.strategic_intent.implicit_aspirations?.length > 0) {
        w.addSubheading('Implicit Aspirations');
        w.addPills(analysis.strategic_intent.implicit_aspirations, colors.teal.bg, colors.teal.text);
    }

    // Strategic Positioning
    w.addSectionBlock('Strategic Positioning', colors.cyan.bg, colors.cyan.text);
    w.addCard(
        (x, y, cw) => renderTitleDetail(w.currentSlide, 'Current Position', analysis.strategic_positioning.current_position, x, y, cw),
        { borderColor: colors.border },
    );
    w.addCard(
        (x, y, cw) => renderTitleDetail(w.currentSlide, 'Target Position', analysis.strategic_positioning.target_position, x, y, cw),
        { borderColor: colors.border },
    );
    w.addCard(
        (x, y, cw) => renderTitleDetail(w.currentSlide, 'Competitive Landscape', analysis.strategic_positioning.competitive_landscape, x, y, cw),
        { borderColor: colors.border },
    );

    // Key Strategic Themes
    if (analysis.key_strategic_themes?.length > 0) {
        w.addSectionBlock('Key Strategic Themes', colors.amber.bg, colors.amber.text);
        renderCardPairs(w, analysis.key_strategic_themes, (t, x, y, cw) =>
            renderTitleDetail(w.currentSlide, t.theme, t.description, x, y, cw, {
                extraLine: `Evidence: ${t.evidence_from_document}`,
                extraColor: colors.amber.text,
            }),
            colors.border,
        );
    }

    // Stakeholder Insights
    if (analysis.stakeholder_insights?.length > 0) {
        w.addSectionBlock('Stakeholder Insights', colors.violet.bg, colors.violet.text);
        const rows: any[][] = [[
            { text: 'Stakeholder', options: { bold: true, color: colors.violet.text, fill: { color: colors.violet.bg } } },
            { text: 'Role / Interest', options: { bold: true, color: colors.violet.text, fill: { color: colors.violet.bg } } },
            { text: 'Influence', options: { bold: true, color: colors.violet.text, fill: { color: colors.violet.bg } } },
        ]];
        analysis.stakeholder_insights.forEach(si => {
            rows.push([{ text: s(si.stakeholder) }, { text: s(si.role_or_interest) }, { text: s(si.influence_level) }]);
        });
        w.addTable(rows, { colWidths: [CW * 0.3, CW * 0.5, CW * 0.2], borderColor: colors.border });
    }

    // Resources & Capabilities
    if (analysis.resources_and_capabilities?.length > 0) {
        w.addSectionBlock('Resources & Capabilities', colors.sky.bg, colors.sky.text);
        renderCardPairs(w, analysis.resources_and_capabilities, (r, x, y, cw) =>
            renderTitleDetail(w.currentSlide, r.resource, r.current_state, x, y, cw, {
                extraLine: `Strategic Relevance: ${r.strategic_relevance}`,
                extraColor: colors.sky.text,
            }),
            colors.border,
        );
    }

    // Identified Risks
    if (analysis.identified_risks?.length > 0) {
        w.addSectionBlock('Identified Risks', colors.rose.bg, colors.rose.text);
        const rRows: any[][] = [[
            { text: 'Risk', options: { bold: true, color: colors.rose.text, fill: { color: colors.rose.bg } } },
            { text: 'Severity', options: { bold: true, color: colors.rose.text, fill: { color: colors.rose.bg } } },
            { text: 'Context', options: { bold: true, color: colors.rose.text, fill: { color: colors.rose.bg } } },
        ]];
        analysis.identified_risks.forEach(r => {
            rRows.push([{ text: s(r.risk) }, { text: s(r.severity) }, { text: s(r.context) }]);
        });
        w.addTable(rRows, { colWidths: [CW * 0.3, CW * 0.15, CW * 0.55], borderColor: colors.border });
    }

    // ── PART 2 ──
    w.addSectionBlock('Part 2 — Analytical Assessment', colors.cyan.bg, colors.cyan.text);

    // Strategic Gaps
    if (analysis.strategic_gaps_and_observations?.length > 0) {
        w.addSectionBlock('Strategic Gaps & Observations', colors.amber.bg, colors.amber.text);
        w.addPills(analysis.strategic_gaps_and_observations, colors.amber.bg, colors.amber.text);
    }

    // Forward-Looking Assessment
    w.addSectionBlock('Forward-Looking Assessment', colors.emerald.bg, colors.emerald.text);
    if (analysis.forward_looking_assessment.opportunities?.length > 0) {
        w.addSubheading('Opportunities');
        w.addPills(analysis.forward_looking_assessment.opportunities, colors.emerald.bg, colors.emerald.text);
    }
    if (analysis.forward_looking_assessment.recommended_next_steps?.length > 0) {
        w.addSubheading('Recommended Next Steps');
        w.addPills(analysis.forward_looking_assessment.recommended_next_steps, colors.sky.bg, colors.sky.text);
    }
    if (analysis.forward_looking_assessment.potential_challenges?.length > 0) {
        w.addSubheading('Potential Challenges');
        w.addPills(analysis.forward_looking_assessment.potential_challenges, colors.rose.bg, colors.rose.text);
    }
    w.addSubheading('Overall Assessment');
    w.addText(analysis.forward_looking_assessment.overall_assessment, { color: colors.slate600 });

    // Additional Insights
    if (analysis.llm_inferred_additions?.length > 0) {
        w.addSectionBlock('Additional Insights', colors.muted.bg, colors.muted.text);
        renderCardPairs(w, analysis.llm_inferred_additions, (a, x, y, cw) =>
            renderTitleDetail(w.currentSlide, a.section_title, a.content, x, y, cw),
            colors.border,
        );
    }

    w.finalize();

    const safe = (title || 'strategic-analysis').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'strategic-analysis';
    const name = filename || `${safe} - Strategic Analysis.pptx`;
    pptx.writeFile({ fileName: name });
}
