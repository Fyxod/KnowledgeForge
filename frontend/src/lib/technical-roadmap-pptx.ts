/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { TechnicalRoadmapLLMOutput } from './api';
import {
    PAGE_W, PAGE_H, ML, CW, FONT,
    s, makeBullets, estimateTextHeight, estimateBulletsHeight,
    SlideWriter,
} from './pptx-slide-writer';

const colors = {
    primary: '0EA5E9',
    accent1: '7C3AED',
    accent2: 'D946EF',
    success: '10B981',
    danger: 'EF4444',
    slate600: '475569',
    slate800: '1F2937',
    headerBg: 'e3defc',
    border: 'c4bcf0',
};

// ── Phase card helper ──────────────────────────────────────────────────────────
function writePhaseCard(
    w: SlideWriter,
    label: string,
    phase: TechnicalRoadmapLLMOutput['phased_roadmap']['short_term'],
): void {
    // Header row: label + time frame
    const labelH = estimateTextHeight(label, FONT.phaseTitle, CW / 2);
    w.ensureSpace(labelH + 1.5); // need room for at least label + some content

    w.addTwoColumns(
        (x, y, colW) => {
            w.currentSlide.addText(s(label), {
                x, y, w: colW, h: labelH,
                fontSize: FONT.phaseTitle, bold: true, color: colors.accent2,
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

    w.addSubheading('Focus Areas', { indent: 0.1 });
    w.addBullets(phase.focus_areas, { fontSize: 9, indent: 0.1 });

    w.addSubheading('Initiatives', { indent: 0.1 });
    const initiatives = phase.key_initiatives.map(
        (it) => `${it.initiative}: ${it.objective} (Outcome: ${it.expected_outcome})`
    );
    w.addBullets(initiatives, { fontSize: 9, indent: 0.1 });

    w.addSubheading('Dependencies', { indent: 0.1 });
    w.addBullets(phase.dependencies, { fontSize: 9, indent: 0.1 });
}

// ── Build slides ───────────────────────────────────────────────────────────────
export function downloadTechnicalRoadmapPptx(roadmap: TechnicalRoadmapLLMOutput, filename?: string) {
    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'LETTER_PORTRAIT', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'LETTER_PORTRAIT';
    pptx.author = 'NotebookLM';
    pptx.subject = 'Technical Roadmap';
    pptx.title = s(roadmap.roadmap_title);

    const w = new SlideWriter(pptx);
    w.newSlide();

    // ── Title ──────────────────────────────────────────────────────────────
    w.addTitle(roadmap.roadmap_title);
    w.addSubtitle('Technical roadmap with vision, domains, phased plan, enablers, and risks.');
    w.gap(0.1);

    // ── Overall Vision ─────────────────────────────────────────────────────
    w.addSectionHeader('Overall Vision', colors.success);
    w.addText(roadmap.overall_vision.goal);
    w.addBullets(roadmap.overall_vision.success_metrics);

    // ── Current State Analysis ─────────────────────────────────────────────
    w.addSectionHeader('Current State Analysis', colors.primary);
    w.addText(roadmap.current_state_analysis.summary);

    // Two-column: challenges & capabilities
    w.addTwoColumns(
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hdrH = estimateTextHeight('Key Challenges', FONT.subheading, colW);
            slide.addText('Key Challenges', {
                x, y, w: colW, h: hdrH,
                fontSize: FONT.subheading, bold: true, color: colors.danger,
            } as any);
            let dy = y + hdrH + 0.04;

            const bh = estimateBulletsHeight(roadmap.current_state_analysis.key_challenges, 9, colW);
            slide.addText(makeBullets(roadmap.current_state_analysis.key_challenges, { fontSize: 9 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
        (x, y, colW) => {
            const slide = w.currentSlide;
            const hdrH = estimateTextHeight('Existing Capabilities', FONT.subheading, colW);
            slide.addText('Existing Capabilities', {
                x, y, w: colW, h: hdrH,
                fontSize: FONT.subheading, bold: true, color: colors.success,
            } as any);
            let dy = y + hdrH + 0.04;

            const bh = estimateBulletsHeight(roadmap.current_state_analysis.existing_capabilities, 9, colW);
            slide.addText(makeBullets(roadmap.current_state_analysis.existing_capabilities, { fontSize: 9 }) as any, {
                x, y: dy, w: colW, h: bh, valign: 'top', lineSpacingMultiple: 1.1,
            } as any);
            return dy + bh;
        },
    );

    // ── Technology Domains ──────────────────────────────────────────────────
    w.addSectionHeader('Technology Domains', colors.accent1);
    const domains = roadmap.technology_domains;
    const left = domains.filter((_, i) => i % 2 === 0);
    const right = domains.filter((_, i) => i % 2 !== 0);

    w.addTwoColumns(
        (x, y, colW) => {
            const slide = w.currentSlide;
            let dy = y;
            for (const d of left) {
                const nh = estimateTextHeight(d.domain_name, FONT.subheading, colW);
                slide.addText(s(d.domain_name), {
                    x, y: dy, w: colW, h: nh,
                    fontSize: FONT.subheading, bold: true, color: colors.accent1,
                } as any);
                dy += nh + 0.02;
                const dh = estimateTextHeight(d.description, FONT.body, colW);
                slide.addText(s(d.description), {
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
            for (const d of right) {
                const nh = estimateTextHeight(d.domain_name, FONT.subheading, colW);
                slide.addText(s(d.domain_name), {
                    x, y: dy, w: colW, h: nh,
                    fontSize: FONT.subheading, bold: true, color: colors.accent1,
                } as any);
                dy += nh + 0.02;
                const dh = estimateTextHeight(d.description, FONT.body, colW);
                slide.addText(s(d.description), {
                    x, y: dy, w: colW, h: dh,
                    fontSize: FONT.body, color: colors.slate800, valign: 'top',
                } as any);
                dy += dh + 0.08;
            }
            return dy;
        },
    );

    // ── Phased Technical Roadmap ────────────────────────────────────────────
    w.addSectionHeader('Phased Technical Roadmap', colors.accent2);
    writePhaseCard(w, 'Short Term', roadmap.phased_roadmap.short_term);
    writePhaseCard(w, 'Mid Term', roadmap.phased_roadmap.mid_term);
    writePhaseCard(w, 'Long Term', roadmap.phased_roadmap.long_term);

    // ── Key Technology Enablers ─────────────────────────────────────────────
    w.addSectionHeader('Key Technology Enablers', colors.primary);
    const enBullets = roadmap.key_technology_enablers.map((e) => `${e.enabler}: ${e.impact}`);
    w.addBullets(enBullets);

    // ── Risks & Mitigation ─────────────────────────────────────────────────
    w.addSectionHeader('Risks & Mitigation', colors.danger);
    const riskRows: any[][] = [[
        { text: 'Risk', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
        { text: 'Mitigation', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
    ]];
    roadmap.risks_and_mitigations.forEach((r) => {
        riskRows.push([{ text: s(r.risk) }, { text: s(r.mitigation) }]);
    });
    w.addTable(riskRows, { colWidths: [CW / 2, CW / 2], borderColor: colors.border });

    // ── Innovation Opportunities ───────────────────────────────────────────
    if (roadmap.innovation_opportunities.length > 0) {
        w.addSectionHeader('Innovation Opportunities', colors.primary);
        for (const iop of roadmap.innovation_opportunities) {
            w.addSubheading(`${iop.idea} (${iop.maturity_level})`, { color: colors.accent1 });
            w.addText(iop.description);
        }
    }

    // ── Tabular Summary ────────────────────────────────────────────────────
    if (roadmap.tabular_summary.length > 0) {
        w.addSectionHeader('Tabular Summary', colors.accent1);
        const sumRows: any[][] = [[
            { text: 'Time Frame', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
            { text: 'Key Points', options: { bold: true, color: colors.slate800, fill: { color: colors.headerBg } } },
        ]];
        roadmap.tabular_summary.forEach((r) => {
            sumRows.push([
                { text: s(r.time_frame) },
                { text: (r.key_points || []).map((p) => s(p)).join('\n') },
            ]);
        });
        w.addTable(sumRows, { colWidths: [CW * 0.25, CW * 0.75], borderColor: colors.border });
    }

    // ── LLM Inferred Additions ─────────────────────────────────────────────
    if (roadmap.llm_inferred_additions && roadmap.llm_inferred_additions.length > 0) {
        w.addSectionHeader('LLM Inferred Additions', colors.slate600);
        for (const a of roadmap.llm_inferred_additions) {
            w.addSubheading(a.section_title);
            w.addText(a.content);
        }
    }

    w.finalize();

    const safe = (roadmap.roadmap_title || 'technical-roadmap').replace(/[^a-z0-9\-\s]/gi, '').trim();
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
