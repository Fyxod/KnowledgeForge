/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { StrategicRoadmapLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, ML, CW, FONT,
    s, makeBullets, estimateTextHeight, estimateBulletsHeight,
    SlideWriter,
} from './pptx-slide-writer';

const colors = {
    primary: '6d56f1',
    accent1: 'D946EF',
    accent2: '5341c8',
    success: '10B981',
    warning: 'F59E0B',
    danger: 'EF4444',
    slate600: '475569',
    slate800: '1F2937',
    headerBg: 'e3defc',
    border: 'c4bcf0',
    white: 'FFFFFF',
};

// ── Phase card helper ──────────────────────────────────────────────────────────
function writePhaseCard(w: SlideWriter, phase: StrategicRoadmapLLMOutput['phased_roadmap'][0]): void {
    const labelH = estimateTextHeight(phase.phase, FONT.phaseTitle, CW / 2);
    w.ensureSpace(labelH + 1.5);

    w.addTwoColumns(
        (x, y, colW) => {
            w.currentSlide.addText(s(phase.phase), {
                x, y, w: colW, h: labelH,
                fontSize: FONT.phaseTitle, bold: true, color: colors.accent1,
            } as any);
            return y + labelH;
        },
        (x, y, colW) => {
            w.currentSlide.addText(s(phase.time_frame), {
                x, y, w: colW, h: labelH,
                fontSize: FONT.body, color: colors.slate600, align: 'right',
            } as any);
            return y + labelH;
        },
    );

    w.addLine({ indent: 0.1 });

    w.addSubheading('Objectives', { indent: 0.1 });
    w.addBullets(phase.key_objectives, { fontSize: 9, indent: 0.1 });

    w.addSubheading('Initiatives', { indent: 0.1 });
    w.addBullets(phase.key_initiatives, { fontSize: 9, indent: 0.1 });

    w.addSubheading('Expected Outcomes', { indent: 0.1 });
    w.addBullets(phase.expected_outcomes, { fontSize: 9, indent: 0.1 });
}

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadStrategicRoadmapPptx(roadmap: StrategicRoadmapLLMOutput, filename?: string) {
    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'LETTER_PORTRAIT', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'LETTER_PORTRAIT';
    pptx.author = 'NotebookLM';
    pptx.subject = 'Strategic Roadmap';
    pptx.title = s(roadmap.roadmap_title);

    const w = new SlideWriter(pptx);
    w.newSlide();

    // ── Title ──────────────────────────────────────────────────────────────
    w.addTitle(roadmap.roadmap_title);
    w.addSubtitle('Strategic, phased plan with goals, enablers, risks, and measurable milestones.');
    w.gap(0.1);

    // ── Vision & End Goal ──────────────────────────────────────────────────
    w.addSectionHeader('Vision & End Goal', colors.success);
    w.addText(roadmap.vision_and_end_goal.description);
    w.addBullets(roadmap.vision_and_end_goal.success_criteria);

    // ── Current Baseline ───────────────────────────────────────────────────
    w.addSectionHeader('Current Baseline', colors.accent2);
    w.addText(roadmap.current_baseline.summary);

    // SWOT 2×2 table
    const swot = roadmap.current_baseline.swot;
    const swotRows: any[][] = [
        [
            { text: 'Strengths', options: { bold: true, color: colors.white, fill: { color: colors.success }, fontSize: FONT.swotTitle } },
            { text: 'Weaknesses', options: { bold: true, color: colors.white, fill: { color: colors.warning }, fontSize: FONT.swotTitle } },
        ],
        [
            { text: swot.strengths.map((x) => `• ${s(x)}`).join('\n'), options: { fontSize: 9 } },
            { text: swot.weaknesses.map((x) => `• ${s(x)}`).join('\n'), options: { fontSize: 9 } },
        ],
        [
            { text: 'Opportunities', options: { bold: true, color: colors.white, fill: { color: colors.accent2 }, fontSize: FONT.swotTitle } },
            { text: 'Threats', options: { bold: true, color: colors.white, fill: { color: colors.danger }, fontSize: FONT.swotTitle } },
        ],
        [
            { text: swot.opportunities.map((x) => `• ${s(x)}`).join('\n'), options: { fontSize: 9 } },
            { text: swot.threats.map((x) => `• ${s(x)}`).join('\n'), options: { fontSize: 9 } },
        ],
    ];
    w.addTable(swotRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.border });

    // ── Strategic Pillars ──────────────────────────────────────────────────
    w.addSectionHeader('Strategic Pillars', colors.primary);

    const pillars = roadmap.strategic_pillars;
    const leftPillars = pillars.filter((_, i) => i % 2 === 0);
    const rightPillars = pillars.filter((_, i) => i % 2 !== 0);

    w.addTwoColumns(
        (x, y, colW) => {
            const slide = w.currentSlide;
            let dy = y;
            for (const p of leftPillars) {
                const nh = estimateTextHeight(p.pillar_name, FONT.pillTitle, colW);
                slide.addText(s(p.pillar_name), {
                    x, y: dy, w: colW, h: nh,
                    fontSize: FONT.pillTitle, bold: true, color: colors.primary,
                } as any);
                dy += nh + 0.02;
                const dh = estimateTextHeight(p.description, FONT.body, colW);
                slide.addText(s(p.description), {
                    x, y: dy, w: colW, h: dh,
                    fontSize: FONT.body, color: colors.slate800, valign: 'top',
                } as any);
                dy += dh + 0.08;
            }
            return dy;
        },
        (x, y, colW) => {
            const slide = w.currentSlide;
            let dy = y;
            for (const p of rightPillars) {
                const nh = estimateTextHeight(p.pillar_name, FONT.pillTitle, colW);
                slide.addText(s(p.pillar_name), {
                    x, y: dy, w: colW, h: nh,
                    fontSize: FONT.pillTitle, bold: true, color: colors.primary,
                } as any);
                dy += nh + 0.02;
                const dh = estimateTextHeight(p.description, FONT.body, colW);
                slide.addText(s(p.description), {
                    x, y: dy, w: colW, h: dh,
                    fontSize: FONT.body, color: colors.slate800, valign: 'top',
                } as any);
                dy += dh + 0.08;
            }
            return dy;
        },
    );

    // ── Phased Strategic Roadmap ───────────────────────────────────────────
    w.addSectionHeader('Phased Strategic Roadmap', colors.accent1);
    for (const phase of roadmap.phased_roadmap) {
        writePhaseCard(w, phase);
    }

    // ── Enablers & Dependencies ────────────────────────────────────────────
    w.addSectionHeader('Enablers & Dependencies', colors.primary);

    w.addTwoColumns(
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hh = estimateTextHeight('Technologies', FONT.subheading, colW);
            slide.addText('Technologies', {
                x, y, w: colW, h: hh,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            let dy = y + hh + 0.04;
            const bh = estimateBulletsHeight(roadmap.enablers_and_dependencies.technologies, 9, colW);
            slide.addText(makeBullets(roadmap.enablers_and_dependencies.technologies, { fontSize: 9 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hh = estimateTextHeight('Skills & Resources', FONT.subheading, colW);
            slide.addText('Skills & Resources', {
                x, y, w: colW, h: hh,
                fontSize: FONT.subheading, bold: true, color: colors.slate800,
            } as any);
            let dy = y + hh + 0.04;
            const bh = estimateBulletsHeight(roadmap.enablers_and_dependencies.skills_and_resources, 9, colW);
            slide.addText(makeBullets(roadmap.enablers_and_dependencies.skills_and_resources, { fontSize: 9 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
    );

    w.addSubheading('Stakeholders');
    w.addBullets(roadmap.enablers_and_dependencies.stakeholders, { fontSize: 9 });

    // ── Risks & Mitigation ─────────────────────────────────────────────────
    w.addSectionHeader('Risks & Mitigation', colors.danger);
    const riskRows: any[][] = [[
        { text: 'Risk', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
        { text: 'Mitigation', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
    ]];
    roadmap.risks_and_mitigation.forEach((r) => {
        riskRows.push([{ text: s(r.risk) }, { text: s(r.mitigation_strategy) }]);
    });
    w.addTable(riskRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.border });

    // ── Key Metrics & Milestones ───────────────────────────────────────────
    w.addSectionHeader('Key Metrics & Milestones', colors.accent2);
    for (const m of roadmap.key_metrics_and_milestones) {
        w.addSubheading(m.year_or_phase, { color: colors.accent2 });
        w.addBullets(m.metrics, { fontSize: 9 });
    }

    // ── Future Opportunities ───────────────────────────────────────────────
    if (roadmap.future_opportunities.length > 0) {
        w.addSectionHeader('Future Opportunities', colors.accent2);
        w.addBullets(roadmap.future_opportunities);
    }

    // ── LLM Inferred Additions ─────────────────────────────────────────────
    if (roadmap.llm_inferred_additions && roadmap.llm_inferred_additions.length > 0) {
        w.addSectionHeader('Additional Insights', colors.slate600);
        for (const a of roadmap.llm_inferred_additions) {
            w.addSubheading(a.section_title);
            w.addText(a.content);
        }
    }

    w.finalize();

    const safe = (roadmap.roadmap_title || 'strategic-roadmap').replace(/[^a-z0-9\-\s]/gi, '').trim();
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
