/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { TechnicalRoadmapLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, ML, CW, FONT,
    s, makeBullets, estimateTextHeight, estimateBulletsHeight,
    SlideWriter,
} from './pptx-slide-writer';

// ── Color palette (no # prefix for pptxgenjs) ───────────────────────────────
const colors = {
    bannerBg: '0284C7',
    sky:     { bg: 'E0F2FE', text: '0369A1' },
    emerald: { bg: 'D1FAE5', text: '047857' },
    violet:  { bg: 'EDE9FE', text: '6D28D9' },
    fuchsia: { bg: 'FAE8FF', text: 'A21CAF' },
    rose:    { bg: 'FFE4E6', text: 'BE123C' },
    muted:   { bg: 'F1F5F9', text: '475569' },
    slate600: '475569',
    slate800: '1F2937',
    white: 'FFFFFF',
    roseHeaderBg: 'FFE4E6',
    roseBorder: 'FECDD3',
    violetBorder: 'DDD6FE',
    emeraldBorder: 'A7F3D0',
    skyBorder: 'BAE6FD',
    border: 'E2E8F0',
};

// ── Phase card helper ──────────────────────────────────────────────────────────
function writePhaseCard(
    w: SlideWriter,
    label: string,
    phase: TechnicalRoadmapLLMOutput['phased_roadmap']['short_term'],
): void {
    w.addCard(
        (x, y, cardW) => {
            const slide = w.currentSlide;
            const labelH = estimateTextHeight(label, FONT.phaseTitle, cardW * 0.6);

            slide.addText(s(label), {
                x, y, w: cardW * 0.6, h: labelH,
                fontSize: FONT.phaseTitle, bold: true, color: colors.fuchsia.text,
            } as any);
            slide.addText(s(phase.time_frame), {
                x: x + cardW * 0.6, y, w: cardW * 0.4, h: labelH,
                fontSize: FONT.body, color: colors.slate600, align: 'right',
            } as any);
            let dy = y + labelH + 0.04;

            slide.addShape('line' as any, {
                x, y: dy, w: cardW, h: 0,
                line: { color: colors.violetBorder, width: 0.5 },
            } as any);
            dy += 0.06;

            // Focus Areas
            slide.addText('Focus Areas', {
                x, y: dy, w: cardW, h: 0.22,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            dy += 0.24;
            const focH = estimateBulletsHeight(phase.focus_areas, 10, cardW);
            slide.addText(makeBullets(phase.focus_areas, { fontSize: 10 }) as any, {
                x, y: dy, w: cardW, h: focH, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            dy += focH + 0.04;

            // Initiatives
            const initiatives = phase.key_initiatives.map(
                (it) => `${it.initiative}: ${it.objective} (Outcome: ${it.expected_outcome})`,
            );
            slide.addText('Initiatives', {
                x, y: dy, w: cardW, h: 0.22,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            dy += 0.24;
            const iniH = estimateBulletsHeight(initiatives, 10, cardW);
            slide.addText(makeBullets(initiatives, { fontSize: 10 }) as any, {
                x, y: dy, w: cardW, h: iniH, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            dy += iniH + 0.04;

            // Dependencies
            slide.addText('Dependencies', {
                x, y: dy, w: cardW, h: 0.22,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            dy += 0.24;
            const depH = estimateBulletsHeight(phase.dependencies, 10, cardW);
            slide.addText(makeBullets(phase.dependencies, { fontSize: 10 }) as any, {
                x, y: dy, w: cardW, h: depH, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + depH;
        },
        { borderColor: colors.violetBorder },
    );
}

// ── Reusable card-pair renderer ─────────────────────────────────────────────
function renderTitleDetailPairs<T>(
    w: SlideWriter,
    items: T[],
    getTitle: (item: T) => string,
    getDetail: (item: T) => string,
    titleColor: string,
    borderColor: string,
    opts?: { extraLine?: (item: T) => string; extraColor?: string },
): void {
    for (let i = 0; i < items.length; i += 2) {
        const renderItem = (item: T) => (x: number, y: number, cw: number) => {
            const tH = estimateTextHeight(getTitle(item), FONT.subheading, cw);
            w.currentSlide.addText(s(getTitle(item)), {
                x, y, w: cw, h: tH,
                fontSize: FONT.subheading, bold: true, color: titleColor, valign: 'top',
            } as any);
            const dH = estimateTextHeight(getDetail(item), FONT.body, cw);
            w.currentSlide.addText(s(getDetail(item)), {
                x, y: y + tH + 0.04, w: cw, h: dH,
                fontSize: FONT.body, color: colors.slate600, valign: 'top',
            } as any);
            let endY = y + tH + 0.04 + dH;
            if (opts?.extraLine) {
                const extra = opts.extraLine(item);
                if (extra) {
                    const exH = 0.2;
                    w.currentSlide.addText(s(extra), {
                        x, y: endY + 0.04, w: cw, h: exH,
                        fontSize: 9, color: opts.extraColor ?? colors.violet.text, italic: true,
                        valign: 'top',
                    } as any);
                    endY += 0.04 + exH;
                }
            }
            return endY;
        };

        if (i + 1 < items.length) {
            w.addCardPair(renderItem(items[i]), renderItem(items[i + 1]), { borderColor });
        } else {
            w.addCard(renderItem(items[i]), { borderColor });
        }
    }
}

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadTechnicalRoadmapPptx(roadmap: TechnicalRoadmapLLMOutput, filename?: string) {
    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'WIDE', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'WIDE';
    pptx.author = 'Knowledge Synthesis Platform';
    pptx.subject = 'Technical Roadmap';
    pptx.title = s(roadmap.roadmap_title);

    const w = new SlideWriter(pptx);

    // ── Title Slide ──────────────────────────────────────────────────────────
    w.addBanner(
        roadmap.roadmap_title,
        'Technical roadmap with vision, domains, phased plan, enablers, and risks.',
        colors.bannerBg,
    );

    // ── Overall Vision ───────────────────────────────────────────────────────
    w.addSectionBlock('Overall Vision', colors.sky.bg, colors.sky.text);
    w.addText(roadmap.overall_vision.goal, { color: colors.slate600 });
    if (roadmap.overall_vision.success_metrics?.length > 0) {
        w.addText('Success Metrics', { bold: true });
        w.addPills(roadmap.overall_vision.success_metrics, colors.emerald.bg, colors.emerald.text);
    }

    // ── Current State Analysis ───────────────────────────────────────────────
    w.addSectionBlock('Current State Analysis', colors.sky.bg, colors.sky.text);
    w.addText(roadmap.current_state_analysis.summary, { color: colors.slate600 });

    w.addTwoColumns(
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hdrH = estimateTextHeight('Key Challenges', FONT.subheading, colW);
            slide.addText('Key Challenges', {
                x, y, w: colW, h: hdrH,
                fontSize: FONT.subheading, bold: true, color: colors.rose.text,
            } as any);
            let dy = y + hdrH + 0.04;
            const bh = estimateBulletsHeight(roadmap.current_state_analysis.key_challenges, 10, colW);
            slide.addText(makeBullets(roadmap.current_state_analysis.key_challenges, { fontSize: 10 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hdrH = estimateTextHeight('Existing Capabilities', FONT.subheading, colW);
            slide.addText('Existing Capabilities', {
                x, y, w: colW, h: hdrH,
                fontSize: FONT.subheading, bold: true, color: colors.emerald.text,
            } as any);
            let dy = y + hdrH + 0.04;
            const bh = estimateBulletsHeight(roadmap.current_state_analysis.existing_capabilities, 10, colW);
            slide.addText(makeBullets(roadmap.current_state_analysis.existing_capabilities, { fontSize: 10 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
    );

    // ── Technology Domains (2-col cards) ──────────────────────────────────────
    w.addSectionBlock('Technology Domains', colors.emerald.bg, colors.emerald.text);
    renderTitleDetailPairs(
        w, roadmap.technology_domains,
        (d) => d.domain_name, (d) => d.description,
        colors.emerald.text, colors.emeraldBorder,
    );

    // ── Phased Technical Roadmap ─────────────────────────────────────────────
    w.addSectionBlock('Phased Technical Roadmap', colors.fuchsia.bg, colors.fuchsia.text);
    writePhaseCard(w, 'Short Term', roadmap.phased_roadmap.short_term);
    writePhaseCard(w, 'Mid Term', roadmap.phased_roadmap.mid_term);
    writePhaseCard(w, 'Long Term', roadmap.phased_roadmap.long_term);

    // ── Key Technology Enablers ──────────────────────────────────────────────
    w.addSectionBlock('Key Technology Enablers', colors.violet.bg, colors.violet.text);
    const enBullets = roadmap.key_technology_enablers.map((e) => `${e.enabler}: ${e.impact}`);
    w.addBullets(enBullets);

    // ── Risks & Mitigation ───────────────────────────────────────────────────
    w.addSectionBlock('Risks & Mitigation', colors.rose.bg, colors.rose.text);
    const riskRows: any[][] = [[
        { text: 'Risk', options: { bold: true, color: colors.rose.text, fill: { color: colors.roseHeaderBg } } },
        { text: 'Mitigation', options: { bold: true, color: colors.rose.text, fill: { color: colors.roseHeaderBg } } },
    ]];
    roadmap.risks_and_mitigations.forEach((r) => {
        riskRows.push([{ text: s(r.risk) }, { text: s(r.mitigation) }]);
    });
    w.addTable(riskRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.roseBorder });

    // ── Innovation Opportunities (2-col cards) ───────────────────────────────
    if (roadmap.innovation_opportunities?.length > 0) {
        w.addSectionBlock('Innovation Opportunities', colors.sky.bg, colors.sky.text);
        renderTitleDetailPairs(
            w, roadmap.innovation_opportunities,
            (iop) => iop.idea, (iop) => iop.description,
            colors.sky.text, colors.skyBorder,
            { extraLine: (iop) => `Maturity: ${iop.maturity_level}`, extraColor: colors.violet.text },
        );
    }

    // ── Tabular Summary ──────────────────────────────────────────────────────
    if (roadmap.tabular_summary?.length > 0) {
        w.addSectionBlock('Tabular Summary', colors.violet.bg, colors.violet.text);
        const sumRows: any[][] = [[
            { text: 'Time Frame', options: { bold: true, color: colors.violet.text, fill: { color: colors.violet.bg } } },
            { text: 'Key Points', options: { bold: true, color: colors.violet.text, fill: { color: colors.violet.bg } } },
        ]];
        roadmap.tabular_summary.forEach((r) => {
            sumRows.push([
                { text: s(r.time_frame) },
                { text: (r.key_points || []).map((p) => s(p)).join('\n') },
            ]);
        });
        w.addTable(sumRows, { colWidths: [CW * 0.25, CW * 0.75], borderColor: colors.violetBorder });
    }

    // ── Additional Insights (2-col cards) ────────────────────────────────────
    if (roadmap.llm_inferred_additions?.length > 0) {
        w.addSectionBlock('Additional Insights', colors.muted.bg, colors.muted.text);
        renderTitleDetailPairs(
            w, roadmap.llm_inferred_additions,
            (a) => a.section_title, (a) => a.content,
            colors.slate800, colors.border,
        );
    }

    w.finalize();

    const safe = (roadmap.roadmap_title || 'technical-roadmap').replace(/[^a-z0-9\-\s]/gi, '').trim();
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
