#!/usr/bin/env python3
"""
Knowledge Base Module for Fuzzy Search
Contains mock documents for insurance, medications, and billing information.
"""

from rapidfuzz import fuzz
from typing import List, Dict


# Mock document chunks organized by category
KNOWLEDGE_BASE = {
    "insurance": [
        {
            "id": "ins_001",
            "title": "PPO vs HMO Coverage Differences",
            "content": "PPO (Preferred Provider Organization) plans let you see any doctor without a referral and cover out-of-network care at a higher cost. HMO (Health Maintenance Organization) plans require you to choose a primary care physician and get referrals for specialists, but usually have lower premiums and copays. PPO plans offer more flexibility while HMO plans offer more predictable costs.",
            "category": "insurance"
        },
        {
            "id": "ins_002",
            "title": "Specialist Referral Requirements",
            "content": "HMO plans require a referral from your primary care physician before seeing a specialist. PPO and EPO plans typically don't require referrals, allowing you to see specialists directly. Without a required referral in an HMO plan, the visit may not be covered by insurance.",
            "category": "insurance"
        },
        {
            "id": "ins_003",
            "title": "Emergency Room Coverage and Copays",
            "content": "Emergency room visits are covered by most insurance plans when you have a true medical emergency. Typical ER copays range from $150-$500 depending on your plan. If your condition is not deemed a true emergency, your insurance may not cover the full cost. Urgent care centers are a less expensive alternative for non-emergency situations.",
            "category": "insurance"
        },
        {
            "id": "ins_004",
            "title": "Out-of-Network Provider Policies",
            "content": "Out-of-network providers are doctors or facilities not contracted with your insurance plan. PPO plans typically cover out-of-network care but at higher costs with larger deductibles and copays. HMO plans usually don't cover out-of-network care except in emergencies. Always check if a provider is in-network before scheduling to avoid unexpected costs.",
            "category": "insurance"
        },
        {
            "id": "ins_005",
            "title": "Prescription Drug Coverage Tiers",
            "content": "Most insurance plans use a tier system for prescription coverage. Tier 1 drugs (generic) have the lowest copay, usually $10-20. Tier 2 drugs (preferred brand-name) cost more, typically $30-50. Tier 3 drugs (non-preferred brand-name) have higher copays of $60-100. Tier 4 specialty drugs can cost hundreds of dollars or require coinsurance of 20-40%.",
            "category": "insurance"
        },
        {
            "id": "ins_006",
            "title": "Preventive Care Coverage",
            "content": "Most insurance plans cover preventive care services at no cost to you when you use in-network providers. This includes annual physicals, vaccinations, cancer screenings, and well-child visits. Preventive care is covered even if you haven't met your deductible. Check your plan's specific list of covered preventive services.",
            "category": "insurance"
        },
    ],
    "medications": [
        {
            "id": "med_001",
            "title": "Statin Side Effects",
            "content": "Statins are cholesterol-lowering medications that can cause muscle pain or weakness in some people. Other common side effects include headache, nausea, and digestive problems. Rarely, statins can cause liver damage or memory problems. Contact your doctor if you experience unexplained muscle pain, dark urine, or yellowing of skin or eyes.",
            "category": "medications"
        },
        {
            "id": "med_002",
            "title": "Blood Pressure Medication Side Effects",
            "content": "Blood pressure medications can cause dizziness or lightheadedness, especially when standing up quickly. ACE inhibitors may cause a dry cough in some patients. Diuretics can increase urination and may affect potassium levels. Beta-blockers might cause fatigue or cold hands and feet. Report persistent side effects to your doctor.",
            "category": "medications"
        },
        {
            "id": "med_003",
            "title": "Common Drug Interactions",
            "content": "Some medications can interact with each other or with certain foods. Blood thinners like warfarin interact with vitamin K-rich foods and many other medications. NSAIDs like ibuprofen can reduce the effectiveness of blood pressure medications. Grapefruit juice affects the metabolism of many drugs including statins and some blood pressure medications. Always tell your doctor and pharmacist about all medications and supplements you take.",
            "category": "medications"
        },
        {
            "id": "med_004",
            "title": "Taking Medications With or Without Food",
            "content": "Some medications work best on an empty stomach, while others should be taken with food to reduce stomach upset. Thyroid medications like levothyroxine should be taken on an empty stomach at least 30 minutes before eating. Pain relievers like ibuprofen should be taken with food to protect your stomach. Always follow the specific instructions on your prescription label.",
            "category": "medications"
        },
        {
            "id": "med_005",
            "title": "Medication Storage Requirements",
            "content": "Most medications should be stored at room temperature in a dry place away from light and moisture. The bathroom medicine cabinet is actually a poor storage location due to humidity. Some medications like insulin require refrigeration. Never store medications where children can reach them. Check expiration dates regularly and dispose of expired medications properly.",
            "category": "medications"
        },
        {
            "id": "med_006",
            "title": "What to Do If You Miss a Dose",
            "content": "If you miss a medication dose, take it as soon as you remember unless it's almost time for your next dose. Never take a double dose to make up for a missed one. For birth control pills or critical medications, follow the specific instructions provided with your prescription. Set phone reminders or use a pill organizer to help remember your medications.",
            "category": "medications"
        },
        {
            "id": "med_007",
            "title": "Antibiotic Use and Resistance",
            "content": "Antibiotics only work against bacterial infections, not viruses like colds or flu. Always complete the full course of antibiotics even if you feel better. Stopping early can allow bacteria to survive and become resistant. Overuse of antibiotics contributes to antibiotic resistance, making infections harder to treat. Never share antibiotics or use leftover antibiotics from a previous illness.",
            "category": "medications"
        },
        {
            "id": "med_008",
            "title": "Generic vs Brand Name Medications",
            "content": "Generic medications contain the same active ingredients as brand-name drugs and work the same way. They must meet the same FDA standards for safety, quality, and effectiveness. Generic drugs are usually much cheaper than brand names because manufacturers don't have to repeat the original research. Your doctor can specify if a brand name is medically necessary.",
            "category": "medications"
        },
    ],
    "billing": [
        {
            "id": "bill_001",
            "title": "Copay vs Deductible Explained",
            "content": "A copay is a fixed amount you pay for a covered service, like $30 for a doctor visit. A deductible is the amount you must pay out-of-pocket before your insurance starts covering costs. Copays usually count toward your out-of-pocket maximum but may not count toward your deductible. After meeting your deductible, you typically still pay copays or coinsurance.",
            "category": "billing"
        },
        {
            "id": "bill_002",
            "title": "Understanding Coinsurance",
            "content": "Coinsurance is the percentage of costs you pay after meeting your deductible. For example, with 80/20 coinsurance, your insurance pays 80% and you pay 20%. Coinsurance applies until you reach your out-of-pocket maximum for the year. Once you hit that maximum, your insurance covers 100% of covered services.",
            "category": "billing"
        },
        {
            "id": "bill_003",
            "title": "Payment Plan Options",
            "content": "Most healthcare providers offer payment plans for large medical bills. You can typically arrange interest-free monthly payments by contacting the billing department. Payment plans usually require a down payment and automatic monthly payments from your bank account. Setting up a payment plan helps avoid collections and protects your credit score.",
            "category": "billing"
        },
        {
            "id": "bill_004",
            "title": "How to Dispute a Medical Bill",
            "content": "If you believe a medical bill is incorrect, first request an itemized bill to review all charges. Compare the bill to your Explanation of Benefits (EOB) from your insurance. Contact the provider's billing department to discuss any errors or charges you don't understand. You can also file an appeal with your insurance company if they denied coverage you believe should be covered.",
            "category": "billing"
        },
        {
            "id": "bill_005",
            "title": "Insurance Claim Submission Process",
            "content": "Most providers submit insurance claims directly to your insurance company on your behalf. Claims must typically be submitted within 90-180 days of the service date. The insurance processes the claim and sends an Explanation of Benefits showing what they covered. You'll receive a bill for any remaining balance after insurance payment.",
            "category": "billing"
        },
        {
            "id": "bill_006",
            "title": "Financial Assistance Programs",
            "content": "Many hospitals and healthcare systems offer financial assistance or charity care for patients who can't afford their medical bills. You may qualify based on your income and family size. Nonprofit hospitals are required by law to have financial assistance policies. Contact the hospital's billing department or financial counselor to ask about available programs and how to apply.",
            "category": "billing"
        },
        {
            "id": "bill_007",
            "title": "Understanding Your Explanation of Benefits",
            "content": "An Explanation of Benefits (EOB) is not a bill but a statement from your insurance showing what they paid. It lists the service provided, the provider's charge, the negotiated rate, what insurance paid, and what you owe. The patient responsibility section shows your copay, deductible, or coinsurance amounts. Keep EOBs to compare with bills and track your deductible progress.",
            "category": "billing"
        },
    ]
}


