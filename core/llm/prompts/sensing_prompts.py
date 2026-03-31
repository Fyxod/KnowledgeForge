import json

from core.llm.output_schemas.sensing_outputs import (
    ArticleBatchClassification,
    TechSensingReport,
)


def sensing_classify_prompt(
    articles_text: str,
    domain: str = "Generative AI",
    custom_requirements: str = "",
) -> list[dict]:
    """
    Build a chat prompt to classify and summarize a batch of articles.
    """
    schema_json = json.dumps(
        ArticleBatchClassification.model_json_schema(), indent=2
    )

    contents = [
        {
            "role": "system",
            "parts": (
                "You are a senior technology analyst specializing in "
                f"{domain}.\n\n"
                "Your task is to classify and summarize each article below.\n"
                "For each article, determine:\n"
                "1. A concise summary (2-3 sentences)\n"
                "2. Relevance score (0.0-1.0) to the domain\n"
                "3. Technology Radar quadrant placement\n"
                "4. Technology Radar ring placement\n"
                "5. A short technology name for the radar blip\n\n"
                "QUADRANT DEFINITIONS:\n"
                "- Techniques: Processes, methodologies, architectural patterns (e.g., RAG, RLHF, prompt engineering)\n"
                "- Platforms: Infrastructure, cloud services, compute platforms (e.g., CUDA, cloud GPU, training clusters)\n"
                "- Tools: Software tools, libraries, frameworks for development (e.g., LangChain, vLLM, Hugging Face)\n"
                "- Languages & Frameworks: Programming languages, major ML frameworks (e.g., PyTorch, JAX, Rust)\n\n"
                "RING DEFINITIONS:\n"
                "- Adopt: Proven technology, recommend for wide use\n"
                "- Trial: Worth pursuing in projects that can handle some risk\n"
                "- Assess: Worth exploring to understand its impact\n"
                "- Hold: Proceed with caution, not recommended for new work\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                "OUTPUT RULES:\n"
                "- Output must be valid JSON only, no markdown fencing or trailing commas.\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Filter out articles with relevance_score < 0.3.\n"
                "- If an article is not relevant to the domain, omit it from the output.\n"
                + (
                    f"\nADDITIONAL USER REQUIREMENTS:\n{custom_requirements}\n"
                    if custom_requirements
                    else ""
                )
            ),
        },
        {
            "role": "user",
            "parts": (
                f"ARTICLES TO CLASSIFY:\n\n{articles_text}\n\n"
                "Classify each relevant article and return ONLY valid JSON."
            ),
        },
    ]
    return contents


