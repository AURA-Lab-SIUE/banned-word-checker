/**
 * AURA Lab Banned Word Checker — browser engine.
 * JS port of core.py. Loads the same data/banned-words.json so the Python
 * Streamlit app and this static page stay in sync.
 */

const STAGE_ORDER = ['title_or_abstract', 'project_summary', 'project_description'];
const STAGE_LABELS = {
  title_or_abstract: 'Title or Abstract',
  project_summary: 'Project Summary',
  project_description: 'Project Description',
};

const SECTION_HEADERS = [
  { key: 'project_description', re: /project\s+description/i },
  { key: 'project_summary', re: /project\s+summary/i },
  { key: 'abstract', re: /abstract/i },
  { key: 'title', re: /(?:project\s+)?title/i },
];

let wordlistCache = null;
let patternsCache = null;

/** Load the canonical word list. Cached after first call. */
export async function loadWordlist(path = '../data/banned-words.json') {
  if (wordlistCache) return wordlistCache;
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to fetch word list: ${res.status}`);
  const data = await res.json();
  wordlistCache = data;
  return data;
}

function escapeRegex(s) {
  return s.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
}

/** Compile regex patterns for all terms. Cached. */
function compilePatterns(terms) {
  if (patternsCache) return patternsCache;
  patternsCache = terms.map(({ term, source }) => {
    // Word-boundary match; phrase spaces become \s+ so newline-wrapped text matches.
    const escaped = escapeRegex(term).replace(/\\ /g, '\\s+').replace(/ /g, '\\s+');
    const pattern = new RegExp('\\b' + escaped + '\\b', 'gi');
    return { pattern, term, source };
  });
  return patternsCache;
}

function extractContexts(text, pattern, { maxContexts = 3, window = 40 } = {}) {
  const contexts = [];
  // Reset lastIndex to be safe since pattern has /g flag
  pattern.lastIndex = 0;
  let m;
  while ((m = pattern.exec(text)) !== null) {
    if (contexts.length >= maxContexts) break;
    const start = Math.max(0, m.index - window);
    const end = Math.min(text.length, m.index + m[0].length + window);
    let snippet = text.slice(start, end).replace(/\n/g, ' ').trim();
    if (start > 0) snippet = '... ' + snippet;
    if (end < text.length) snippet = snippet + ' ...';
    contexts.push(snippet);
    // Guard against zero-width matches
    if (m.index === pattern.lastIndex) pattern.lastIndex++;
  }
  return contexts;
}

/** Scan one stage of text. Returns array of {term, source, count, contexts}. */
function scanText(text, patterns) {
  if (!text || !text.trim()) return [];
  const hits = [];
  for (const { pattern, term, source } of patterns) {
    pattern.lastIndex = 0;
    const matches = text.match(pattern);
    if (matches && matches.length) {
      hits.push({
        term,
        source,
        count: matches.length,
        contexts: extractContexts(text, pattern),
      });
    }
  }
  hits.sort((a, b) => (b.count - a.count) || a.term.localeCompare(b.term));
  return hits;
}

/** Run the 3-stage decision tree. Returns CheckResult shape. */
export async function checkDocument({ title = '', abstract = '', projectSummary = '', projectDescription = '' } = {}) {
  const data = await loadWordlist();
  const patterns = compilePatterns(data.terms);

  const stageTexts = {
    title_or_abstract: [title, abstract].filter(Boolean).join('\n\n'),
    project_summary: projectSummary || '',
    project_description: projectDescription || '',
  };

  const stages = [];
  let flaggedStage = null;

  for (const key of STAGE_ORDER) {
    const text = stageTexts[key];
    if (flaggedStage !== null) {
      stages.push({
        stage: key,
        label: STAGE_LABELS[key],
        hits: [],
        textLength: text.length,
        scanned: false,
      });
      continue;
    }
    const hits = scanText(text, patterns);
    stages.push({
      stage: key,
      label: STAGE_LABELS[key],
      hits,
      textLength: text.length,
      scanned: true,
    });
    if (hits.length) flaggedStage = key;
  }

  const category = flaggedStage ? 3 : 1;
  return {
    category,
    flaggedStage,
    stages,
    totalTermsChecked: data.terms.length,
    requiresReviewerComment: category === 1,
  };
}

const PLAIN_LABELS = { 1: 'CLEAN', 3: 'FLAGGED' };
const PLAIN_DESCRIPTIONS = {
  1: 'No flagged terms found. Reviewer would document why "no" was chosen.',
  3: 'Flagged terms found in this document. Revise before submission.',
};
const REVIEWER_LABELS = { 1: 'Category 1', 3: 'Category 3' };
const REVIEWER_DESCRIPTIONS = {
  1: 'Category 1: No DEIA or other EO language found. Reviewer adds comment to explain why "no" was chosen.',
  3: 'Category 3: Retain flag. DEIA and other EO language found.',
};

export function formatLabel(result, mode = 'plain') {
  if (mode === 'reviewer') {
    return {
      label: REVIEWER_LABELS[result.category],
      description: REVIEWER_DESCRIPTIONS[result.category],
    };
  }
  return {
    label: PLAIN_LABELS[result.category],
    description: PLAIN_DESCRIPTIONS[result.category],
  };
}

/** Best-effort split of raw text into the 4 NSF section buckets. */
export function splitSections(fullText) {
  const sections = { title: '', abstract: '', project_summary: '', project_description: '' };
  // Build line-anchored header regex
  const headerLines = [];
  const lines = fullText.split('\n');
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    for (const { key, re } of SECTION_HEADERS) {
      // Match a line that is JUST the header (allow trailing colon, optional)
      if (new RegExp('^\\s*' + re.source.replace(/^.|.$/g, '') + '\\s*:?\\s*$', 'i').test(trimmed)) {
        headerLines.push({ key, lineIdx: i });
        break;
      }
    }
  });

  if (headerLines.length === 0) {
    sections.project_description = fullText.trim();
    return sections;
  }

  // Preamble (everything before first header)
  const preamble = lines.slice(0, headerLines[0].lineIdx).join('\n').trim();
  if (preamble) {
    if (preamble.length < 300) sections.title = preamble;
    else sections.abstract = preamble;
  }

  headerLines.forEach((h, i) => {
    const startLine = h.lineIdx + 1;
    const endLine = i + 1 < headerLines.length ? headerLines[i + 1].lineIdx : lines.length;
    const content = lines.slice(startLine, endLine).join('\n').trim();
    if (sections.hasOwnProperty(h.key)) {
      sections[h.key] = sections[h.key]
        ? (sections[h.key] + '\n\n' + content).trim()
        : content;
    }
  });

  return sections;
}

// ---------- File parsing helpers ----------

/** Extract text from a File (.docx) using mammoth.js. Returns Promise<string>. */
export async function extractDocxText(file) {
  if (!window.mammoth) throw new Error('mammoth.js not loaded');
  const arrayBuffer = await file.arrayBuffer();
  const result = await window.mammoth.extractRawText({ arrayBuffer });
  return result.value || '';
}

/** Extract text from a File (.pdf) using PDF.js. Returns Promise<string>. */
export async function extractPdfText(file) {
  if (!window.pdfjsLib) throw new Error('PDF.js not loaded');
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const pageTexts = [];
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const content = await page.getTextContent();
    pageTexts.push(content.items.map(it => it.str).join(' '));
  }
  return pageTexts.join('\n');
}
