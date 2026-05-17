"""Core engine for the AURA Lab Banned Word Checker.

Faithful to the leaked NSF decision tree:

    Stage 1: TITLE or ABSTRACT  -> if hit, Category 3, END
    Stage 2: PROJECT SUMMARY    -> if hit, Category 3, END
    Stage 3: PROJECT DESCRIPTION -> if hit, Category 3, END
    All clean -> Category 1, END (requires reviewer comment)

Loads canonical word list from data/banned-words.json so this module and the
JS port stay in sync.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Iterable

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WORDLIST = os.path.join(REPO_ROOT, 'data', 'banned-words.json')

STAGE_ORDER = ('title_or_abstract', 'project_summary', 'project_description')
STAGE_LABELS = {
    'title_or_abstract': 'Title or Abstract',
    'project_summary': 'Project Summary',
    'project_description': 'Project Description',
}


@dataclass
class Hit:
    term: str
    source: str           # 'leaked' | 'existing' | 'both'
    count: int
    contexts: list = field(default_factory=list)  # short snippets around each match


@dataclass
class StageResult:
    stage: str
    label: str
    hits: list             # list[Hit]
    text_length: int
    scanned: bool          # False if skipped due to earlier-stage early-exit

    @property
    def flagged(self) -> bool:
        return bool(self.hits)


@dataclass
class CheckResult:
    category: int              # 1 (clean) or 3 (flagged)
    flagged_stage: str | None  # which stage first caught a hit, or None
    stages: list               # list[StageResult] in order
    total_terms_checked: int
    requires_reviewer_comment: bool  # True if Category 1 (clean) per the leaked tree

    def to_dict(self) -> dict:
        d = asdict(self)
        d['stages'] = [asdict(s) for s in self.stages]
        return d


def load_wordlist(path: str = DEFAULT_WORDLIST) -> list[dict]:
    """Returns list of {term, source} dicts from canonical JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['terms']


def _compile_patterns(terms: list[dict]) -> list[tuple]:
    """Returns list of (compiled_pattern, term, source)."""
    out = []
    for entry in terms:
        term = entry['term']
        # Word-boundary match, case-insensitive. Phrase terms with spaces use \s+
        # so newline-wrapped or extra-spaced text still matches.
        escaped = re.escape(term).replace(r'\ ', r'\s+')
        pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
        out.append((pattern, term, entry['source']))
    return out


def _extract_contexts(text: str, pattern: re.Pattern, max_contexts: int = 3,
                      window: int = 40) -> list[str]:
    """Return up to max_contexts short snippets around matches for review UX."""
    contexts = []
    for m in pattern.finditer(text):
        if len(contexts) >= max_contexts:
            break
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        snippet = text[start:end].replace('\n', ' ').strip()
        if start > 0:
            snippet = '... ' + snippet
        if end < len(text):
            snippet = snippet + ' ...'
        contexts.append(snippet)
    return contexts


def scan_text(text: str, patterns: list[tuple]) -> list[Hit]:
    """Returns sorted list[Hit] (most frequent first) for a given stage of text."""
    if not text or not text.strip():
        return []
    hits = []
    for pattern, term, source in patterns:
        matches = list(pattern.finditer(text))
        if matches:
            hits.append(Hit(
                term=term,
                source=source,
                count=len(matches),
                contexts=_extract_contexts(text, pattern),
            ))
    hits.sort(key=lambda h: (-h.count, h.term))
    return hits


