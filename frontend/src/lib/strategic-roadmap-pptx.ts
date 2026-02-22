/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { StrategicRoadmapLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, ML, CW, FONT,
    s, makeBullets, estimateTextHeight, estimateBulletsHeight,
    SlideWriter,
} from './pptx-slide-writer';

// ── Color palette (no # prefix for pptxgenjs) ───────────────────────────────
const colors = {
    bannerBg: '7C3AED',
    emerald: { bg: 'D1FAE5', text: '047857' },
    sky:     { bg: 'E0F2FE', text: '0369A1' },
    violet:  { bg: 'EDE9FE', text: '6D28D9' },
    fuchsia: { bg: 'FAE8FF', text: 'A21CAF' },
    rose:    { bg: 'FFE4E6', text: 'BE123C' },
    muted:   { bg: 'F1F5F9', text: '475569' },
    // SWOT header fills
    swotStrengthsHdr: '10B981',
    swotWeaknessesHdr: 'F59E0B',
    swotOpportunitiesHdr: '0284C7',
    swotThreatsHdr: 'EF4444',
    slate600: '475569',
    slate800: '1F2937',
    white: 'FFFFFF',
    roseHeaderBg: 'FFE4E6',
    roseBorder: 'FECDD3',
    violetBorder: 'DDD6FE',
    border: 'E2E8F0',
};

