"""Merge leaked NSF word list + existing app.py list into canonical data/banned-words.json."""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Leaked list from user message (with OCR artifacts that we clean)
LEAKED_RAW = """activism
activists
advocacy
advocate
advocates
barrier
barriers
biased
Biased toward
biases
Biases towards
bipoc
black and latinx
community diversity
community equity
cultural differences
cultural heritage
culturally responsive
culturally responsive
disabilities disability
discriminated
discrimination
discriminatory
diverse backgrounds
diverse backgrounds
diverse communities
diverse community
diverse group
diverse groups
diversified
diversify
diversifying
diversity and inclusion
diversity
equity
enhance the diversity
enhancing diversity
equal opportunity
equality
equitable
equity
ethnicity
excluded
female
females
fostering inclusivity
gender
gender diversity
genders
hate speech
excluded
female
females
fostering inclusivity
gender
gender diversity
genders
hate
speech
hispanic
minority
historically
implicit bias
implicit biases
inclusion
inclusive
inclusiveness
inclusivity
Increase diversity
increase the diversity
indigenous community
inequalities
inequality
inequitable
inequities
institutional
lgbt
marginalize
marginalized
minorities
minority
multicultural
multicultural
polarization
political
prejudice
privileges
promoting
diversity
race and ethnicity
racial
racial diversity
racial inequality
racial justice
racially
racism
sense of belonging
sexual preferences
social justice
socio cultural
socio economic
sociocultural
socioeconomic status
stereotypes
systemic
trauma
under appreciated
under represented
under served
underrepresentation
underrepresented
underserved
undervalued
victim
women
women and underrepresented
advocate
advocates
antiracist
barrier
barriers
biased
biases
bipoc
community
diversity
disabilities
disability
discrimination
discriminatory"""

