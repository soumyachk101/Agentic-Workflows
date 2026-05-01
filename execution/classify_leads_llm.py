import os
import json
import argparse
import asyncio
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def classify_lead(client, lead, classification_type):
    """
    Classifies a single lead using Anthropic
    """
    # Create a concise lead summary for the LLM
    lead_summary = {
        "name": lead.get("name", "N/A"),
        "description": lead.get("description", "N/A"),
        "industry": lead.get("industry", "N/A"),
        "website": lead.get("website", "N/A")
    }

    prompt = f"""
    Classify the following business lead based on the criteria: {classification_type}

    Lead Info:
    {json.dumps(lead_summary, indent=2)}

    Output ONLY a JSON object with:
    - "match": boolean (true if it matches the criteria)
    - "confidence": float (0.0 to 1.0)
    - "reason": string (brief explanation)
    """

    try:
        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse the JSON response
        result_text = response.content[0].text.strip()
        # Clean up in case of markdown formatting
        if result_text.startswith("```json"):
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        
        return json.loads(result_text)
    except Exception as e:
        print(f"⚠️ Classification error for {lead.get('name')}: {str(e)}")
        return {"match": False, "confidence": 0, "reason": "Error during classification"}

async def classify_leads(leads, classification_type, batch_size=5):
    """
    Classifies a list of leads in batches
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found.")
        return leads

    client = AsyncAnthropic(api_key=api_key)
    
    classified_leads = []
    print(f"🧠 Classifying {len(leads)} leads for '{classification_type}'...")

    for i in range(0, len(leads), batch_size):
        batch = leads[i:i+batch_size]
        tasks = [classify_lead(client, lead, classification_type) for lead in batch]
        results = await asyncio.gather(*tasks)
        
        for lead, result in zip(batch, results):
            lead["classification_match"] = result.get("match")
            lead["classification_confidence"] = result.get("confidence")
            lead["classification_reason"] = result.get("reason")
            classified_leads.append(lead)
        
        print(f"✅ Processed {min(i+batch_size, len(leads))}/{len(leads)} leads...")

    return classified_leads

def main():
    parser = argparse.ArgumentParser(description="Classify leads using AI")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--classification_type", required=True, help="Description of what to match (e.g. 'Software Agency')")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Load leads
    with open(args.input, "r") as f:
        leads = json.load(f)

    # Run async classification
    classified_leads = asyncio.run(classify_leads(leads, args.classification_type))

    # Save results
    with open(args.output, "w") as f:
        json.dump(classified_leads, f, indent=2)
    
    print(f"💾 Classified leads saved to {args.output}")

if __name__ == "__main__":
    main()
