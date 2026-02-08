import sys
import os

# Add the project root to sys.path to import the tool
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.web_search import execute

def test_search(query, search_type="text"):
    print(f"\n--- Testing Search Type: {search_type} | Query: {query} ---")
    params = {
        "query": query,
        "search_type": search_type,
        "max_results": 2
    }
    result = execute(params)
    print(result[:1000] + ("..." if len(result) > 1000 else ""))

if __name__ == "__main__":
    try:
        # Test Text Search
        test_search("Python programming language", "text")
        
        # Test Images Search
        test_search("Mount Everest", "images")
        
        # Test Videos Search
        test_search("SpaceX launch", "videos")
        
        # Test News Search
        test_search("Latest technology news", "news")
        
        # Test Books Search
        test_search("The Great Gatsby", "books")
        
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install the required dependencies: pip install ddgs")
    except Exception as e:
        print(f"An error occurred: {e}")
