from dotenv import load_dotenv
from tavily import TavilyClient
import os
import asyncio
import time

# Load environment variables
load_dotenv()
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Initialize Tavily client
client = TavilyClient(api_key=tavily_api_key)

async def search_tavily(query: str, max_results: int = 5, depth: str = "advanced"):
    """
    Perform an asynchronous web search using Tavily API with retry logic.

    Args:
        query (str): The search query string.
        max_results (int): Maximum number of results to return (default=5).
        depth (str): Search depth, "basic" or "advanced" (default="advanced").

    Returns:
        dict: Tavily API response containing search results, or empty dict on failure.
    """
    attempts = 0
    while attempts < 5:
        try:
            return await asyncio.to_thread(
                client.search,
                query=query,
                include_answer="advanced",
                search_depth=depth,
                max_results=max_results,
                include_favicon=True,
            )
        except Exception as e:
            attempts += 1
            print(f"Tavily search attempt {attempts} failed: {e}")
            if attempts >= 5:
                return {}
            await asyncio.sleep(1)
# or this maybe, we'll see
# def search(queries: list, max_results: int = 5, word_limit: int = 300):
#     """
#     Performs a search operation using multiple search engines and processes the results.
#     Args:
#         queries (list): A list of search queries to execute.
#         max_results (int, optional): The maximum number of results to fetch for each query. Defaults to 5.
#         word_limit (int, optional): The maximum number of words to extract from each result's content. Defaults to 300.
#     Returns:
#         list: A list of dictionaries, where each dictionary contains:
#             - "search_query" (str): The original search query.
#             - "search_results" (list): A list of dictionaries for each search result, containing:
#                 - "page_title" (str): The title of the page.
#                 - "page_body" (str): The body content of the page (including extracted content).
#     Notes:
#         - The function attempts to fetch results from Google and DuckDuckGo.
#         - Results are processed in parallel using a thread pool for efficiency.
#         - If an error occurs during any stage of the process, it is logged, and the function continues with the remaining queries.
#         - The results are grouped by the original search query.
#     """

#     try:
#         # return ["no web search results found"]
#         results = []

#         # Fetch search results
#         for query in queries:
#             try:
#                 success, result = google_search(query=query, max_results=max_results)
#                 if success:
#                     for r in result:
#                         r["query"] = query
#                     results.extend(result)
#                     continue
#             except Exception as e:
#                 print(f"Google search failed for query: {query}. Error: {e}")

#             try:
#                 duck_results = fetch_duckduckgo_results(query=query, max_results=max_results)
#                 if duck_results:
#                     for r in duck_results:
#                         r["query"] = query
#                     results.extend(duck_results)
#             except Exception as e:
#                 print(f"DuckDuckGo search failed for query: {query}. Error: {e}")

#         # Group results by query
#         grouped = defaultdict(list)
#         for entry in results:
#             grouped[entry.get("query", "")].append(entry)

#         # Flatten the results again with word_limit info
#         entries_with_limit = []
#         for query, entries in grouped.items():
#             for i, entry in enumerate(entries):
#                 limit = 800 if i < 1 else word_limit
#                 entries_with_limit.append((entry, limit))

#         # Process entries in parallel
#         def process_entry(entry, word_limit_in):
#             try:
#                 link = entry.get("link")
#                 extracted = (
#                     extract_content_from_link(link, word_limit=word_limit_in)
#                     if link
#                     else ""
#                 )
#                 return {
#                     "search_query": entry.get("query", ""),
#                     "page_title": entry.get("title", ""),
#                     "page_body": f"{entry.get('body', '')} {extracted}",
#                 }
#             except Exception:
#                 return None

#         all_processed = []
#         with ThreadPoolExecutor(max_workers=15) as executor:
#             futures = [
#                 executor.submit(process_entry, entry, limit)
#                 for entry, limit in entries_with_limit
#             ]
#             for future in as_completed(futures):
#                 result = future.result()
#                 if result:
#                     all_processed.append(result)

#         # Regroup by search_query
#         grouped_results = defaultdict(list)
#         for item in all_processed:
#             grouped_results[item["search_query"]].append(
#                 {
#                     "page_title": item["page_title"],
#                     "page_body": item["page_body"],
#                     # "link": item["link"]
#                 }
#             )

#         final_output = [
#             {"search_query": query, "search_results": entries}
#             for query, entries in grouped_results.items()
#         ]

#         return final_output

#     except Exception as e:
#         print(f"Overall search error: {e}")
#         return []