# Existing list pulled from app.py BANNED_WORDS set
EXISTING_RAW = {
    'activism', 'activist', 'activists', 'advance diversity', 'advance inclusivity',
    'advance the diversity', 'advancing diversity', 'advancing inclusive', 'advocacy',
    'advocate', 'advocates', 'affirmative action', 'alliance for diversity', 'ally',
    'allyship', 'antiracist', 'background inclusivity', 'barrier', 'barriers',
    'bias toward', 'bias towards', 'biased', 'biased toward', 'biased towards',
    'biases', 'biases toward', 'biases towards', 'bicultural', 'bipoc', 'bl cultural',
    'black and latinx', 'black cultural', 'black culture', 'black cultures',
    'broaden diversity', 'broaden the diversity', 'clean energy', 'climate action',
    'climate change', 'climate conscious', 'climate consciousness', 'climate equality',
    'climate equity', 'climate injustice', 'climate injustices', 'climate justice',
    'climate justices', 'climate research', 'commitment to diversity',
    'community diversity', 'community equity', 'community inclusivity',
    'cultural activism', 'cultural activist', 'cultural activists', 'cultural advocacy',
    'cultural advocate', 'cultural and ethnic', 'cultural and racial',
    'cultural appropriation', 'cultural appropriations', 'cultural bias',
    'cultural competency', 'cultural connections', 'cultural differences',
    'cultural heritage', 'cultural humility', 'cultural inequalities',
    'cultural inequality', 'cultural inequities', 'cultural inequity',
    'cultural injustice', 'cultural injustices', 'cultural justice',
    'cultural relevance', 'cultural segregation', 'culturally attuned',
    'culturally biased', 'culturally responsive', 'culturally sensitive',
    'culturally sustainable', 'culturally sustaining', 'culture and ethnicity',
    'culture and race', 'cultures and ethnicities', 'cultures and races',
    'de colonization', 'de colonize', 'de colonized', 'de colonizing',
    'de segregate', 'de segregated', 'de segregates', 'de segregation',
    'decolonization', 'decolonize', 'decolonized', 'decolonizing', 'dei', 'deij',
    'desegregate', 'desegregated', 'desegregates', 'desegregation', 'disabilities',
    'disability', 'discriminate', 'discriminated', 'discrimination', 'discriminatory',
    'diverse background', 'diverse backgrounds', 'diverse communities',
    'diverse community', 'diverse group', 'diverse groups', 'diverse individual',
    'diverse individuals', 'diverse status', 'diverse statuses', 'diverse voices',
    'diversified', 'diversify', 'diversifying', 'diversity and equity',
    'diversity and inclusion', 'diversity and inclusivity', 'diversity awareness',
    'diversity equity', 'divisiveness', 'eco cultural', 'ecocultural',
    'ehance the diversity', 'ehancing diversity', 'emphasis on diversity',
    'emphasize diversity', 'emphasizing diversity', 'encourage diversity',
    'encouraging diversity', 'enhance diversity', 'enhance the diversity',
    'enhancing diversity', 'environment conscious', 'environment consciousness',
    'environmental conscious', 'environmental consciousness',
    'environmental equality', 'environmental equity', 'environmental governance',
    'environmental justice', 'environmental social', 'environmentally conscious',
    'environmentalsocial', 'equal opportunities', 'equal opportunity', 'equalities',
    'equality', 'equitable', 'equitable and inclusive', 'equities', 'equity', 'esg',
    'esg effort', 'esg efforts', 'esg initiative', 'esg initiatives',
    'ethnic and cultural', 'ethnic cultural', 'ethnic culture', 'ethnic cultures',
    'ethnic diversity', 'ethnic equity', 'ethnicities and cultures', 'ethnicity',
    'ethnicity and culture', 'excluded', 'exclusion', 'exclusive',
    'feel seen and heard', 'female', 'females', 'foster diversity',
    'fostering diversity', 'fostering inclusive', 'fostering inclusivity',
    'fostering the diversity', 'gender', 'gender diversity', 'genders',
    'green infrastructure', 'green new deal', 'green society', 'group equity',
    'group inclusivity', 'hate speech', 'hispanic cultural', 'hispanic culture',
    'hispanic cultures', 'hispanic minority', 'hispanic people', 'hispanic person',
    'hispanic voices', 'historical racism', 'historically', 'historically racist',
    'historically white', 'implicit bias', 'implicit biased', 'implicit biases',
    'inclusion', 'inclusive', 'inclusiveness', 'inclusivity', 'increase diversity',
    'increase the diversity', 'indigenous communities', 'indigenous community',
    'indigenous individual', 'indigenous individuals', 'indigenous minorities',
    'indigenous minority', 'indigenous people', 'indigenous person',
    'indigenous voices', 'inequalities', 'inequality', 'inequitable', 'inequities',
    'injustice', 'injustices', 'institutional', 'institutional racism',
    'institutional/zed racism', 'institutionalize', 'institutionalized',
    'institutionally', 'institutionally racist', 'inter racial', 'inter racially',
    'intergenerational trauma', 'interracial', 'interracially', 'intersectional',
    'intersectionality', 'latina communities', 'latina community',
    'latina individual', 'latina individuals', 'latina minorities', 'latina minority',
    'latina people', 'latina person', 'latina voices', 'latinx communities',
    'latinx community', 'latinx individual', 'latinx individuals',
    'latinx minorities', 'latinx minority', 'latinx people', 'latinx person',
    'latinx voices', 'lgbt', 'marginalization', 'marginalize', 'marginalized',
    'micro aggression', 'micro aggressions', 'micro aggressive',
    'micro aggressiveness', 'microaggression', 'microaggressions', 'microaggressive',
    'microaggressiveness', 'minorities', 'minority', 'multi ethnic',
    'multi ethnically', 'multicultural', 'multiethnic', 'multiethnically',
    'net zero', 'netzero', 'non black', 'non white', 'nonblack', 'nonwhite',
    'oppressed', 'oppression', 'oppressive', 'oppressiveness', 'people of color',
    'poc', 'pocx', 'polarization', 'polarize', 'political', 'politicization',
    'politicize', 'predominately white', 'prejudice', 'prejudices', 'primarily white',
    'priviledges', 'privilege', 'privileged', 'privileged white', 'privileges',
    'pro black', 'pro white', 'prob lack', 'promoting diversity', 'race and culture',
    'race and ethnicity', 'race based', 'racebased', 'races and cultures',
    'races and ethnicities', 'racial', 'racial and cultural', 'racial and ethnic',
    'racial bias', 'racial biases', 'racial disparities', 'racial disparity',
    'racial diversity', 'racial identity', 'racial inequalities', 'racial inequality',
    'racial inequities', 'racial inequity', 'racial injustice', 'racial injustices',
    'racial justice', 'racial minorities', 'racial minority', 'racial oppression',
    'racial prejudice', 'racial prejudices', 'racial segregation',
    'racial socialization', 'racial solidarity', 'racial stereotypes',
    'racial violence', 'racially', 'racially and culturally', 'racially bias',
    'racially biased', 'racially oppressed', 'racism', 'racist', 'reparation',
    'reparations', 'safe space', 'safe spaces', 'segregated',
    'segregated ethnicities', 'segregated ethnicity', 'segregated race',
    'segregated races', 'segregation', 'sense of belonging',
    'sense of belongingness', 'sexual preferences', 'social environmental',
    'social justice', 'socialenvironmental', 'socio cultural', 'socio economic',
    'sociocultural', 'socioeconomic', 'status', 'statuses', 'stereotype',
    'stereotypes', 'stereotypical', 'stereotyping', 'structural racism',
    'structurally racist', 'system of oppression', 'systematic oppression',
    'systematically oppressed', 'systemic', 'systemic oppression', 'systemic racism',
    'systemical', 'systemically', 'systemically oppressed', 'systemically racist',
    'systems of oppression', 'systems of power', 'tokenistic', 'tokensim',
    'trans ethnic', 'transethnic', 'trauma', 'traumatic', 'under appreciated',
    'under appreciation', 'under privilege', 'under privileged',
    'under representation', 'under represented', 'under served', 'under serving',
    'under valued', 'under valuing', 'underappreciated', 'underappreciation',
    'underprivilege', 'underprivileged', 'underrepresentation', 'underrepresented',
    'underserved', 'underserving', 'undervalued', 'undervaluing',
    'unequal opportunities', 'unequal opportunity', 'unjust', 'victim', 'victimhood',
    'victimized', 'victims', 'voices are acknowledged', 'voices heard',
    'voices matter', 'welcoming environment', 'white colonialism',
    'white colonization', 'white colonizer', 'white colonizers', 'white fragility',
    'white historically', 'white nationalism', 'white nationalist', 'white people',
    'white person', 'white privilege', 'white serving', 'white supremacy',
    'whiteness', 'women', 'women and underrepresented'
}


