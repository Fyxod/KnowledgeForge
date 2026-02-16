/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { InsightsLLMOutput } from './api';

// ── Theme ──────────────────────────────────────────────────────────────────────
const colors = {
    primary: '6d56f1',
    accent1: 'F59E0B',
    accent2: '5341c8',
    success: '10B981',
    danger: 'EF4444',
    slate800: '1F2937',
    slate600: '475569',
    white: 'FFFFFF',
    border: 'c4bcf0',
};

const M = 0.5;

function s(text: string | undefined | null): string {
    if (!text) return '';
    return String(text)
        .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/×/g, 'x')
        .replace(/±/g, '+/-').replace(/[–—]/g, '-').replace(/[""]/g, '"')
        .replace(/\u202F/g, ' ').replace(/'/g, "'").replace(/‑/g, '-');
}

function bullets(items: string[], opts?: { fontSize?: number; color?: string }): any[] {
    return items.map((t) => ({
        text: s(t),
        options: { bullet: { type: 'bullet' as const }, fontSize: opts?.fontSize ?? 13, color: opts?.color ?? colors.slate800, breakLine: true },
    }));
}

function headerBar(slide: any, pptx: PptxGenJS, title: string, color: string = colors.primary) {
    slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 10, h: 0.9, fill: { color } });
    slide.addText(s(title), { x: M, y: 0.15, w: `${10 - M * 2}`, h: 0.6, fontSize: 22, bold: true, color: colors.white });
}

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadInsightsPptx(insights: InsightsLLMOutput, filename?: string) {
    const title = insights?.document_summary?.title || 'Insights';
    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'NARROW_10_33', width: 10.33, height: 7.5 }); // 3" narrower than default wide
    pptx.layout = 'NARROW_10_33';
    pptx.author = 'NotebookLM';
    pptx.subject = 'Insights';
    pptx.title = s(title);

    // ── Title Slide ────────────────────────────────────────────────────────────
    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: colors.primary };
    titleSlide.addText(s(title), {
        x: M, y: '28%', w: `${10 - M * 2}`, h: 1.2,
        fontSize: 32, bold: true, color: colors.white, align: 'center',
    } as any);
    if (insights.document_summary?.purpose) {
        titleSlide.addText(s(insights.document_summary.purpose), {
            x: M, y: '50%', w: `${10 - M * 2}`,
            fontSize: 14, color: colors.border, align: 'center',
        } as any);
    }
    if (insights.document_summary?.key_themes?.length > 0) {
        titleSlide.addText('Key Themes', {
            x: M, y: '62%', w: `${10 - M * 2}`,
            fontSize: 12, bold: true, color: colors.white, align: 'center',
        } as any);
        titleSlide.addText(insights.document_summary.key_themes.map((t) => s(t)).join('  •  '), {
            x: M, y: '68%', w: `${10 - M * 2}`,
            fontSize: 11, color: colors.border, align: 'center',
        } as any);
    }

    // ── Key Discussion Points ──────────────────────────────────────────────────
    if (insights.key_discussion_points?.length > 0) {
        const dpSlide = pptx.addSlide();
        headerBar(dpSlide, pptx, 'Key Discussion Points', colors.primary);
        const dpBullets = insights.key_discussion_points.map((p) => `${p.topic}: ${p.details}`);
        dpSlide.addText(bullets(dpBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Strengths ──────────────────────────────────────────────────────────────
    if (insights.strengths?.length > 0) {
        const strSlide = pptx.addSlide();
        headerBar(strSlide, pptx, 'Strengths', colors.success);
        const strBullets = insights.strengths.map((st) => `${st.aspect}: ${st.evidence_or_example}`);
        strSlide.addText(bullets(strBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Gaps & Improvements ────────────────────────────────────────────────────
    if (insights.improvement_or_missing_areas?.length > 0) {
        const gapSlide = pptx.addSlide();
        headerBar(gapSlide, pptx, 'Gaps & Improvements', colors.danger);
        const gapRows: any[][] = [[
            { text: 'Gap', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
            { text: 'Suggested Improvement', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
        ]];
        insights.improvement_or_missing_areas.forEach((g) => {
            gapRows.push([{ text: s(g.gap) }, { text: s(g.suggested_improvement) }]);
        });
        gapSlide.addTable(gapRows, {
            x: M, y: 1.1, w: `${10 - M * 2}`,
            fontSize: 12, border: { pt: 0.5, color: colors.border },
            colW: [4.5, 4.5],
            autoPage: true,
        } as any);
    }

    // ── Innovation Aspects ─────────────────────────────────────────────────────
    if (insights.innovation_aspects?.length > 0) {
        const innSlide = pptx.addSlide();
        headerBar(innSlide, pptx, 'Innovation Aspects', colors.accent1);
        const innBullets = insights.innovation_aspects.map(
            (i) => `${i.innovation_title}: ${i.description} (Impact: ${i.potential_impact})`
        );
        innSlide.addText(bullets(innBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Future Considerations ──────────────────────────────────────────────────
    if (insights.future_considerations?.length > 0) {
        const futSlide = pptx.addSlide();
        headerBar(futSlide, pptx, 'Future Considerations', colors.accent2);
        const futBullets = insights.future_considerations.map(
            (f) => `${f.focus_area}: ${f.recommendation}`
        );
        futSlide.addText(bullets(futBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Pseudocode / Technical Outline ─────────────────────────────────────────
    if (insights.pseudocode_or_technical_outline && insights.pseudocode_or_technical_outline.length > 0) {
        const codeSlide = pptx.addSlide();
        headerBar(codeSlide, pptx, 'Pseudocode / Technical Outline', colors.primary);
        const codeBullets = insights.pseudocode_or_technical_outline
            .filter((p) => p.section || p.pseudocode)
            .map((p) => `${p.section || ''}: ${p.pseudocode || ''}`);
        if (codeBullets.length > 0) {
            codeSlide.addText(bullets(codeBullets, { fontSize: 11 }) as any, {
                x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.15,
            } as any);
        }
    }

    // ── LLM Inferred Additions ─────────────────────────────────────────────────
    if (insights.llm_inferred_additions && insights.llm_inferred_additions.length > 0) {
        const addSlide = pptx.addSlide();
        headerBar(addSlide, pptx, 'Additional Insights', colors.slate600);
        const addBullets = insights.llm_inferred_additions.map((a) => `${a.section_title}: ${a.content}`);
        addSlide.addText(bullets(addBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Download ───────────────────────────────────────────────────────────────
    const safe = (title || 'insights').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'insights';
    const name = filename || `${safe} - Insights.pptx`;
    pptx.writeFile({ fileName: name });
}
