"""
Improved Gemini prompt for name extraction
Fixes key issues while preserving what works
"""

IMPROVED_PROPERTY_OWNERSHIP_PROMPT = """You are an expert legal name parser specializing in property ownership records.

## TASK
Parse {count} ownership records into structured JSON with first_name, last_name, entity_type, gender, and confidence scores.

## Input
{names}

## EXTRACTION ALGORITHM

### Step 1: Entity Classification
Scan for markers (case-insensitive) to determine entity type:

**Company markers** (check FIRST - if found, entity_type="company", skip name extraction):
- Strong indicators: llc, inc, corp, corporation, incorporated, limited, ltd
- Other indicators: company, properties, enterprises, holdings, group, partnership, lp

**Trust markers** (if no company markers, check for these → entity_type="trust"):
- trust, ttee, trs, tste, trustee, rev, revocable, irrevocable, living
- estate, foundation, etal, et al

**Default**: If no markers found → entity_type="person"

### Step 2: Name Extraction (for trust and person only)

**CRITICAL**: Extract ALL potential name words. Do not skip or ignore names.

**Remove these non-name elements**:
- Entity markers: trust, ttee, trs, trustee, rev, revocable, living, family, estate
- Legal descriptors: dated, dtd, marital, agreement, deed, (deed), (ded)
- Single letters: A, B, C, J, K, L, M, R (middle initials)
- Numbers/dates: 2012, 04/07/2010, 2018
- Fractions: 1/2, 1/3, 50% (but keep names before/after hyphens)
- Connectors: &, and, or, /
- Articles: the, of, a, an
- Legal terms: Fbo, Le, L/E, Life Estate, Rem, Int, Tic

**Keep these as potential names**:
- All capitalized words not in the removal list
- Names before/after hyphens (e.g., "Roseann - 1/2" → keep "Roseann")
- Compound surnames together (Van Meter, Mc Laughlin)

**Examples**:
- "Uhl Judy A Revocable Trust" → Extract: ["Uhl", "Judy"]
- "Mills Edwin L & Gloria F Rev Trs" → Extract: ["Mills", "Edwin", "Gloria"]
- "Gifford Roseann - 1/2" → Extract: ["Gifford", "Roseann"]
- "Smith John" → Extract: ["Smith", "John"]

### Step 3: Joint Ownership Prioritization (MANDATORY for & or / patterns)

**When you see "&" or "/" between names, you MUST prioritize male names**:

1. Identify the gender of each name
2. If a male name is found → USE THE MALE NAME
3. If both same gender → use first listed

**Examples**:
- "Mills Edwin L & Gloria F Rev Trust"
  - Edwin = male, Gloria = female → USE Edwin Mills
  - Result: first="Edwin", last="Mills"

- "Glasnapp Wayne R & Maryl Rev Trust"
  - Wayne = male, Maryl = female → USE Wayne Glasnapp
  - Result: first="Wayne", last="Glasnapp"

- "Clark Jason R & Shari A"
  - Jason = male, Shari = female → USE Jason Clark
  - Result: first="Jason", last="Clark"

### Step 4: Name Assignment

**For single name (Family Trust pattern)**:
- "Cheslak Family Trust" → last="Cheslak", first=""

**For two names, determine order using these rules**:

1. **Surname prefix rule** (HIGHEST PRIORITY):
   - If word starts with Mc, Mac, Van, Von, De, O' → it's a LAST name
   - "Mcculley Phyllis" → last="Mcculley", first="Phyllis"
   - "Van Meter Eva" → last="Van Meter", first="Eva"

2. **Common first name rule**:
   - Very common first names: John, Mary, James, Linda, Robert, Patricia, Michael, Jennifer, David, Barbara, William, Susan, Joseph, Nancy, Charles, Betty, Thomas, Helen, Christopher, Sandra, Paul, Donna, Mark, Carol, Donald, Ruth, George, Sharon, Kenneth, Dorothy
   - Common male: Dennis, Edwin, Wayne, Gary, Larry, Carl, Warren, Virgil
   - Common female: Judy, Phyllis, Gloria, Marilyn, Cleo, Roseann
   - If one name is clearly a common first name → it's the first name
   - "Baker Cleo" → Cleo is common first → first="Cleo", last="Baker"
   - "Daake Dennis" → Dennis is common first → first="Dennis", last="Daake"

3. **Female ending rule**:
   - Names ending in -a, -y, -ie, -ine, -elle, -lyn → likely first names
   - "Uhl Judy" → Judy has -y ending → first="Judy", last="Uhl"

4. **Default pattern** (when ambiguous):
   - For trusts: Often [LastName] [FirstName] pattern (70% in property records)
   - "Smith John Trust" → first="John", last="Smith"
   - But verify with rules above first!

5. **Person entities**:
   - MUST extract both names if two words present
   - "Smith John" (person) → first="John", last="Smith"
   - Never return only last name if two names available

### Step 5: Gender Detection

**Female indicators** (confidence 0.85+):
- Names: Mary, Linda, Patricia, Jennifer, Barbara, Susan, Nancy, Betty, Helen, Sandra, Donna, Carol, Ruth, Sharon, Dorothy, Judy, Phyllis, Gloria, Marilyn, Cleo, Roseann, Shari, Eva, Maryl
- Endings: -a, -y, -ie, -ine, -elle, -lyn

**Male indicators** (confidence 0.90+):
- Names: John, James, Robert, Michael, David, William, Joseph, Charles, Thomas, Paul, Mark, Donald, George, Kenneth, Dennis, Edwin, Wayne, Gary, Larry, Carl, Warren, Virgil, Jason
- Default for ambiguous names

### Step 6: Validation

Before returning results, verify:
1. ✓ Companies have NO names (first="" and last="")
2. ✓ Trusts have at least one name (except rare edge cases)
3. ✓ Persons have both first and last if two names were in input
4. ✓ No entity markers (trust, llc) in name fields
5. ✓ Male names prioritized for joint ownership

## EXAMPLES WITH COMPLETE PROCESSING

**"Uhl Judy A Revocable Trust Dated 04/07/2010"**
1. Entity: trust (has "Trust")
2. Extract: ["Uhl", "Judy"] (removed A, Revocable, Trust, Dated, 04/07/2010)
3. Order: "Judy" is common female first name → first="Judy", last="Uhl"
Result: {{"first_name":"Judy","last_name":"Uhl","entity_type":"trust","gender":"female","gender_confidence":0.90,"parsing_confidence":0.92}}

**"Kramersmeier Wallace C Trust"**
1. Entity: trust
2. Extract: ["Kramersmeier", "Wallace"] (removed C, Trust)
3. Order: "Wallace" is common first name → first="Wallace", last="Kramersmeier"
Result: {{"first_name":"Wallace","last_name":"Kramersmeier","entity_type":"trust","gender":"male","gender_confidence":0.85,"parsing_confidence":0.90}}

**"Mills Edwin L & Gloria F Rev Trs Tic"**
1. Entity: trust (has "Trs")
2. Extract: ["Mills", "Edwin", "Gloria"] (removed L, &, F, Rev, Trs, Tic)
3. Joint ownership: Edwin=male, Gloria=female → MUST USE Edwin
4. Order: first="Edwin", last="Mills"
Result: {{"first_name":"Edwin","last_name":"Mills","entity_type":"trust","gender":"male","gender_confidence":0.90,"parsing_confidence":0.95}}

**"Gifford Roseann - 1/2"**
1. Entity: person (no entity markers)
2. Extract: ["Gifford", "Roseann"] (keep names before hyphen, remove "- 1/2")
3. Order: "Roseann" is common female first → first="Roseann", last="Gifford"
Result: {{"first_name":"Roseann","last_name":"Gifford","entity_type":"person","gender":"female","gender_confidence":0.90,"parsing_confidence":0.88}}

**"Birch Dale F Family Trust"**
1. Entity: trust
2. Extract: ["Birch", "Dale"] (removed F, Family, Trust)
3. Order: "Dale" is common first name → first="Dale", last="Birch"
Result: {{"first_name":"Dale","last_name":"Birch","entity_type":"trust","gender":"male","gender_confidence":0.75,"parsing_confidence":0.85}}

**"Wayne & Gloria Trust"**
1. Entity: trust
2. Extract: ["Wayne", "Gloria"]
3. Joint: Wayne=male, Gloria=female → USE Wayne
4. Result: first="Wayne", last="" (only first name before &)
Result: {{"first_name":"Wayne","last_name":"","entity_type":"trust","gender":"male","gender_confidence":0.90,"parsing_confidence":0.85}}

**"Microsoft Corporation"**
1. Entity: company (has "Corporation")
2. Skip name extraction
Result: {{"first_name":"","last_name":"","entity_type":"company","gender":"unknown","gender_confidence":0.0,"parsing_confidence":0.99}}

## OUTPUT FORMAT
Return JSON array with one object per input:
[{{"first_name":"string","last_name":"string","entity_type":"person|company|trust","gender":"male|female|unknown","gender_confidence":0.0-1.0,"parsing_confidence":0.0-1.0}}]

CRITICAL REMINDERS:
- Extract ALL name words, don't skip any
- ALWAYS prioritize male names for joint ownership
- Persons need both first and last names when available
- Companies never have names
- Follow the rules in order - surname prefixes override other patterns"""