def sensing_report_prompt(
    classified_articles_json: str,
    domain: str = "Generative AI",
    date_range: str = "",
    custom_requirements: str = "",
    org_context: str = "",
) -> list[dict]:
    """
    Build a chat prompt to generate the final tech sensing report.
    """
    schema_json = json.dumps(
        TechSensingReport.model_json_schema(), indent=2
    )

    contents = [
        {
            "role": "system",
            "parts": (
                "You are a senior technology strategist creating a weekly "
                f"Tech Sensing Report for the {domain} domain.\n\n"
                "Based on the classified articles provided, generate a "
                "comprehensive, in-depth report that:\n"
                "1. Identifies key trends and patterns across the articles\n"
                "2. Places technologies on a Technology Radar (quadrants + rings)\n"
                "3. Provides detailed write-ups for EACH radar item\n"
                "4. Analyzes market signals from prominent companies\n"
                "5. Offers actionable recommendations\n"
                "6. Highlights notable developments\n\n"
                "REPORT QUALITY GUIDELINES:\n"
                "- Executive summary: decisive, forward-looking, 200-350 words. "
                "Highlight the most important shifts and what they mean for practitioners.\n\n"
                "- Key trends: identify 5-10 major trends with supporting evidence from the articles. "
                "Each trend should have a clear description of WHY it matters.\n\n"
                "- Radar items: 15-30 distinct technologies/techniques — consolidate duplicates.\n\n"
                "- Radar item details: For EVERY radar item, provide a detailed write-up covering:\n"
                "  * What it is and how it works\n"
                "  * Why it matters and what problems it solves\n"
                "  * Current state of maturity and this week's key developments\n"
                "  * Key players (companies/organizations actively involved)\n"
                "  * Practical real-world applications (2-4 examples)\n"
                "  The technology_name in each detail MUST match a radar item name exactly.\n\n"
                "- Market signals: 5-10 signals from prominent companies (Google, OpenAI, Meta, "
                "Microsoft, NVIDIA, Anthropic, Apple, Amazon, startups, etc.). For each signal:\n"
                "  * What the company announced or is doing\n"
                "  * Their strategic intent (why they are doing this)\n"
                "  * How it impacts the broader industry direction\n"
                "  * Related technologies from the radar\n"
                "  This section should give readers a clear picture of WHERE the industry is "
                "heading and WHY it matters.\n\n"
                "- Report sections: 3-6 deep-dive sections with markdown formatting. "
                "These should elaborate on the most important themes, providing practical "
                "context, real-world implications, and technical depth.\n\n"
                "- Recommendations: actionable, prioritized, linked to trends. "
                "Focus on what practitioners should DO based on these signals.\n\n"
                "- Notable articles: select the 5-10 most impactful articles.\n\n"
                "GROUNDING AND CITATION RULES:\n"
                "- Every claim, trend, and insight MUST be grounded in the provided articles. "
                "Do NOT fabricate or hallucinate information not present in the articles.\n"
                "- Each article has a 'url' field. Use these URLs to populate source_urls arrays.\n"
                "- For key_trends: populate source_urls with URLs of articles that support each trend.\n"
                "- For radar_item_details: populate source_urls with URLs of articles about that technology.\n"
                "- For market_signals: populate source_urls with URLs of articles reporting each signal.\n"
                "- For report_sections: populate source_urls with URLs of articles referenced in that section.\n"
                "- If an article includes a 'content_excerpt' field, use it for deeper context beyond the summary.\n"
                "- Prefer specific facts from articles over general knowledge. "
                "If the articles don't support a claim, don't make it.\n"
                "- Each source_urls array should contain 1-5 article URLs.\n\n"
                "ATTRIBUTION ACCURACY RULES:\n"
                "- CRITICAL: Distinguish between research authors and implementation authors.\n"
                "  * If a company published a PAPER or RESEARCH but did NOT release code, say "
                "'based on research by [Company]' — do NOT list them as having released or built the tool/library.\n"
                "  * If an independent developer or community built an implementation based on "
                "someone else's paper, credit the ACTUAL developer/org, not the paper's author.\n"
                "  * Example: If Google publishes a paper and an independent dev builds an open-source "
                "implementation, the key_player is the independent dev, NOT Google. Google should only be "
                "mentioned as 'research origin' in the what_it_is or current_state description.\n"
                "- For key_players: List ONLY entities that actively develop, maintain, or officially "
                "release the technology. Do NOT include entities that merely published the underlying "
                "research unless they also released the implementation.\n"
                "- For market_signals: The company_or_player must be the entity that TOOK THE ACTION "
                "(announced, released, invested). Do not attribute community actions to a company that only inspired them.\n"
                "- When describing a technology in what_it_is or current_state, clearly state its origin:\n"
                "  * 'Based on [Company] research paper [name]' for paper-inspired implementations\n"
                "  * 'Released by [Company]' for official releases\n"
                "  * 'Community/open-source implementation of [concept]' for independent builds\n"
                "- If the articles don't clearly state who built or released something, say so rather than guessing.\n\n"
                "OUTPUT REQUIREMENT:\n"
                "Return the entire response strictly as a valid JSON object matching the schema below.\n"
                "Do NOT include markdown, comments, or text outside the JSON object.\n\n"
                f"OUTPUT SCHEMA:\n```json\n{schema_json}\n```\n\n"
                "OUTPUT RULES:\n"
                "- Output must be valid JSON only, no markdown fencing or trailing commas.\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Use markdown in report_sections content fields.\n"
                "- Include all top-level keys, even if some arrays are empty.\n"
                "- Every radar_item_details entry's technology_name must match exactly one radar_items entry's name.\n"
                + (
                    f"\nADDITIONAL USER REQUIREMENTS:\n{custom_requirements}\n"
                    if custom_requirements
                    else ""
                )
                + (
                    f"\n{org_context}\n"
                    if org_context
                    else ""
                )
            ),
        },
        {
            "role": "user",
            "parts": (
                f"DATE RANGE: {date_range}\n"
                f"DOMAIN: {domain}\n\n"
                f"CLASSIFIED ARTICLES:\n\n{classified_articles_json}\n\n"
                "Generate the complete Tech Sensing Report. Return ONLY valid JSON."
            ),
        },
    ]
    return contents
