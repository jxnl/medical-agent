# Search Implementation Guide

## Overview

The knowledge base search feature provides fuzzy search across insurance policies, medication guides, and billing information. It uses RapidFuzz for string matching and returns confidence-scored results to help the agent provide relevant information or recognize when to escalate.

## Architecture

### Components

1. **Knowledge Base Module** (`src/knowledge_base.py`)
   - Contains mock document chunks organized by category
   - Implements `fuzzy_search_knowledge()` function
   - Uses RapidFuzz for partial string matching

2. **Search Tool** (`src/telehealth_service.py`)
   - MCP tool `search_knowledge_base` callable by the agent
   - Formats results with confidence indicators
   - Returns structured data for agent interpretation

3. **System Prompt** (`src/telehealth_service.py`)
   - Guides agent on when to use search
   - Explains how to interpret confidence scores
   - Specifies escalation criteria

## Document Categories

### Insurance (6 documents)
- PPO vs HMO coverage differences
- Specialist referral requirements
- Emergency room coverage and copays
- Out-of-network provider policies
- Prescription drug coverage tiers
- Preventive care coverage

### Medications (8 documents)
- Statin side effects
- Blood pressure medication side effects
- Common drug interactions
- Taking medications with or without food
- Medication storage requirements
- What to do if you miss a dose
- Antibiotic use and resistance
- Generic vs brand name medications

### Billing (7 documents)
- Copay vs deductible explained
- Understanding coinsurance
- Payment plan options
- How to dispute a medical bill
- Insurance claim submission process
- Financial assistance programs
- Understanding explanation of benefits

## Expected Behavior

### Confidence Score Ranges

**High Confidence (85-100)**
- Strong semantic or keyword match
- Agent should present information confidently
- Example: "What's the difference between PPO and HMO?" matches PPO/HMO document

**Good Match (70-84)**
- Reasonable match with some uncertainty
- Agent should present as general information
- Example: "How do I handle medication" matches storage or dosage docs

**Partial Match (60-69)**
- Weak match, potentially relevant
- Agent should share cautiously and offer escalation
- Example: "coverage" might match multiple insurance docs

**No Match (< 60)**
- No relevant information found
- Tool returns "no_results: true"
- Agent should escalate to human

### Search Tool Response Format

```python
{
    "content": [{
        "type": "text",
        "text": "Formatted results with confidence indicators"
    }],
    "results_count": 3,  # Number of results returned
    "top_score": 95.0,   # Highest match score
    "no_results": False  # True if no matches found
}
```

## Failure Modes and Edge Cases

### 1. Ambiguous Queries

**Problem:** Query is too vague and matches many documents

**Example:**
- "coverage" → matches multiple insurance documents
- "medications" → matches all medication documents

**Expected Behavior:**
- Search returns multiple partial matches
- Agent should ask for clarification
- "What specific type of coverage are you asking about?"

**How to Detect:**
- Multiple results with similar scores
- Generic single-word queries
- No clear top match

### 2. Over-Specific Queries

**Problem:** Query asks for account-specific or personalized information

**Examples:**
- "Does my plan cover acupuncture?"
- "What's my deductible amount?"
- "Is Dr. Johnson in my network?"

**Expected Behavior:**
- Search may return general information about coverage
- Agent recognizes need for personal data
- Agent escalates to someone with account access

**How to Detect:**
- Query contains "my", "I", or "me"
- Asks for specific dollar amounts, dates, or personal details
- Requires database lookup or account records

### 3. Typos and Misspellings

**Problem:** User makes spelling errors in query

**Examples:**
- "side affects of cholestrol meds" (affects→effects, cholestrol→cholesterol)
- "ppo vs hmo" (informal abbreviations)
- "disputing bills" (different word form)

**Expected Behavior:**
- Fuzzy matching handles moderate typos
- Partial ratio matching catches variations
- Should still return relevant documents

**How to Handle:**
- RapidFuzz's partial_ratio is tolerant of errors
- Threshold of 60 allows some fuzzy matches
- Agent presents results normally

### 4. Multi-Topic Queries

**Problem:** Query spans multiple categories

**Examples:**
- "insurance and billing questions"
- "medication coverage and copays"

