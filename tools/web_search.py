from ddgs import DDGS
import json

# The SCHEMA for the Google GenAI tool definition
SCHEMA = {
    "name": "web_search",
    "display_name": "Searching the web",
    "description": "Performs web searches using DuckDuckGo. Supports text, images, videos, news, and books.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The search query."
            },
            "search_type": {
                "type": "STRING",
                "description": "The type of search to perform. Options: 'text', 'images', 'videos', 'news', 'books'.",
                "enum": ["text", "images", "videos", "news", "books"],
                "default": "text"
            },
            "region": {
                "type": "STRING",
                "description": "Region code (e.g., 'us-en', 'uk-en'). Defaults to 'us-en'.",
                "default": "us-en"
            },
            "safesearch": {
                "type": "STRING",
                "description": "Safe search level: 'on', 'moderate', 'off'. Defaults to 'moderate'.",
                "enum": ["on", "moderate", "off"],
                "default": "moderate"
            },
            "timelimit": {
                "type": "STRING",
                "description": "Time limit for results: 'd' (day), 'w' (week), 'm' (month), 'y' (year). Defaults to None.",
                "enum": ["d", "w", "m", "y"]
            },
            "max_results": {
                "type": "INTEGER",
                "description": "Maximum number of results to return. Defaults to 10.",
                "default": 10
            },
            "backend": {
                "type": "STRING",
                "description": "Specific backend for text search (e.g., 'api', 'html', 'lite'). Defaults to 'auto'.",
                "default": "auto"
            }
        },
        "required": ["query"]
    }
}

def execute(params: dict) -> str:
    """Executes the web search tool and returns results as a JSON string."""
    query = params.get("query")
    search_type = params.get("search_type", "text")
    region = params.get("region", "us-en")
    safesearch = params.get("safesearch", "moderate")
    timelimit = params.get("timelimit")
    max_results = params.get("max_results", 10)
    backend = params.get("backend", "auto")

    try:
        ddgs = DDGS()
        results = []

        if search_type == "text":
            results = ddgs.text(
                query, 
                region=region, 
                safesearch=safesearch, 
                timelimit=timelimit, 
                max_results=max_results,
                backend=backend
            )
        elif search_type == "images":
            results = ddgs.images(
                query, 
                region=region, 
                safesearch=safesearch, 
                timelimit=timelimit, 
                max_results=max_results
            )
        elif search_type == "videos":
            results = ddgs.videos(
                query, 
                region=region, 
                safesearch=safesearch, 
                timelimit=timelimit, 
                max_results=max_results
            )
        elif search_type == "news":
            results = ddgs.news(
                query, 
                region=region, 
                safesearch=safesearch, 
                timelimit=timelimit, 
                max_results=max_results
            )
        elif search_type == "books":
            results = ddgs.books(
                query, 
                max_results=max_results
            )
        else:
            return f"Error: Unsupported search type '{search_type}'."

        if not results:
            return "No results found."

        return json.dumps(results, indent=2)

    except Exception as e:
        return f"Error during web search: {str(e)}"
