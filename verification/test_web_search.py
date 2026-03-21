import json
import os
import sys
import types
import unittest
from unittest.mock import patch

# Add the project root to sys.path to import the tool
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.web_search import execute


class WebSearchToolTests(unittest.TestCase):
    def test_ddg_search_still_works_without_tavily_installed(self):
        fake_results = [{"title": "Python", "href": "https://example.com", "body": "Docs"}]

        with patch("tools.web_search.DDGS") as mock_ddgs:
            mock_ddgs.return_value.text.return_value = fake_results
            result = execute({"query": "python", "provider": "ddg", "max_results": 1})

        self.assertEqual(json.loads(result), fake_results)

    def test_tavily_provider_rejects_non_text_search(self):
        result = execute({"query": "python", "provider": "tavily", "search_type": "news"})
        self.assertEqual(result, "Error: Tavily only supports text search.")

    def test_tavily_provider_maps_results_to_ddg_shape(self):
        fake_module = types.ModuleType("tavily")

        class FakeTavilyClient:
            def search(self, query, max_results):
                self.last_query = query
                self.last_max_results = max_results
                return {
                    "results": [
                        {
                            "title": "Python",
                            "url": "https://example.com",
                            "content": "Docs",
                            "score": 0.95,
                        }
                    ]
                }

        fake_module.TavilyClient = FakeTavilyClient

        with patch.dict(sys.modules, {"tavily": fake_module}):
            result = execute({"query": "python", "provider": "tavily", "max_results": 1})

        self.assertEqual(
            json.loads(result),
            [
                {
                    "title": "Python",
                    "href": "https://example.com",
                    "body": "Docs",
                    "score": 0.95,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
