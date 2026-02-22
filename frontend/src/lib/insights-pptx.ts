/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { InsightsLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, CW, FONT,
    s, estimateTextHeight, SlideWriter,
} from './pptx-slide-writer';

// ── Color palette (matches UI Tailwind colors, no # prefix for pptxgenjs) ────
const colors = {
    bannerBg: 'F97316',       // orange-500
    amber:   { bg: 'FEF3C7', text: 'B45309' },
    violet:  { bg: 'EDE9FE', text: '6D28D9' },
    emerald: { bg: 'D1FAE5', text: '047857' },
    rose:    { bg: 'FFE4E6', text: 'BE123C' },
    pink:    { bg: 'FCE7F3', text: 'BE185D' },
    sky:     { bg: 'E0F2FE', text: '0369A1' },
    muted:   { bg: 'F1F5F9', text: '475569' },
    slate600: '475569',
    slate800: '1F2937',
    roseHeaderBg: 'FFE4E6',
    roseBorder: 'FECDD3',
    emeraldBorder: 'A7F3D0',
    pinkBorder: 'FBCFE8',
    skyBorder: 'BAE6FD',
    border: 'E2E8F0',
};

// ── Card content helper ─────────────────────────────────────────────────────
/** Render a title + detail text block inside a card, return bottom Y */
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
            fontSize: 9, color: opts.extraColor ?? colors.pink.text, italic: true,
            valign: 'top',
        } as any);
        endY += 0.04 + exH;
    }
    return endY;
}

/** Render items as 2-column card pairs using addCardPair, with odd-item fallback to addCard */
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

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadInsightsPptx(insights: InsightsLLMOutput, filename?: string) {
    const title = insights?.document_summary?.title || 'Insights';
    const purpose = insights?.document_summary?.purpose || '';

    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'WIDE', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'WIDE';
    pptx.author = 'Knowledge Synthesis Platform';
    pptx.subject = 'Insights';
    pptx.title = s(title);

    const w = new SlideWriter(pptx);

    // ── Title Slide ──────────────────────────────────────────────────────────
    w.addBanner(
        title,
        'Synthesis of discussion points, strengths, gaps, innovations, and next steps.',
        colors.bannerBg,
    );

    // ── Document Summary (own slide) ─────────────────────────────────────────
    if (purpose || (insights.document_summary?.key_themes?.length > 0)) {
        w.addSectionBlock('Document Summary', colors.amber.bg, colors.amber.text);
        if (purpose) {
            w.addText(purpose, { color: colors.slate600 });
        }
        if (insights.document_summary?.key_themes?.length > 0) {
            w.addText('Key Themes', { bold: true });
            w.addPills(insights.document_summary.key_themes, colors.amber.bg, colors.amber.text);
        }
    }

    // ── Key Discussion Points (own slide, 2-col cards) ───────────────────────
    if (insights.key_discussion_points?.length > 0) {
        w.addSectionBlock('Key Discussion Points', colors.violet.bg, colors.violet.text);
        renderCardPairs(w, insights.key_discussion_points, (p, x, y, cw) =>
            renderTitleDetail(w.currentSlide, p.topic, p.details, x, y, cw),
            colors.border,
        );
    }

    // ── Strengths (own slide, 2-col cards) ───────────────────────────────────
    if (insights.strengths?.length > 0) {
        w.addSectionBlock('Strengths', colors.emerald.bg, colors.emerald.text);
        renderCardPairs(w, insights.strengths, (st, x, y, cw) =>
            renderTitleDetail(w.currentSlide, st.aspect, st.evidence_or_example, x, y, cw),
            colors.emeraldBorder,
        );
    }

    // ── Gaps & Improvements (own slide, full-width table) ────────────────────
    if (insights.improvement_or_missing_areas?.length > 0) {
        w.addSectionBlock('Gaps & Improvements', colors.rose.bg, colors.rose.text);
        const gapRows: any[][] = [[
            { text: 'Gap', options: { bold: true, color: colors.rose.text, fill: { color: colors.roseHeaderBg } } },
            { text: 'Suggested Improvement', options: { bold: true, color: colors.rose.text, fill: { color: colors.roseHeaderBg } } },
        ]];
        insights.improvement_or_missing_areas.forEach((g) => {
            gapRows.push([{ text: s(g.gap) }, { text: s(g.suggested_improvement) }]);
        });
        w.addTable(gapRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.roseBorder });
    }

    // ── Innovation Aspects (own slide, 2-col cards) ──────────────────────────
    if (insights.innovation_aspects?.length > 0) {
        w.addSectionBlock('Innovation Aspects', colors.pink.bg, colors.pink.text);
        renderCardPairs(w, insights.innovation_aspects, (inn, x, y, cw) =>
            renderTitleDetail(w.currentSlide, inn.innovation_title, inn.description, x, y, cw, {
                extraLine: `Potential Impact: ${inn.potential_impact}`,
                extraColor: colors.pink.text,
            }),
            colors.pinkBorder,
        );
    }

    // ── Future Considerations (own slide, 2-col cards) ───────────────────────
    if (insights.future_considerations?.length > 0) {
        w.addSectionBlock('Future Considerations', colors.sky.bg, colors.sky.text);
        renderCardPairs(w, insights.future_considerations, (f, x, y, cw) =>
            renderTitleDetail(w.currentSlide, f.focus_area, f.recommendation, x, y, cw),
            colors.skyBorder,
        );
    }

    // ── Pseudocode / Technical Outline (own slide) ───────────────────────────
    if (insights.pseudocode_or_technical_outline?.length > 0) {
        w.addSectionBlock('Pseudocode / Technical Outline', colors.violet.bg, colors.violet.text);
        for (const p of insights.pseudocode_or_technical_outline) {
            if (p.section) w.addSubheading(p.section);
            if (p.pseudocode) w.addCodeBlock(p.pseudocode);
        }
    }

    // ── Additional Insights (own slide, 2-col cards) ─────────────────────────
    if (insights.llm_inferred_additions?.length > 0) {
        w.addSectionBlock('Additional Insights', colors.muted.bg, colors.muted.text);
        renderCardPairs(w, insights.llm_inferred_additions, (a, x, y, cw) =>
            renderTitleDetail(w.currentSlide, a.section_title, a.content, x, y, cw),
            colors.border,
        );
    }

    w.finalize();

    const safe = (title || 'insights').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'insights';
    const name = filename || `${safe} - Insights.pptx`;
    pptx.writeFile({ fileName: name });
}
