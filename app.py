"""Streamlit frontend for the AURA Lab Banned Word Checker.

Implements the leaked NSF 3-stage decision tree faithfully:
  Stage 1: Title or Abstract -> Category 3 on hit, EARLY-EXIT
  Stage 2: Project Summary   -> Category 3 on hit, EARLY-EXIT
  Stage 3: Project Description -> Category 3 on hit, EARLY-EXIT
  All clean -> Category 1 (requires reviewer comment)

Uses core.py for engine + data/banned-words.json for word list, so this app
and the static web port stay in sync.
"""
from __future__ import annotations

import os
from io import BytesIO

import streamlit as st

import core

# ---------- Page config + styling ----------

st.set_page_config(
    page_title='AURA Lab Word Checker',
    page_icon=':lock:',
    layout='wide',
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@400;700&family=Public+Sans:wght@400;700&display=swap');
h1, h2, h3, h4, h5, h6 { font-family: 'Lexend', sans-serif; }
body, p, li, label, .stMarkdown { font-family: 'Public Sans', sans-serif; }
a, a:visited { color: #ea4335 !important; }
.cat-3 {
    background: #fdecea; border-left: 6px solid #c0392b;
    padding: 1rem; border-radius: 0.25rem; margin: 0.5rem 0;
}
.cat-1 {
    background: #e8f5e9; border-left: 6px solid #2e7d32;
    padding: 1rem; border-radius: 0.25rem; margin: 0.5rem 0;
}
.stage-card {
    background: #f7f7f7; border: 1px solid #ddd;
    padding: 0.75rem; border-radius: 0.25rem; margin: 0.25rem 0;
}
.stage-skipped { opacity: 0.55; }
.hit-pill {
    display: inline-block; background: #fff; border: 1px solid #c0392b;
    color: #c0392b; padding: 2px 8px; border-radius: 999px;
    margin: 2px; font-size: 0.85rem;
}
.source-tag {
    font-size: 0.7rem; opacity: 0.7; margin-left: 4px;
}
</style>
""", unsafe_allow_html=True)


# ---------- File parsing helpers ----------

def extract_text_from_docx(file_like) -> str:
    try:
        import docx
        doc = docx.Document(file_like)
        return '\n'.join(p.text for p in doc.paragraphs)
    except Exception as e:
        st.error(f'Error reading .docx: {e}')
        return ''


def extract_text_from_pdf(file_like) -> str:
    try:
        import pdfplumber
        text = ''
        with pdfplumber.open(file_like) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + '\n'
        return text
    except Exception as e:
        st.error(f'Error reading .pdf: {e}')
        return ''


# ---------- Sidebar ----------

with st.sidebar:
    logo_path = os.path.join('assets', 'aura-lab-logo.png')
    if os.path.exists(logo_path):
        st.image(logo_path)
    else:
        st.markdown('### AURA Lab')
    siue_logo = os.path.join('assets', 'siue-red-logo.png')
    if os.path.exists(siue_logo):
        st.image(siue_logo)
    st.markdown('---')
    st.markdown(
        'This tool is provided by the **AURA Lab** (Avatars, Users, '
        'Relationships, and Affect) at **Southern Illinois University '
        'Edwardsville**.'
    )
    st.markdown('[AURA Lab Website](https://aura-lab-siue.github.io)')
    st.markdown('[SIUE](https://www.siue.edu)')
    st.markdown('---')

    st.markdown('### Output Mode')
    mode = st.radio(
        'Format the result as:',
        options=['plain', 'reviewer'],
        format_func=lambda m: 'Plain (FLAGGED / CLEAN)' if m == 'plain' else 'Reviewer (Category 1 / 3)',
        index=0,
        help='Plain Mode is friendlier for grant writers. Reviewer Mode mirrors the leaked decision-tree language.',
    )

    st.markdown('---')
    st.markdown('### Word List')
    terms = core.load_wordlist()
    st.metric('Terms checked', len(terms))
    leaked_n = sum(1 for t in terms if t['source'] in ('leaked', 'both'))
    st.caption(f'{leaked_n} appear in the leaked NSF source list.')


# ---------- Main UI ----------

st.title('Banned Word Checker for Federal Grants')

st.markdown(
    'Implements the 3-stage decision tree from the leaked NSF review process. '
    'Provide your grant text in the three sections below, or upload a document '
    'and let the tool attempt to split it.'
)

with st.expander('How the decision tree works'):
    st.markdown("""
1. **Stage 1 — Title or Abstract** is checked first. Any flagged term here results in **Category 3**, and later stages are NOT scanned.
2. **Stage 2 — Project Summary** is checked only if Stage 1 was clean. A hit here also results in Category 3 with early exit.
3. **Stage 3 — Project Description** is checked only if Stages 1 and 2 were clean. A hit here results in Category 3.
4. **All stages clean** results in **Category 1** — in the leaked process, this requires a reviewer comment explaining why no DEIA/EO language was flagged.

This early-exit behavior mirrors the leaked diagram exactly. It means a doc flagged in the title generates a shorter report than one flagged in the description.
""")


tab_inputs, tab_upload = st.tabs(['Paste Sections', 'Upload File'])

with tab_inputs:
    col1, col2 = st.columns(2)
    with col1:
        title_text = st.text_area('Title', height=80, key='title_paste')
        abstract_text = st.text_area('Abstract', height=180, key='abstract_paste')
    with col2:
        summary_text = st.text_area('Project Summary', height=180, key='summary_paste')
        description_text = st.text_area('Project Description', height=180, key='description_paste')

with tab_upload:
    uploaded = st.file_uploader(
        'Upload a .docx or .pdf (the tool will attempt to split it by NSF section headers)',
        type=['docx', 'pdf'],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        buf = BytesIO(uploaded.getvalue())
        if uploaded.name.lower().endswith('.pdf'):
            raw = extract_text_from_pdf(buf)
        else:
            raw = extract_text_from_docx(buf)

        if raw:
            sections = core.split_sections(raw)
            st.success(
                'Auto-detected sections below. Edit any text before running the check.'
            )
            col1, col2 = st.columns(2)
            with col1:
                title_text = st.text_area('Title', value=sections['title'], height=80, key='title_upload')
                abstract_text = st.text_area('Abstract', value=sections['abstract'], height=180, key='abstract_upload')
            with col2:
                summary_text = st.text_area('Project Summary', value=sections['project_summary'], height=180, key='summary_upload')
                description_text = st.text_area('Project Description', value=sections['project_description'], height=180, key='description_upload')
        else:
            st.error('Could not extract text from the uploaded file.')


# Pull the active tab's values. Streamlit re-runs on every interaction so both
# tabs' widgets exist; we use whichever has content.
def _pick(key_paste, key_upload):
    return st.session_state.get(key_upload) or st.session_state.get(key_paste) or ''


title = _pick('title_paste', 'title_upload')
abstract = _pick('abstract_paste', 'abstract_upload')
summary = _pick('summary_paste', 'summary_upload')
description = _pick('description_paste', 'description_upload')

run_check = st.button('Run Check', type='primary', use_container_width=True)

if run_check:
    if not any([title.strip(), abstract.strip(), summary.strip(), description.strip()]):
        st.warning('Provide text in at least one section before running the check.')
    else:
        result = core.check_document(
            title=title,
            abstract=abstract,
            project_summary=summary,
            project_description=description,
        )
        label_info = core.format_label(result, mode=mode)

        # Headline card
        css_class = 'cat-3' if result.category == 3 else 'cat-1'
        st.markdown(f'''
<div class="{css_class}">
<strong>{label_info['label']}</strong><br>
{label_info['description']}
</div>
''', unsafe_allow_html=True)

        if result.flagged_stage:
            st.caption(f'First flagged stage: **{core.STAGE_LABELS[result.flagged_stage]}**. '
                       f'Per the leaked decision tree, later stages were not scanned.')

        # Stage-by-stage breakdown
        st.subheader('Stage breakdown')
        for stage in result.stages:
            css = 'stage-card stage-skipped' if not stage.scanned else 'stage-card'
            with st.container():
                st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
                header = f'**{stage.label}**'
                if not stage.scanned:
                    st.markdown(header + ' &mdash; *skipped (earlier-stage early-exit)*', unsafe_allow_html=True)
                elif stage.hits:
                    st.markdown(header + f' &mdash; **{len(stage.hits)} flagged term(s)**', unsafe_allow_html=True)
                    pills = ''
                    for h in stage.hits:
                        pills += f'<span class="hit-pill">{h.term} × {h.count}<span class="source-tag">[{h.source}]</span></span> '
                    st.markdown(pills, unsafe_allow_html=True)
                    with st.expander(f'Context snippets ({stage.label})'):
                        for h in stage.hits:
                            st.markdown(f'**{h.term}** ({h.count} match{"es" if h.count != 1 else ""})')
                            for c in h.contexts:
                                st.markdown(f'> {c}')
                else:
                    st.markdown(header + ' &mdash; clean', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        if result.category == 1:
            st.info(
                'Per the leaked process, Category 1 requires a reviewer comment '
                'explaining why "no" was chosen. Document your reasoning if you '
                'are using this tool for self-review before submission.'
            )