def check_document(
    *,
    title: str = '',
    abstract: str = '',
    project_summary: str = '',
    project_description: str = '',
    wordlist_path: str = DEFAULT_WORDLIST,
) -> CheckResult:
    """Run the 3-stage decision tree. Returns CheckResult.

    Stage 1 bundles title + abstract per the leaked diagram. If either has a
    hit, the document is Category 3 and later stages are NOT scanned (faithful
    to the leaked early-exit behavior).
    """
    terms = load_wordlist(wordlist_path)
    patterns = _compile_patterns(terms)

    stage_texts = {
        'title_or_abstract': '\n\n'.join(t for t in (title, abstract) if t),
        'project_summary': project_summary or '',
        'project_description': project_description or '',
    }

    stages: list[StageResult] = []
    flagged_stage = None

    for stage_key in STAGE_ORDER:
        text = stage_texts[stage_key]
        if flagged_stage is not None:
            # Early-exit: don't scan further stages
            stages.append(StageResult(
                stage=stage_key,
                label=STAGE_LABELS[stage_key],
                hits=[],
                text_length=len(text),
                scanned=False,
            ))
            continue

        hits = scan_text(text, patterns)
        stages.append(StageResult(
            stage=stage_key,
            label=STAGE_LABELS[stage_key],
            hits=hits,
            text_length=len(text),
            scanned=True,
        ))
        if hits:
            flagged_stage = stage_key

    category = 3 if flagged_stage else 1
    return CheckResult(
        category=category,
        flagged_stage=flagged_stage,
        stages=stages,
        total_terms_checked=len(terms),
        requires_reviewer_comment=(category == 1),
    )


# ---------- Plain-mode label mapping ----------

PLAIN_MODE_LABELS = {
    1: 'CLEAN',
    3: 'FLAGGED',
}

PLAIN_MODE_DESCRIPTIONS = {
    1: 'No flagged terms found. Reviewer would document why "no" was chosen.',
    3: 'Flagged terms found in this document. Revise before submission.',
}

REVIEWER_MODE_LABELS = {
    1: 'Category 1',
    3: 'Category 3',
}

REVIEWER_MODE_DESCRIPTIONS = {
    1: 'Category 1: No DEIA or other EO language found. Reviewer adds comment to explain why "no" was chosen.',
    3: 'Category 3: Retain flag. DEIA and other EO language found.',
}


def format_label(result: CheckResult, *, mode: str = 'plain') -> dict:
    """Returns {label, description} dict appropriate for the chosen mode.

    mode: 'plain' or 'reviewer'
    """
    if mode == 'reviewer':
        return {
            'label': REVIEWER_MODE_LABELS[result.category],
            'description': REVIEWER_MODE_DESCRIPTIONS[result.category],
        }
    return {
        'label': PLAIN_MODE_LABELS[result.category],
        'description': PLAIN_MODE_DESCRIPTIONS[result.category],
    }


# ---------- Best-effort section detection from unstructured text ----------

# Common NSF section headers (case-insensitive). Order matters for the regex.
SECTION_HEADERS = [
    ('project_description', r'project\s+description'),
    ('project_summary', r'project\s+summary'),
    ('abstract', r'abstract'),
    ('title', r'(?:project\s+)?title'),
]


def split_sections(full_text: str) -> dict[str, str]:
    """Best-effort split of a raw document into {title, abstract, project_summary, project_description}.

    Looks for common headers; everything before the first detected header
    falls into 'title' if short, else 'abstract'. Sections not detected are
    returned as empty strings.

    This is a convenience for the case where someone uploads a full grant doc
    without manually placing text in three boxes. UI should let the user
    confirm and edit the split before running the check.
    """
    # Build a combined header pattern that captures which section starts where
    parts = []
    for key, pat in SECTION_HEADERS:
        parts.append(rf'(?P<{key}>^\s*{pat}\s*:?\s*$)')
    combined = re.compile('|'.join(parts), re.IGNORECASE | re.MULTILINE)

    matches = list(combined.finditer(full_text))
    if not matches:
        # No headers found; dump everything into project_description as a fallback
        return {
            'title': '',
            'abstract': '',
            'project_summary': '',
            'project_description': full_text.strip(),
        }

    sections = {'title': '', 'abstract': '', 'project_summary': '', 'project_description': ''}

    # Preamble before first header
    preamble = full_text[:matches[0].start()].strip()
    if preamble:
        if len(preamble) < 300:
            sections['title'] = preamble
        else:
            sections['abstract'] = preamble

    # Each header captures from end-of-header to start-of-next-header
    for i, m in enumerate(matches):
        # Which named group matched?
        for key, _ in SECTION_HEADERS:
            if m.group(key):
                start = m.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
                content = full_text[start:end].strip()
                if key in sections:
                    # If already populated, append (handles duplicate headers gracefully)
                    sections[key] = (sections[key] + '\n\n' + content).strip() if sections[key] else content
                break

    return sections
