/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { TechnicalRoadmapLLMOutput } from './api';

// ── Theme ──────────────────────────────────────────────────────────────────────
const colors = {
    primary: '0EA5E9',
    accent1: '7C3AED',
    accent2: 'D946EF',
    success: '10B981',
    warning: 'F59E0B',
    danger: 'EF4444',
    slate800: '1F2937',
    slate600: '475569',
    white: 'FFFFFF',
    lightBg: 'F1F0FB',
    border: 'c4bcf0',
};

const M = 0.5; // margin in inches

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
export function downloadTechnicalRoadmapPptx(roadmap: TechnicalRoadmapLLMOutput, filename?: string) {
    const pptx = new PptxGenJS();
    pptx.author = 'NotebookLM';
    pptx.subject = 'Technical Roadmap';
    pptx.title = s(roadmap.roadmap_title);
    pptx.layout = 'LAYOUT_WIDE';

    // ── Title Slide ────────────────────────────────────────────────────────────
    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: colors.primary };
    titleSlide.addText(s(roadmap.roadmap_title), {
        x: M, y: '30%', w: `${10 - M * 2}`, h: 1.2,
        fontSize: 32, bold: true, color: colors.white, align: 'center',
    } as any);
    titleSlide.addText('Technical Roadmap', {
        x: M, y: '52%', w: `${10 - M * 2}`,
        fontSize: 16, color: colors.border, align: 'center',
    } as any);

    // ── Overall Vision ─────────────────────────────────────────────────────────
    const visionSlide = pptx.addSlide();
    headerBar(visionSlide, pptx, 'Overall Vision', colors.success);
    visionSlide.addText(s(roadmap.overall_vision.goal), {
        x: M, y: 1.1, w: `${10 - M * 2}`, h: 0.8, fontSize: 14, color: colors.slate800, valign: 'top',
    } as any);
    visionSlide.addText(bullets(roadmap.overall_vision.success_metrics) as any, {
        x: M, y: 2.0, w: `${10 - M * 2}`, h: 4.5, valign: 'top', lineSpacingMultiple: 1.2,
    } as any);

    // ── Current State Analysis ─────────────────────────────────────────────────
    const stateSlide = pptx.addSlide();
    headerBar(stateSlide, pptx, 'Current State Analysis', colors.primary);
    stateSlide.addText(s(roadmap.current_state_analysis.summary), {
        x: M, y: 1.1, w: `${10 - M * 2}`, h: 0.8, fontSize: 13, color: colors.slate800, valign: 'top',
    } as any);
    // Two-column: challenges & capabilities
    stateSlide.addText('Key Challenges', { x: M, y: 2.0, w: 4, fontSize: 14, bold: true, color: colors.danger } as any);
    stateSlide.addText(bullets(roadmap.current_state_analysis.key_challenges, { fontSize: 12 }) as any, {
        x: M, y: 2.4, w: 4, h: 4.0, valign: 'top', lineSpacingMultiple: 1.2,
    } as any);
    stateSlide.addText('Existing Capabilities', { x: 5.3, y: 2.0, w: 4, fontSize: 14, bold: true, color: colors.success } as any);
    stateSlide.addText(bullets(roadmap.current_state_analysis.existing_capabilities, { fontSize: 12 }) as any, {
        x: 5.3, y: 2.4, w: 4, h: 4.0, valign: 'top', lineSpacingMultiple: 1.2,
    } as any);

    // ── Technology Domains ──────────────────────────────────────────────────────
    const domSlide = pptx.addSlide();
    headerBar(domSlide, pptx, 'Technology Domains', colors.accent1);
    const domRows: any[][] = [[
        { text: 'Domain', options: { bold: true, color: colors.white, fill: { color: colors.accent1 } } },
        { text: 'Description', options: { bold: true, color: colors.white, fill: { color: colors.accent1 } } },
    ]];
    roadmap.technology_domains.forEach((d) => {
        domRows.push([{ text: s(d.domain_name) }, { text: s(d.description) }]);
    });
    domSlide.addTable(domRows, {
        x: M, y: 1.1, w: `${10 - M * 2}`,
        fontSize: 12, border: { pt: 0.5, color: colors.border },
        colW: [3, 6],
        rowH: 0.5,
        autoPage: true,
    } as any);

    // ── Phased Roadmap slides ──────────────────────────────────────────────────
    const phases: { label: string; phase: typeof roadmap.phased_roadmap.short_term }[] = [
        { label: 'Short Term', phase: roadmap.phased_roadmap.short_term },
        { label: 'Mid Term', phase: roadmap.phased_roadmap.mid_term },
        { label: 'Long Term', phase: roadmap.phased_roadmap.long_term },
    ];
    for (const { label, phase } of phases) {
        const sl = pptx.addSlide();
        headerBar(sl, pptx, `${label} — ${s(phase.time_frame)}`, colors.accent2);
        let yOff = 1.1;

        sl.addText('Focus Areas', { x: M, y: yOff, w: 4, fontSize: 13, bold: true, color: colors.accent1 } as any);
        sl.addText(bullets(phase.focus_areas, { fontSize: 11 }) as any, {
            x: M, y: yOff + 0.35, w: 4, h: 2.0, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);

        sl.addText('Dependencies', { x: 5.3, y: yOff, w: 4, fontSize: 13, bold: true, color: colors.slate600 } as any);
        sl.addText(bullets(phase.dependencies, { fontSize: 11 }) as any, {
            x: 5.3, y: yOff + 0.35, w: 4, h: 2.0, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);

        yOff = 3.6;
        sl.addText('Key Initiatives', { x: M, y: yOff, w: 9, fontSize: 13, bold: true, color: colors.accent2 } as any);
        const initBullets = phase.key_initiatives.map(
            (it) => `${it.initiative}: ${it.objective} → ${it.expected_outcome}`
        );
        sl.addText(bullets(initBullets, { fontSize: 11 }) as any, {
            x: M, y: yOff + 0.35, w: `${10 - M * 2}`, h: 3.0, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);
    }

    // ── Key Technology Enablers ─────────────────────────────────────────────────
    const enSlide = pptx.addSlide();
    headerBar(enSlide, pptx, 'Key Technology Enablers', colors.primary);
    const enBullets = roadmap.key_technology_enablers.map((e) => `${e.enabler}: ${e.impact}`);
    enSlide.addText(bullets(enBullets) as any, {
        x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
    } as any);

    // ── Risks & Mitigations ────────────────────────────────────────────────────
    const riskSlide = pptx.addSlide();
    headerBar(riskSlide, pptx, 'Risks & Mitigations', colors.danger);
    const riskRows: any[][] = [[
        { text: 'Risk', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
        { text: 'Mitigation', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
    ]];
    roadmap.risks_and_mitigations.forEach((r) => {
        riskRows.push([{ text: s(r.risk) }, { text: s(r.mitigation) }]);
    });
    riskSlide.addTable(riskRows, {
        x: M, y: 1.1, w: `${10 - M * 2}`,
        fontSize: 12, border: { pt: 0.5, color: colors.border },
        colW: [4.5, 4.5],
        autoPage: true,
    } as any);

    // ── Innovation Opportunities ───────────────────────────────────────────────
    if (roadmap.innovation_opportunities.length > 0) {
        const innSlide = pptx.addSlide();
        headerBar(innSlide, pptx, 'Innovation Opportunities', colors.accent1);
        const innBullets = roadmap.innovation_opportunities.map(
            (i) => `${i.idea} (${i.maturity_level}): ${i.description}`
        );
        innSlide.addText(bullets(innBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Tabular Summary ────────────────────────────────────────────────────────
    if (roadmap.tabular_summary.length > 0) {
        const sumSlide = pptx.addSlide();
        headerBar(sumSlide, pptx, 'Tabular Summary', colors.accent1);
        const sumRows: any[][] = [[
            { text: 'Time Frame', options: { bold: true, color: colors.white, fill: { color: colors.accent1 } } },
            { text: 'Key Points', options: { bold: true, color: colors.white, fill: { color: colors.accent1 } } },
        ]];
        roadmap.tabular_summary.forEach((r) => {
            sumRows.push([
                { text: s(r.time_frame) },
                { text: (r.key_points || []).map((p) => s(p)).join('\n') },
            ]);
        });
        sumSlide.addTable(sumRows, {
            x: M, y: 1.1, w: `${10 - M * 2}`,
            fontSize: 11, border: { pt: 0.5, color: colors.border },
            colW: [2.5, 6.5],
            autoPage: true,
        } as any);
    }

    // ── LLM Inferred Additions ─────────────────────────────────────────────────
    if (roadmap.llm_inferred_additions && roadmap.llm_inferred_additions.length > 0) {
        const addSlide = pptx.addSlide();
        headerBar(addSlide, pptx, 'Additional Insights', colors.slate600);
        const addBullets = roadmap.llm_inferred_additions.map((a) => `${a.section_title}: ${a.content}`);
        addSlide.addText(bullets(addBullets) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
        } as any);
    }

    // ── Download ───────────────────────────────────────────────────────────────
    const safe = (roadmap.roadmap_title || 'technical-roadmap').replace(/[^a-z0-9\-\s]/gi, '').trim();
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