**Expected Behavior:**
- Search may return mixed category results
- Agent should address what it can
- Offer to break down into specific questions

**How to Detect:**
- Multiple high-scoring results from different categories
- Conjunctions like "and", "plus", "also"

### 5. Context-Dependent Questions

**Problem:** Question requires patient history or medical context

**Examples:**
- "Should I take this medication with food?"
- "Will this interact with my other medications?"
- "Is this side effect normal for me?"

**Expected Behavior:**
- Search returns general guidance
- Agent recognizes need for personalized advice
- Agent escalates to healthcare provider

**How to Detect:**
- Query implies decision-making about patient care
- Asks "should I" or seeks medical advice
- References patient's specific situation

### 6. Out-of-Scope Questions

**Problem:** Query is completely unrelated to knowledge base

**Examples:**
- "When is my appointment?" (should use appointment tools)
- "I need a prescription refill" (should use prescription tools)
- "What's the weather?" (completely unrelated)

**Expected Behavior:**
- Search returns no results (score < 60)
- Agent recognizes different intent
- Agent uses appropriate tools or clarifies intent

**How to Detect:**
- No matches above threshold
- Keywords suggest different tool needed
- Query format doesn't match knowledge base content

## Agent Decision Making

### When to Use Search

The agent should use `search_knowledge_base` for:
- Questions about insurance terminology and policies
- General medication information (side effects, storage, etc.)
- Billing and payment process questions
- Educational or explanatory requests

### When to Escalate After Search

The agent should escalate when:

1. **No Results Found**
   - Search returns no_results: true
   - Information might be outside knowledge base

2. **Low Confidence Match**
   - Top score < 70
   - Results don't clearly answer the question

3. **Personal Information Needed**
   - Search returns general info but user needs specifics
   - Query contains possessive pronouns (my, our)
   - Asks for account balances, dates, or personal records

4. **Medical Advice Required**
   - Question requires clinical judgment
   - User asking "should I" about medical decisions
   - Concerns about symptoms or side effects

5. **Multiple Low-Confidence Results**
   - Many results with similar low scores
   - Unclear which is most relevant
   - User needs expert to sort through options

### Best Practices for Agent

1. **Always Cite Source Category**
   - "According to our insurance information..."
   - "Our medication guides explain..."

2. **Include Confidence in Language**
   - High confidence: "Here's information about..."
   - Good match: "Based on general information..."
   - Partial match: "I found some related information, though it might not be exactly what you need..."

3. **Offer Follow-Up Options**
   - "Does this answer your question?"
   - "Would you like me to connect you with someone for your specific situation?"

4. **Never Make Up Information**
   - Only use what's in search results
   - If unsure, escalate rather than guess

5. **Recognize Limitations**
   - "This is general information"
   - "For your specific plan/situation, I'll need to connect you with..."

## Testing Strategy

### Unit Tests

Test `fuzzy_search_knowledge()` function:
- Exact matches return high scores
- Typos still return good matches
- Irrelevant queries return low scores
- Category filtering works correctly

### Integration Tests

Test `search_knowledge_base` tool:
- Formats results correctly
- Handles empty queries
- Returns proper confidence indicators
- Sets no_results flag appropriately

### Behavioral Tests

Test agent decision-making:
- Uses search for appropriate queries
- Provides information for high-confidence matches
- Escalates for account-specific questions
- Handles ambiguous queries with clarification

## Performance Considerations

### Optimization

- Documents are pre-loaded in memory (acceptable for ~20 documents)
- RapidFuzz is fast enough for real-time search
- No external API calls needed

### Scalability

For larger knowledge bases:
- Consider vector embeddings (e.g., Sentence Transformers)
- Add caching for frequent queries
- Implement document indexing
- Consider external search engine

## Future Enhancements

1. **Semantic Search**
   - Use embeddings for better understanding
   - Catch conceptual matches beyond keywords

2. **Query Expansion**
   - Automatically handle synonyms
   - Expand abbreviations

3. **Result Ranking**
   - Combine multiple scoring methods
   - Learn from user feedback

4. **Category Filtering**
   - Allow agent to specify category
   - Improve precision for specific domains

5. **Document Updates**
   - Load documents from external source
   - Support dynamic knowledge base updates
   - Version control for documents

