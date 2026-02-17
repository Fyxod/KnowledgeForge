/* eslint-disable @typescript-eslint/no-explicit-any */
import PptxGenJS from 'pptxgenjs';
import {
    PAGE_W, PAGE_H, ML, CW, FONT,
    s, SlideWriter,
} from './pptx-slide-writer';

const colors = {
    slate800: '1F2937',
};

// ── Minimal markdown parser → semantic blocks ─────────────────────────────────
interface Block {
    type: 'title' | 'sectionTitle' | 'subheading' | 'bullet' | 'ordered' | 'text' | 'code' | 'blank';
    content: string;
}

function sanitize(str: string): string {
    return s(
        str.replace(/\*\*(.+?)\*\*/g, '$1')
           .replace(/\*(.+?)\*/g, '$1')
           .replace(/`(.+?)`/g, '$1'),
    );
}

function markdownToBlocks(md: string): Block[] {
    let src = (md || '')
        .replace(/([:\.\)])\s*-\s+/g, '$1\n- ')
        .replace(/\s{2,}-\s+/g, '\n- ');

    const lines = src.split(/\r?\n/);
    const blocks: Block[] = [];
    let inCode = false;

    for (const raw of lines) {
        const line = raw.trimEnd();

        if (/^```/.test(line)) { inCode = !inCode; continue; }
        if (inCode) { blocks.push({ type: 'code', content: s(raw) }); continue; }
        if (!line.trim()) { blocks.push({ type: 'blank', content: '' }); continue; }

        const h1 = line.match(/^#\s+(.+)$/);
        if (h1) { blocks.push({ type: 'title', content: s(h1[1]) }); continue; }

        const h2 = line.match(/^##\s+(.+)$/);
        if (h2) { blocks.push({ type: 'sectionTitle', content: s(h2[1]) }); continue; }

        const h3 = line.match(/^###\s+(.+)$/);
        if (h3) { blocks.push({ type: 'subheading', content: s(h3[1]) }); continue; }

        const boldOnly = line.match(/^\*\*(.+?)\*\*:?$/);
        if (boldOnly) { blocks.push({ type: 'sectionTitle', content: s(boldOnly[1]) }); continue; }

        const ul = line.match(/^[-*]\s+(.+)$/);
        if (ul) { blocks.push({ type: 'bullet', content: sanitize(ul[1]) }); continue; }

        const ol = line.match(/^\d+\.\s+(.+)$/);
        if (ol) { blocks.push({ type: 'ordered', content: sanitize(ol[1]) }); continue; }

        const clean = sanitize(line);
        if (clean) blocks.push({ type: 'text', content: clean });
    }

    return blocks;
}

// ── Public API ─────────────────────────────────────────────────────────────────
export function downloadSummaryPptx(markdown: string, filename?: string, opts?: { title?: string }) {
    const blocks = markdownToBlocks(markdown);
    const firstTitle = blocks.find((b) => b.type === 'title');
    const title = opts?.title || (firstTitle ? firstTitle.content : 'Document Summary');

    const pptx = new PptxGenJS();
    pptx.defineLayout({ name: 'LETTER_PORTRAIT', width: PAGE_W, height: PAGE_H });
    pptx.layout = 'LETTER_PORTRAIT';
    pptx.author = 'NotebookLM';
    pptx.subject = 'Summary';
    pptx.title = title;

    const w = new SlideWriter(pptx);
    w.newSlide();

    // Centered title
    w.addTitle(title);

    // Collect consecutive bullets for batch rendering
    let bulletBatch: string[] = [];
    let bulletType: 'bullet' | 'ordered' = 'bullet';

    const flushBullets = () => {
        if (bulletBatch.length === 0) return;
        if (bulletType === 'bullet') {
            w.addBullets(bulletBatch);
        } else {
            // Ordered list — render as numbered text
            const items = bulletBatch.map((t, i) => `${i + 1}. ${t}`);
            for (const item of items) {
                w.addText(item);
            }
        }
        bulletBatch = [];
    };

    for (const block of blocks) {
        // Skip the title we already rendered
        if (block.type === 'title' && block.content === title) continue;

        // Flush bullets if next block is not a matching list type
        if (block.type !== 'bullet' && block.type !== 'ordered') {
            flushBullets();
        }

        switch (block.type) {
            case 'title':
                w.addTitle(block.content);
                break;

            case 'sectionTitle':
                w.addSectionHeader(block.content, colors.slate800);
                break;

            case 'subheading':
                w.addSubheading(block.content);
                break;

            case 'bullet':
                bulletType = 'bullet';
                bulletBatch.push(block.content);
                break;

            case 'ordered':
                bulletType = 'ordered';
                bulletBatch.push(block.content);
                break;

            case 'text':
                w.addText(block.content);
                break;

            case 'code':
                w.addText(block.content, { fontSize: FONT.code });
                break;

            case 'blank':
                w.gap(0.06);
                break;
        }
    }

    flushBullets();
    w.finalize();

    // Fallback: if no content at all
    if (w.pageNum === 0) {
        const fallback = pptx.addSlide();
        fallback.addText(s(markdown).slice(0, 2000), {
            x: ML, y: 0.83, w: CW, h: 9,
            fontSize: FONT.body, color: colors.slate800, valign: 'top',
        } as any);
    }

    const safe = (title || 'summary').replace(/[^a-z0-9\-\s]/gi, '').trim() || 'summary';
    const name = filename || `${safe}.pptx`;
    pptx.writeFile({ fileName: name });
}
