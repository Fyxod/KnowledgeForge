def sensing_classify_prompt(
    articles_text: str,
    domain: str = "Generative AI",
    custom_requirements: str = "",
) -> list[dict]:
    """
    Build a chat prompt to classify and summarize a batch of articles.

    NOTE: Do NOT embed the JSON schema here — invoke_llm() already injects
    the schema via PydanticOutputParser.get_format_instructions().  Embedding
    it twice causes the LLM to echo the schema definition back instead of
    producing actual classified article data.
    """
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
                "OUTPUT RULES:\n"
                "- Return ONLY a valid JSON object with an \"articles\" array.\n"
                "- Each element must have: title, source, url, published_date, summary, "
                "relevance_score, quadrant, ring, technology_name, reasoning.\n"
                "- Do NOT include schema definitions, $defs, $ref, properties, or type metadata.\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Filter out articles with relevance_score < 0.3.\n"
                "- If an article is not relevant to the domain, omit it from the output.\n"
                "- The articles array MUST contain actual classified data, not be empty.\n"
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
                "Classify each relevant article above. The articles array in your "
                "response MUST contain classified entries — do NOT return an empty "
                "array. Return ONLY valid JSON."
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

    NOTE: Do NOT embed the full JSON schema here — invoke_llm() already
    injects it via PydanticOutputParser.  Only list expected top-level keys
    to guide the LLM without causing schema echo.
    """

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
                "3. Analyzes market signals from prominent companies\n"
                "4. Offers actionable recommendations\n"
                "5. Highlights notable developments\n\n"
                "REPORT QUALITY GUIDELINES:\n"
                "- Executive summary: decisive, forward-looking, 200-350 words. "
                "Use markdown formatting: bold (**term**) for key technologies, "
                "bullet points for the top 3-5 highlights, and separate paragraphs. "
                "Do NOT write it as a single wall of text.\n\n"
                "- Key trends: identify 5-10 major trends with supporting evidence from the articles. "
                "Each trend should have a clear description of WHY it matters.\n\n"
                "- Radar items: 15-30 distinct technologies/techniques — consolidate duplicates.\n\n"
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
                "- For market_signals: The company_or_player must be the entity that TOOK THE ACTION "
                "(announced, released, invested). Do not attribute community actions to a company that only inspired them.\n"
                "- If the articles don't clearly state who built or released something, say so rather than guessing.\n\n"
                "OUTPUT RULES:\n"
                "- Return ONLY a valid JSON object with these top-level keys: report_title, "
                "executive_summary, domain, date_range, total_articles_analyzed, key_trends, "
                "radar_items, market_signals, report_sections, recommendations, notable_articles.\n"
                "- Do NOT include radar_item_details — those will be generated separately.\n"
                "- Do NOT include schema definitions, $defs, $ref, properties, or type metadata.\n"
                "- Output must be valid JSON only, no markdown fencing or trailing commas.\n"
                "- Newlines inside string values MUST be written as \\n (escaped), NOT as actual line breaks.\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
                "- Use markdown in report_sections content fields.\n"
                "- Include all top-level keys listed above, even if some arrays are empty.\n"
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


def sensing_details_prompt(
    radar_items_json: str,
    classified_articles_json: str,
    domain: str = "Generative AI",
) -> list[dict]:
    """
    Build a chat prompt to generate detailed write-ups for each radar item.

    This is Phase 2 of report generation — called after the skeleton (Phase 1)
    has produced the radar_items list.  Keeping this separate avoids exceeding
    output token limits by splitting the heaviest section into its own call.
    """
    contents = [
        {
            "role": "system",
            "parts": (
                "You are a senior technology strategist writing detailed technology "
                f"radar entries for the {domain} domain.\n\n"
                "You are given a list of RADAR ITEMS (name, quadrant, ring) and the "
                "CLASSIFIED ARTICLES that were used to create them.\n\n"
                "For EVERY radar item, generate a detailed write-up covering:\n"
                "  * what_it_is: Clear explanation of what this technology is and how it works (2-4 sentences).\n"
                "  * why_it_matters: Why this technology is significant and what problems it solves (2-3 sentences).\n"
                "  * current_state: Current maturity, adoption level, and key developments (2-3 sentences).\n"
                "  * key_players: Companies/organizations that actively develop, maintain, or officially "
                "release this technology. Do NOT include entities that only published the underlying "
                "research paper unless they also released the implementation.\n"
                "  * practical_applications: Real-world use cases and applications (2-4 items).\n"
                "  * source_urls: URLs of articles informing this write-up.\n\n"
                "ATTRIBUTION ACCURACY RULES:\n"
                "- Distinguish between research authors and implementation authors.\n"
                "- For key_players: List ONLY entities that actively develop, maintain, or officially "
                "release the technology.\n"
                "- Clearly state origin: 'Based on [Company] research' vs 'Released by [Company]' "
                "vs 'Community/open-source implementation'.\n"
                "- If the articles don't clearly state who built something, say so.\n\n"
                "GROUNDING RULES:\n"
                "- Every claim MUST be grounded in the provided articles.\n"
                "- Use article URLs to populate source_urls (1-5 per entry).\n"
                "- Do NOT fabricate information not present in the articles.\n\n"
                "OUTPUT RULES:\n"
                "- Return ONLY a valid JSON object with one key: radar_item_details (array).\n"
                "- Each element must have: technology_name, what_it_is, why_it_matters, "
                "current_state, key_players, practical_applications, source_urls.\n"
                "- technology_name MUST exactly match the radar item name provided.\n"
                "- Do NOT include schema definitions, $defs, $ref, properties, or type metadata.\n"
                "- Newlines inside string values MUST be written as \\n (escaped).\n"
                '- Double quotes inside string values MUST be escaped as \\".\n'
            ),
        },
        {
            "role": "user",
            "parts": (
                f"DOMAIN: {domain}\n\n"
                f"RADAR ITEMS:\n{radar_items_json}\n\n"
                f"CLASSIFIED ARTICLES:\n{classified_articles_json}\n\n"
                "Generate detailed write-ups for EVERY radar item listed above. "
                "Return ONLY valid JSON."
            ),
        },
    ]
    return contents