// ── Phase card helper ──────────────────────────────────────────────────────────
function writePhaseCard(w: SlideWriter, phase: StrategicRoadmapLLMOutput['phased_roadmap'][0]): void {
    w.addCard(
        (x, y, cardW) => {
            const slide = w.currentSlide;
            const labelH = estimateTextHeight(phase.phase, FONT.phaseTitle, cardW * 0.6);

            // Phase name + time frame
            slide.addText(s(phase.phase), {
                x, y, w: cardW * 0.6, h: labelH,
                fontSize: FONT.phaseTitle, bold: true, color: colors.fuchsia.text,
            } as any);
            slide.addText(s(phase.time_frame), {
                x: x + cardW * 0.6, y, w: cardW * 0.4, h: labelH,
                fontSize: FONT.body, color: colors.slate600, align: 'right',
            } as any);
            let dy = y + labelH + 0.04;

            // Separator
            slide.addShape('line' as any, {
                x, y: dy, w: cardW, h: 0,
                line: { color: colors.violetBorder, width: 0.5 },
            } as any);
            dy += 0.06;

            // Objectives
            slide.addText('Objectives', {
                x, y: dy, w: cardW, h: 0.22,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            dy += 0.24;
            const objH = estimateBulletsHeight(phase.key_objectives, 10, cardW);
            slide.addText(makeBullets(phase.key_objectives, { fontSize: 10 }) as any, {
                x, y: dy, w: cardW, h: objH, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            dy += objH + 0.04;

            // Initiatives
            slide.addText('Initiatives', {
                x, y: dy, w: cardW, h: 0.22,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            dy += 0.24;
            const iniH = estimateBulletsHeight(phase.key_initiatives, 10, cardW);
            slide.addText(makeBullets(phase.key_initiatives, { fontSize: 10 }) as any, {
                x, y: dy, w: cardW, h: iniH, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            dy += iniH + 0.04;

            // Expected Outcomes
            slide.addText('Expected Outcomes', {
                x, y: dy, w: cardW, h: 0.22,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            dy += 0.24;
            const outH = estimateBulletsHeight(phase.expected_outcomes, 10, cardW);
            slide.addText(makeBullets(phase.expected_outcomes, { fontSize: 10 }) as any, {
                x, y: dy, w: cardW, h: outH, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + outH;
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
            return y + tH + 0.04 + dH;
        };

        if (i + 1 < items.length) {
            w.addCardPair(renderItem(items[i]), renderItem(items[i + 1]), { borderColor });
        } else {
            w.addCard(renderItem(items[i]), { borderColor });
        }
    }
}

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadStrategicRoadmapPptx(roadmap: StrategicRoadmapLLMOutput, filename?: string) {
    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'WIDE', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'WIDE';
    pptx.author = 'Knowledge Synthesis Platform';
    pptx.subject = 'Strategic Roadmap';
    pptx.title = s(roadmap.roadmap_title);

    const w = new SlideWriter(pptx);

    // ── Title Slide ──────────────────────────────────────────────────────────
    w.addBanner(
        roadmap.roadmap_title,
        'Strategic, phased plan with goals, enablers, risks, and measurable milestones.',
        colors.bannerBg,
    );

    // ── Vision & End Goal ────────────────────────────────────────────────────
    w.addSectionBlock('Vision & End Goal', colors.emerald.bg, colors.emerald.text);
    w.addText(roadmap.vision_and_end_goal.description, { color: colors.slate600 });
    if (roadmap.vision_and_end_goal.success_criteria?.length > 0) {
        w.addText('Success Criteria', { bold: true });
        w.addPills(roadmap.vision_and_end_goal.success_criteria, colors.emerald.bg, colors.emerald.text);
    }

    // ── Current Baseline + SWOT ──────────────────────────────────────────────
    w.addSectionBlock('Current Baseline', colors.sky.bg, colors.sky.text);
    w.addText(roadmap.current_baseline.summary, { color: colors.slate600 });

    const swot = roadmap.current_baseline.swot;
    const swotRows: any[][] = [
        [
            { text: 'Strengths', options: { bold: true, color: colors.white, fill: { color: colors.swotStrengthsHdr }, fontSize: FONT.swotTitle } },
            { text: 'Weaknesses', options: { bold: true, color: colors.white, fill: { color: colors.swotWeaknessesHdr }, fontSize: FONT.swotTitle } },
        ],
        [
            { text: swot.strengths.map((x) => `\u2022 ${s(x)}`).join('\n'), options: { fontSize: 10 } },
            { text: swot.weaknesses.map((x) => `\u2022 ${s(x)}`).join('\n'), options: { fontSize: 10 } },
        ],
        [
            { text: 'Opportunities', options: { bold: true, color: colors.white, fill: { color: colors.swotOpportunitiesHdr }, fontSize: FONT.swotTitle } },
            { text: 'Threats', options: { bold: true, color: colors.white, fill: { color: colors.swotThreatsHdr }, fontSize: FONT.swotTitle } },
        ],
        [
            { text: swot.opportunities.map((x) => `\u2022 ${s(x)}`).join('\n'), options: { fontSize: 10 } },
            { text: swot.threats.map((x) => `\u2022 ${s(x)}`).join('\n'), options: { fontSize: 10 } },
        ],
    ];
    w.addTable(swotRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.border });

    // ── Strategic Pillars (2-col cards) ──────────────────────────────────────
    w.addSectionBlock('Strategic Pillars', colors.violet.bg, colors.violet.text);
    renderTitleDetailPairs(
        w, roadmap.strategic_pillars,
        (p) => p.pillar_name, (p) => p.description,
        colors.violet.text, colors.violetBorder,
    );

    // ── Phased Strategic Roadmap ─────────────────────────────────────────────
    w.addSectionBlock('Phased Strategic Roadmap', colors.fuchsia.bg, colors.fuchsia.text);
    for (const phase of roadmap.phased_roadmap) {
        writePhaseCard(w, phase);
    }

    // ── Enablers & Dependencies ──────────────────────────────────────────────
    w.addSectionBlock('Enablers & Dependencies', colors.sky.bg, colors.sky.text);
    w.addTwoColumns(
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hh = estimateTextHeight('Technologies', FONT.subheading, colW);
            slide.addText('Technologies', {
                x, y, w: colW, h: hh,
                fontSize: FONT.subheading, bold: true, color: colors.sky.text,
            } as any);
            let dy = y + hh + 0.04;
            const bh = estimateBulletsHeight(roadmap.enablers_and_dependencies.technologies, 10, colW);
            slide.addText(makeBullets(roadmap.enablers_and_dependencies.technologies, { fontSize: 10 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hh = estimateTextHeight('Skills & Resources', FONT.subheading, colW);
            slide.addText('Skills & Resources', {
                x, y, w: colW, h: hh,
                fontSize: FONT.subheading, bold: true, color: colors.sky.text,
            } as any);
            let dy = y + hh + 0.04;
            const bh = estimateBulletsHeight(roadmap.enablers_and_dependencies.skills_and_resources, 10, colW);
            slide.addText(makeBullets(roadmap.enablers_and_dependencies.skills_and_resources, { fontSize: 10 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
    );
    w.addSubheading('Stakeholders', { color: colors.sky.text });
    w.addBullets(roadmap.enablers_and_dependencies.stakeholders, { fontSize: 10 });

    // ── Risks & Mitigation ───────────────────────────────────────────────────
    w.addSectionBlock('Risks & Mitigation', colors.rose.bg, colors.rose.text);
    const riskRows: any[][] = [[
        { text: 'Risk', options: { bold: true, color: colors.rose.text, fill: { color: colors.roseHeaderBg } } },
        { text: 'Mitigation', options: { bold: true, color: colors.rose.text, fill: { color: colors.roseHeaderBg } } },
    ]];
    roadmap.risks_and_mitigation.forEach((r) => {
        riskRows.push([{ text: s(r.risk) }, { text: s(r.mitigation_strategy) }]);
    });
    w.addTable(riskRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.roseBorder });

    // ── Key Metrics & Milestones (2-col cards) ───────────────────────────────
    w.addSectionBlock('Key Metrics & Milestones', colors.violet.bg, colors.violet.text);
    for (let i = 0; i < roadmap.key_metrics_and_milestones.length; i += 2) {
        const renderMetric = (m: typeof roadmap.key_metrics_and_milestones[0]) =>
            (x: number, y: number, cw: number) => {
                const hdr = estimateTextHeight(m.year_or_phase, FONT.subheading, cw);
                w.currentSlide.addText(s(m.year_or_phase), {
                    x, y, w: cw, h: hdr,
                    fontSize: FONT.subheading, bold: true, color: colors.violet.text, valign: 'top',
                } as any);
                const bh = estimateBulletsHeight(m.metrics, 10, cw);
                w.currentSlide.addText(makeBullets(m.metrics, { fontSize: 10 }) as any, {
                    x, y: y + hdr + 0.04, w: cw, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
                } as any);
                return y + hdr + 0.04 + bh;
            };

        const m = roadmap.key_metrics_and_milestones;
        if (i + 1 < m.length) {
            w.addCardPair(renderMetric(m[i]), renderMetric(m[i + 1]), { borderColor: colors.violetBorder });
        } else {
            w.addCard(renderMetric(m[i]), { borderColor: colors.violetBorder });
        }
    }

    // ── Future Opportunities ─────────────────────────────────────────────────
    if (roadmap.future_opportunities?.length > 0) {
        w.addSectionBlock('Future Opportunities', colors.sky.bg, colors.sky.text);
        w.addBullets(roadmap.future_opportunities);
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

    const safe = (roadmap.roadmap_title || 'strategic-roadmap').replace(/[^a-z0-9\-\s]/gi, '').trim();
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