def clean_leaked(raw: str) -> list:
    """Normalize the leaked dump: lowercase, strip, fix OCR splits, dedupe."""
    lines = [ln.strip().lower() for ln in raw.split('\n') if ln.strip()]

    # Fix "disabilities disability" run-together
    fixed = []
    for ln in lines:
        if ln == 'disabilities disability':
            fixed.extend(['disabilities', 'disability'])
        else:
            fixed.append(ln)

    # Reassemble known OCR-split phrases (X line followed immediately by Y line = "X Y")
    # Only apply when the joined phrase makes more sense than either alone in the NSF context.
    reassembly = [
        ('hate', 'speech', 'hate speech'),
        ('hispanic', 'minority', 'hispanic minority'),
        ('promoting', 'diversity', 'promoting diversity'),
    ]
    out = []
    i = 0
    while i < len(fixed):
        merged = False
        for a, b, joined in reassembly:
            if fixed[i] == a and i + 1 < len(fixed) and fixed[i + 1] == b:
                out.append(joined)
                i += 2
                merged = True
                break
        if not merged:
            out.append(fixed[i])
            i += 1

    # Dedupe preserving order
    seen = set()
    deduped = []
    for term in out:
        if term not in seen:
            seen.add(term)
            deduped.append(term)
    return deduped


def main():
    leaked_clean = clean_leaked(LEAKED_RAW)
    existing_clean = sorted({e.lower() for e in EXISTING_RAW})

    print(f"Leaked (cleaned, deduped): {len(leaked_clean)} terms")
    print(f"Existing (cleaned, deduped): {len(existing_clean)} terms")

    leaked_set = set(leaked_clean)
    existing_set = set(existing_clean)
    union = sorted(leaked_set | existing_set)

    entries = []
    for term in union:
        in_l = term in leaked_set
        in_e = term in existing_set
        source = 'both' if (in_l and in_e) else ('leaked' if in_l else 'existing')
        entries.append({'term': term, 'source': source})

    counts = {
        'leaked_only': sum(1 for e in entries if e['source'] == 'leaked'),
        'existing_only': sum(1 for e in entries if e['source'] == 'existing'),
        'both': sum(1 for e in entries if e['source'] == 'both'),
        'total': len(entries),
    }
    print(f"\nUnion: {counts['total']} unique terms")
    print(f"  leaked-only: {counts['leaked_only']}")
    print(f"  existing-only: {counts['existing_only']}")
    print(f"  in both: {counts['both']}")

    print("\nLeaked-only terms (NSF-flagged that existing list missed):")
    for e in entries:
        if e['source'] == 'leaked':
            print(f"  - {e['term']}")

    data = {
        'version': '2.0.0',
        'last_updated': '2026-05-17',
        'source_note': (
            'Merged from (1) leaked NSF decision-tree word list and '
            '(2) community-compiled list from banned-word-checker v1. '
            'Provenance marked per-term: leaked = appears in NSF source, '
            'existing = community-added defensively, both = appears in both.'
        ),
        'counts': counts,
        'terms': entries,
    }

    out_path = os.path.join(REPO, 'data', 'banned-words.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {out_path}")


if __name__ == '__main__':
    sys.exit(main())
