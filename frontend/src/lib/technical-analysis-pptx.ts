/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { TechnicalAnalysisLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, CW, FONT,
    s, estimateTextHeight, SlideWriter,
} from './pptx-slide-writer';

// ── Color palette (no # prefix for pptxgenjs) ─────────────────────────────
const colors = {
    bannerBg: '6366F1',       // indigo-500
    indigo:  { bg: 'E0E7FF', text: '4338CA' },
    violet:  { bg: 'EDE9FE', text: '6D28D9' },
    emerald: { bg: 'D1FAE5', text: '047857' },
    amber:   { bg: 'FEF3C7', text: 'B45309' },
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
export function downloadTechnicalAnalysisPptx(analysis: TechnicalAnalysisLLMOutput, filename?: string) {
    const title = analysis?.analysis_title || 'Technical Analysis';

    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'WIDE', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'WIDE';
    pptx.author = 'Knowledge Synthesis Platform';
    pptx.subject = 'Technical Analysis';
    pptx.title = s(title);

    const w = new SlideWriter(pptx);

    // ── Title Slide ──
    w.addBanner(title, 'Technical content extraction and analytical assessment.', colors.bannerBg);

    // ── Executive Overview ──
    w.addSectionBlock('Executive Overview', colors.indigo.bg, colors.indigo.text);
    w.addText(analysis.executive_overview, { color: colors.slate600 });

    // ── PART 1 ──
    w.addSectionBlock('Part 1 — Document Content Extraction', colors.indigo.bg, colors.indigo.text);

    // Technical Scope
    w.addSectionBlock('Technical Scope', colors.violet.bg, colors.violet.text);
    if (analysis.technical_scope.domains_covered?.length > 0) {
        w.addSubheading('Domains Covered');
        w.addPills(analysis.technical_scope.domains_covered, colors.violet.bg, colors.violet.text);
    }
    if (analysis.technical_scope.technology_stack?.length > 0) {
        w.addSubheading('Technology Stack');
        w.addPills(analysis.technical_scope.technology_stack, colors.indigo.bg, colors.indigo.text);
    }
    w.addSubheading('Architecture Overview');
    w.addText(analysis.technical_scope.architecture_overview, { color: colors.slate600 });

    // Technical Decisions
    if (analysis.technical_decisions?.length > 0) {
        w.addSectionBlock('Technical Decisions', colors.amber.bg, colors.amber.text);
        renderCardPairs(w, analysis.technical_decisions, (d, x, y, cw) =>
            renderTitleDetail(w.currentSlide, d.decision, d.rationale, x, y, cw, {
                extraLine: `Implications: ${d.implications}`,
                extraColor: colors.amber.text,
            }),
            colors.border,
        );
    }

    // Technical Strengths
    if (analysis.technical_strengths?.length > 0) {
        w.addSectionBlock('Technical Strengths', colors.emerald.bg, colors.emerald.text);
        renderCardPairs(w, analysis.technical_strengths, (st, x, y, cw) =>
            renderTitleDetail(w.currentSlide, st.aspect, st.evidence, x, y, cw),
            colors.border,
        );
    }

    // Technical Concerns
    if (analysis.technical_concerns?.length > 0) {
        w.addSectionBlock('Technical Concerns', colors.rose.bg, colors.rose.text);
        const cRows: any[][] = [[
            { text: 'Concern', options: { bold: true, color: colors.rose.text, fill: { color: colors.rose.bg } } },
            { text: 'Impact', options: { bold: true, color: colors.rose.text, fill: { color: colors.rose.bg } } },
            { text: 'Evidence', options: { bold: true, color: colors.rose.text, fill: { color: colors.rose.bg } } },
        ]];
        analysis.technical_concerns.forEach(c => {
            cRows.push([{ text: s(c.concern) }, { text: s(c.impact) }, { text: s(c.evidence) }]);
        });
        w.addTable(cRows, { colWidths: [CW * 0.3, CW * 0.3, CW * 0.4], borderColor: colors.border });
    }

    // Innovation Elements
    if (analysis.innovation_elements?.length > 0) {
        w.addSectionBlock('Innovation Elements', colors.violet.bg, colors.violet.text);
        renderCardPairs(w, analysis.innovation_elements, (inn, x, y, cw) =>
            renderTitleDetail(w.currentSlide, `${inn.element} [${inn.maturity}]`, inn.description, x, y, cw),
            colors.border,
        );
    }

    // Technical Aspirations
    w.addSectionBlock('Technical Aspirations', colors.sky.bg, colors.sky.text);
    if (analysis.technical_aspirations.stated_goals?.length > 0) {
        w.addSubheading('Stated Goals');
        w.addPills(analysis.technical_aspirations.stated_goals, colors.sky.bg, colors.sky.text);
    }
    w.addSubheading('Implied Direction');
    w.addText(analysis.technical_aspirations.implied_direction, { color: colors.slate600 });
    w.addSubheading('Alignment Assessment');
    w.addText(analysis.technical_aspirations.alignment_assessment, { color: colors.slate600 });

    // Implementation Readiness
    w.addSectionBlock('Implementation Readiness', colors.indigo.bg, colors.indigo.text);
    if (analysis.implementation_readiness.ready_components?.length > 0) {
        w.addSubheading('Ready Components');
        w.addPills(analysis.implementation_readiness.ready_components, colors.emerald.bg, colors.emerald.text);
    }
    if (analysis.implementation_readiness.gaps_to_address?.length > 0) {
        w.addSubheading('Gaps to Address');
        w.addPills(analysis.implementation_readiness.gaps_to_address, colors.amber.bg, colors.amber.text);
    }
    if (analysis.implementation_readiness.dependencies?.length > 0) {
        w.addSubheading('Dependencies');
        w.addPills(analysis.implementation_readiness.dependencies, colors.sky.bg, colors.sky.text);
    }

    // ── PART 2 ──
    w.addSectionBlock('Part 2 — Analytical Assessment', colors.violet.bg, colors.violet.text);

    w.addSectionBlock('Forward-Looking Assessment', colors.emerald.bg, colors.emerald.text);
    w.addSubheading('Scalability Outlook');
    w.addText(analysis.forward_looking_assessment.scalability_outlook, { color: colors.slate600 });
    w.addSubheading('Technology Evolution');
    w.addText(analysis.forward_looking_assessment.technology_evolution, { color: colors.slate600 });
    if (analysis.forward_looking_assessment.recommended_focus_areas?.length > 0) {
        w.addSubheading('Recommended Focus Areas');
        w.addPills(analysis.forward_looking_assessment.recommended_focus_areas, colors.emerald.bg, colors.emerald.text);
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

    const safe = (title || 'technical-analysis').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'technical-analysis';
    const name = filename || `${safe} - Technical Analysis.pptx`;
    pptx.writeFile({ fileName: name });
}