def get_all_documents() -> List[Dict]:
    """Get all documents from the knowledge base as a flat list."""
    all_docs = []
    for category_docs in KNOWLEDGE_BASE.values():
        all_docs.extend(category_docs)
    return all_docs


def fuzzy_search_knowledge(
    query: str,
    top_k: int = 3,
    threshold: float = 60.0
) -> List[Dict]:
    """
    Search knowledge base using fuzzy string matching.
    
    Args:
        query: The search query string
        top_k: Maximum number of results to return
        threshold: Minimum similarity score (0-100) for results
    
    Returns:
        List of matching documents with scores, sorted by relevance
    """
    if not query or not query.strip():
        return []
    
    query = query.strip().lower()
    all_docs = get_all_documents()
    
    # Calculate fuzzy match scores for each document
    scored_docs = []
    for doc in all_docs:
        # Search against both title and content
        title_score = fuzz.partial_ratio(query, doc["title"].lower())
        content_score = fuzz.partial_ratio(query, doc["content"].lower())
        
        # Use the maximum score
        max_score = max(title_score, content_score)
        
        if max_score >= threshold:
            scored_docs.append({
                "document": doc,
                "score": max_score,
                "match_type": "title" if title_score > content_score else "content"
            })
    
    # Sort by score (highest first) and return top K
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs[:top_k]

