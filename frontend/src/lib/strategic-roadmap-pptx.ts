/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import type { StrategicRoadmapLLMOutput } from './api';

// ── Theme ──────────────────────────────────────────────────────────────────────
const colors = {
    primary: '6d56f1',
    accent1: 'D946EF',
    accent2: '5341c8',
    success: '10B981',
    warning: 'F59E0B',
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
export function downloadStrategicRoadmapPptx(roadmap: StrategicRoadmapLLMOutput, filename?: string) {
    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'NARROW_10_33', width: 10.33, height: 7.5 }); // 3" narrower than default wide
    pptx.layout = 'NARROW_10_33';
    pptx.author = 'NotebookLM';
    pptx.subject = 'Strategic Roadmap';
    pptx.title = s(roadmap.roadmap_title);

    // ── Title Slide ────────────────────────────────────────────────────────────
    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: colors.primary };
    titleSlide.addText(s(roadmap.roadmap_title), {
        x: M, y: '30%', w: `${10 - M * 2}`, h: 1.2,
        fontSize: 32, bold: true, color: colors.white, align: 'center',
    } as any);
    titleSlide.addText('Strategic Roadmap', {
        x: M, y: '52%', w: `${10 - M * 2}`,
        fontSize: 16, color: colors.border, align: 'center',
    } as any);

    // ── Vision & End Goal ──────────────────────────────────────────────────────
    const visionSlide = pptx.addSlide();
    headerBar(visionSlide, pptx, 'Vision & End Goal', colors.success);
    visionSlide.addText(s(roadmap.vision_and_end_goal.description), {
        x: M, y: 1.1, w: `${10 - M * 2}`, h: 1.0, fontSize: 14, color: colors.slate800, valign: 'top',
    } as any);
    visionSlide.addText('Success Criteria', { x: M, y: 2.2, w: 4, fontSize: 14, bold: true, color: colors.success } as any);
    visionSlide.addText(bullets(roadmap.vision_and_end_goal.success_criteria) as any, {
        x: M, y: 2.6, w: `${10 - M * 2}`, h: 4.0, valign: 'top', lineSpacingMultiple: 1.2,
    } as any);

    // ── Current Baseline + SWOT ────────────────────────────────────────────────
    const baseSlide = pptx.addSlide();
    headerBar(baseSlide, pptx, 'Current Baseline', colors.accent2);
    baseSlide.addText(s(roadmap.current_baseline.summary), {
        x: M, y: 1.1, w: `${10 - M * 2}`, h: 0.7, fontSize: 13, color: colors.slate800, valign: 'top',
    } as any);

    // SWOT as 2×2 table
    const swot = roadmap.current_baseline.swot;
    const swotRows: any[][] = [
        [
            { text: 'Strengths', options: { bold: true, color: colors.white, fill: { color: colors.success } } },
            { text: 'Weaknesses', options: { bold: true, color: colors.white, fill: { color: colors.warning } } },
        ],
        [
            { text: swot.strengths.map((x) => `• ${s(x)}`).join('\n') },
            { text: swot.weaknesses.map((x) => `• ${s(x)}`).join('\n') },
        ],
        [
            { text: 'Opportunities', options: { bold: true, color: colors.white, fill: { color: colors.accent2 } } },
            { text: 'Threats', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
        ],
        [
            { text: swot.opportunities.map((x) => `• ${s(x)}`).join('\n') },
            { text: swot.threats.map((x) => `• ${s(x)}`).join('\n') },
        ],
    ];
    baseSlide.addText('', { x: M, y: 1.9, h: 0.8 });
    baseSlide.addTable(swotRows, {
        x: M, y: 2.0, w: `${10 - M * 2}`,
        fontSize: 11, border: { pt: 0.5, color: colors.border },
        colW: [4.5, 4.5],
    } as any);

    // ── Strategic Pillars ──────────────────────────────────────────────────────
    const pillSlide = pptx.addSlide();
    headerBar(pillSlide, pptx, 'Strategic Pillars', colors.primary);
    const pillBullets = roadmap.strategic_pillars.map((p) => `${p.pillar_name}: ${p.description}`);
    pillSlide.addText(bullets(pillBullets) as any, {
        x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
    } as any);

    // ── Phased Roadmap ─────────────────────────────────────────────────────────
    for (const phase of roadmap.phased_roadmap) {
        const sl = pptx.addSlide();
        headerBar(sl, pptx, `${s(phase.phase)} — ${s(phase.time_frame)}`, colors.accent1);

        sl.addText('Key Objectives', { x: M, y: 1.1, w: 4, fontSize: 13, bold: true, color: colors.accent2 } as any);
        sl.addText(bullets(phase.key_objectives, { fontSize: 11 }) as any, {
            x: M, y: 1.45, w: 4, h: 2.0, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);

        sl.addText('Key Initiatives', { x: 5.3, y: 1.1, w: 4, fontSize: 13, bold: true, color: colors.primary } as any);
        sl.addText(bullets(phase.key_initiatives, { fontSize: 11 }) as any, {
            x: 5.3, y: 1.45, w: 4, h: 2.0, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);

        sl.addText('Expected Outcomes', { x: M, y: 3.8, w: 9, fontSize: 13, bold: true, color: colors.success } as any);
        sl.addText(bullets(phase.expected_outcomes, { fontSize: 11 }) as any, {
            x: M, y: 4.15, w: `${10 - M * 2}`, h: 3.0, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);
    }

    // ── Enablers & Dependencies ────────────────────────────────────────────────
    const enSlide = pptx.addSlide();
    headerBar(enSlide, pptx, 'Enablers & Dependencies', colors.primary);
    enSlide.addText('Technologies', { x: M, y: 1.1, w: 3, fontSize: 13, bold: true, color: colors.primary } as any);
    enSlide.addText(bullets(roadmap.enablers_and_dependencies.technologies, { fontSize: 11 }) as any, {
        x: M, y: 1.45, w: 3, h: 2.5, valign: 'top', lineSpacingMultiple: 1.15,
    } as any);
    enSlide.addText('Skills & Resources', { x: 3.7, y: 1.1, w: 3, fontSize: 13, bold: true, color: colors.accent2 } as any);
    enSlide.addText(bullets(roadmap.enablers_and_dependencies.skills_and_resources, { fontSize: 11 }) as any, {
        x: 3.7, y: 1.45, w: 3, h: 2.5, valign: 'top', lineSpacingMultiple: 1.15,
    } as any);
    enSlide.addText('Stakeholders', { x: 7.0, y: 1.1, w: 2.5, fontSize: 13, bold: true, color: colors.slate600 } as any);
    enSlide.addText(bullets(roadmap.enablers_and_dependencies.stakeholders, { fontSize: 11 }) as any, {
        x: 7.0, y: 1.45, w: 2.5, h: 2.5, valign: 'top', lineSpacingMultiple: 1.15,
    } as any);

    // ── Risks & Mitigation ─────────────────────────────────────────────────────
    const riskSlide = pptx.addSlide();
    headerBar(riskSlide, pptx, 'Risks & Mitigation', colors.danger);
    const riskRows: any[][] = [[
        { text: 'Risk', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
        { text: 'Mitigation', options: { bold: true, color: colors.white, fill: { color: colors.danger } } },
    ]];
    roadmap.risks_and_mitigation.forEach((r) => {
        riskRows.push([{ text: s(r.risk) }, { text: s(r.mitigation_strategy) }]);
    });
    riskSlide.addTable(riskRows, {
        x: M, y: 1.1, w: `${10 - M * 2}`,
        fontSize: 12, border: { pt: 0.5, color: colors.border },
        colW: [4.5, 4.5],
        autoPage: true,
    } as any);

    // ── Key Metrics & Milestones ───────────────────────────────────────────────
    if (roadmap.key_metrics_and_milestones.length > 0) {
        const metSlide = pptx.addSlide();
        headerBar(metSlide, pptx, 'Key Metrics & Milestones', colors.accent2);
        const metBullets: string[] = [];
        roadmap.key_metrics_and_milestones.forEach((m) => {
            metBullets.push(`${m.year_or_phase}:`);
            m.metrics.forEach((mt) => metBullets.push(`  ${mt}`));
        });
        metSlide.addText(bullets(metBullets, { fontSize: 12 }) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.15,
        } as any);
    }

    // ── Future Opportunities ───────────────────────────────────────────────────
    if (roadmap.future_opportunities.length > 0) {
        const futSlide = pptx.addSlide();
        headerBar(futSlide, pptx, 'Future Opportunities', colors.accent2);
        futSlide.addText(bullets(roadmap.future_opportunities) as any, {
            x: M, y: 1.1, w: `${10 - M * 2}`, h: 5.5, valign: 'top', lineSpacingMultiple: 1.2,
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
    const safe = (roadmap.roadmap_title || 'strategic-roadmap').replace(/[^a-z0-9\-\s]/gi, '').trim();
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
