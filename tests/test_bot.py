import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from typing import cast
from src.bot import BackendProtocol, Bot, FallbackBackend, InternetAugmentedBackend, create_backend


class TestBot(unittest.TestCase):

    def setUp(self):
        self.bot = Bot()  # Initialize the bot before each test

    def test_response_to_greeting(self):
        response = self.bot.get_response("Hello")
        self.assertIn("Hello", response)

    def test_response_to_farewell(self):
        response = self.bot.get_response("Goodbye")
        self.assertIn("Goodbye", response)

    def test_response_to_unknown_input(self):
        response = self.bot.get_response("What is this?")
        self.assertIn("I'm not sure how to respond", response)

    def test_batch_processing(self):
        results = self.bot.process_batch_concurrently(["Hello", "help", "Goodbye"])
        self.assertEqual(3, len(results))
        self.assertEqual("Hello", results[0].user_input)
        self.assertIn("Hello", results[0].response)
        self.assertIn("help", results[1].response.lower())
        self.assertIn("Goodbye", results[2].response)

    def test_stream_response(self):
        chunks = list(self.bot.stream_response("Hello"))
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("Hello", "".join(chunks))

    def test_openai_backend_falls_back_without_token(self):
        backend = create_backend(
            "openai",
            openai_api_key="",
            openai_model="gpt-4o-mini",
            openai_temperature=0.2,
            ollama_host="http://127.0.0.1:11434",
            ollama_model="llama3.1",
            allow_backend_fallback=True,
            enable_learning=False,
            learning_store_path="data/test-learned.json",
            learning_min_similarity=0.70,
            system_prompt_path="src/prompts/system_prompt.txt",
            enable_internet_learning=False,
            internet_cache_path="data/test-internet-cache.json",
            internet_timeout_seconds=8,
            internet_max_summary_chars=700,
            internet_cache_ttl_days=14,
            internet_allowed_domains=("en.wikipedia.org", "wikipedia.org"),
            internet_source_providers=("wikipedia",),
            internet_max_sources=1,
        )
        self.assertIsInstance(backend, FallbackBackend)

    def test_openai_backend_raises_without_token_when_fallback_disabled(self):
        with self.assertRaises(ValueError):
            create_backend(
                "openai",
                openai_api_key="",
                openai_model="gpt-4o-mini",
                openai_temperature=0.2,
                ollama_host="http://127.0.0.1:11434",
                ollama_model="llama3.1",
                allow_backend_fallback=False,
                enable_learning=False,
                learning_store_path="data/test-learned.json",
                learning_min_similarity=0.70,
                system_prompt_path="src/prompts/system_prompt.txt",
                enable_internet_learning=False,
                internet_cache_path="data/test-internet-cache.json",
                internet_timeout_seconds=8,
                internet_max_summary_chars=700,
                internet_cache_ttl_days=14,
                internet_allowed_domains=("en.wikipedia.org", "wikipedia.org"),
                internet_source_providers=("wikipedia",),
                internet_max_sources=1,
            )

    def test_fallback_backend_uses_secondary_on_runtime_failure(self):
        class _FailingBackend:
            def generate(self, user_input: str) -> str:
                raise RuntimeError("backend unavailable")

            async def agenerate(self, user_input: str) -> str:
                raise RuntimeError("backend unavailable")

            def stream_generate(self, user_input: str):
                raise RuntimeError("backend unavailable")
                yield ""

            async def astream_generate(self, user_input: str):
                raise RuntimeError("backend unavailable")
                yield ""

        fallback = FallbackBackend(
            primary=cast(BackendProtocol, _FailingBackend()),
            secondary=cast(BackendProtocol, Bot().backend),
        )
        response = fallback.generate("hello")
        self.assertIn("hello", response.lower())

    def test_fallback_backend_reraises_programming_error(self):
        class _BrokenBackend:
            def generate(self, user_input: str) -> str:
                raise AttributeError("bug in backend")

            async def agenerate(self, user_input: str) -> str:
                raise AttributeError("bug in backend")

            def stream_generate(self, user_input: str):
                raise AttributeError("bug in backend")
                yield ""

            async def astream_generate(self, user_input: str):
                raise AttributeError("bug in backend")
                yield ""

        fallback = FallbackBackend(
            primary=cast(BackendProtocol, _BrokenBackend()),
            secondary=cast(BackendProtocol, Bot().backend),
        )
        with self.assertRaises(AttributeError):
            fallback.generate("hello")

    def test_learning_persists_custom_response(self):
        with TemporaryDirectory() as tmp_dir:
            store_path = f"{tmp_dir}/learned.json"
            backend = create_backend(
                "rule-based",
                openai_api_key="",
                openai_model="gpt-4o-mini",
                openai_temperature=0.2,
                ollama_host="http://127.0.0.1:11434",
                ollama_model="llama3.1",
                allow_backend_fallback=True,
                enable_learning=True,
                learning_store_path=store_path,
                learning_min_similarity=0.70,
                system_prompt_path="src/prompts/system_prompt.txt",
                enable_internet_learning=False,
                internet_cache_path="data/test-internet-cache.json",
                internet_timeout_seconds=8,
                internet_max_summary_chars=700,
                internet_cache_ttl_days=14,
                internet_allowed_domains=("en.wikipedia.org", "wikipedia.org"),
                internet_source_providers=("wikipedia",),
                internet_max_sources=1,
            )
            bot = Bot(backend=backend)
            taught = bot.learn("how do you feel", "I feel ready to help.")
            self.assertTrue(taught)
            self.assertIn("ready to help", bot.get_response("How do you feel"))

            backend_reloaded = create_backend(
                "rule-based",
                openai_api_key="",
                openai_model="gpt-4o-mini",
                openai_temperature=0.2,
                ollama_host="http://127.0.0.1:11434",
                ollama_model="llama3.1",
                allow_backend_fallback=True,
                enable_learning=True,
                learning_store_path=store_path,
                learning_min_similarity=0.70,
                system_prompt_path="src/prompts/system_prompt.txt",
                enable_internet_learning=False,
                internet_cache_path="data/test-internet-cache.json",
                internet_timeout_seconds=8,
                internet_max_summary_chars=700,
                internet_cache_ttl_days=14,
                internet_allowed_domains=("en.wikipedia.org", "wikipedia.org"),
                internet_source_providers=("wikipedia",),
                internet_max_sources=1,
            )
            bot_reloaded = Bot(backend=backend_reloaded)
            self.assertIn("ready to help", bot_reloaded.get_response("how do you feel"))

    def test_learning_fuzzy_match(self):
        with TemporaryDirectory() as tmp_dir:
            store_path = f"{tmp_dir}/learned.json"
            backend = create_backend(
                "rule-based",
                openai_api_key="",
                openai_model="gpt-4o-mini",
                openai_temperature=0.2,
                ollama_host="http://127.0.0.1:11434",
                ollama_model="llama3.1",
                allow_backend_fallback=True,
                enable_learning=True,
                learning_store_path=store_path,
                learning_min_similarity=0.70,
                system_prompt_path="src/prompts/system_prompt.txt",
                enable_internet_learning=False,
                internet_cache_path="data/test-internet-cache.json",
                internet_timeout_seconds=8,
                internet_max_summary_chars=700,
                internet_cache_ttl_days=14,
                internet_allowed_domains=("en.wikipedia.org", "wikipedia.org"),
                internet_source_providers=("wikipedia",),
                internet_max_sources=1,
            )
            bot = Bot(backend=backend)
            bot.learn("how do you feel", "I feel calm and focused.")
            self.assertIn("calm and focused", bot.get_response("how are you feeling"))

    def test_internet_augmented_backend_uses_cache_after_first_lookup(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            payload = (
                '{"extract":"Python is a programming language.",' 
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            with patch("src.backends.wrappers.request.urlopen", return_value=_MockResponse(payload)) as mocked_urlopen:
                first = backend.generate("What is Python?")
                second = backend.generate("What is Python?")

            self.assertIn("I found this online", first)
            self.assertIn("wikipedia.org", first)
            self.assertEqual(first, second)
            self.assertEqual(2, mocked_urlopen.call_count)

    def test_internet_augmented_backend_refreshes_when_ttl_expires(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=0,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            payload = (
                '{"extract":"Python is a programming language.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            with patch("src.backends.wrappers.request.urlopen", return_value=_MockResponse(payload)) as mocked_urlopen:
                backend.generate("What is Python?")
                backend.generate("What is Python?")

            self.assertEqual(4, mocked_urlopen.call_count)

    def test_internet_augmented_backend_can_return_multiple_sources(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org", "duckduckgo.com"),
                source_providers=("wikipedia", "duckduckgo"),
                max_sources=2,
            )

            wiki_payload = (
                '{"extract":"Python is a programming language.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")
            ddg_payload = (
                '{"AbstractText":"Python is a high-level language.",'
                '"AbstractURL":"https://duckduckgo.com/Python_(programming_language)"}'
            ).encode("utf-8")

            def _mock_urlopen(req, timeout=0):
                url = req.full_url
                if "wikipedia.org" in url:
                    return _MockResponse(wiki_payload)
                return _MockResponse(ddg_payload)

            with patch("src.backends.wrappers.request.urlopen", side_effect=_mock_urlopen):
                response = backend.generate("What is Python?")

            self.assertIn("Sources:", response)
            self.assertIn("[1]", response)
            self.assertIn("[2]", response)
            self.assertIn("wikipedia.org", response)
            self.assertIn("duckduckgo.com", response)

    def test_internet_augmented_backend_rejects_source_outside_allowlist(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("example.com",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            payload = (
                '{"extract":"Python is a programming language.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            with patch("src.backends.wrappers.request.urlopen", return_value=_MockResponse(payload)):
                response = backend.generate("What is Python?")

            self.assertIn("not sure how to respond", response.lower())

    def test_wikipedia_404_falls_back_to_title_search(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            search_payload = (
                '["what is python?", ["Python (programming language)"], [""], [""] ]'
            ).encode("utf-8")
            summary_payload = (
                '{"extract":"Python is a programming language.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            def _mock_urlopen(req, timeout=0):
                url = req.full_url
                if "w/api.php" in url:
                    return _MockResponse(search_payload)
                if "Python%20%28programming%20language%29" in url:
                    return _MockResponse(summary_payload)
                raise RuntimeError("Not Found")

            with patch("src.backends.wrappers.request.urlopen", side_effect=_mock_urlopen):
                response = backend.generate("What is Python?")

            self.assertIn("I found this online", response)
            self.assertIn("wikipedia.org", response)

    def test_user_sees_note_when_wikipedia_lookup_fails(self):
        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            with patch("src.backends.wrappers.request.urlopen", side_effect=RuntimeError("Not Found")):
                response = backend.generate("What is Python?")

            self.assertIn("wikipedia lookup failed", response.lower())
            self.assertIn("more specific", response.lower())

    def test_question_style_query_is_reduced_to_topic_for_wikipedia(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            search_empty_payload = '["what is london", [], [], []]'.encode("utf-8")
            search_hit_payload = '["london", ["London"], [""], [""] ]'.encode("utf-8")
            summary_payload = (
                '{"extract":"London is the capital and largest city of England.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/London"}}}'
            ).encode("utf-8")

            def _mock_urlopen(req, timeout=0):
                url = req.full_url
                if "w/api.php" in url and "what%20is%20london" in url:
                    return _MockResponse(search_empty_payload)
                if "w/api.php" in url and "search=london" in url:
                    return _MockResponse(search_hit_payload)
                if "page/summary/London" in url:
                    return _MockResponse(summary_payload)
                raise RuntimeError("Not Found")

            with patch("src.backends.wrappers.request.urlopen", side_effect=_mock_urlopen):
                response = backend.generate("What is London?")

            self.assertIn("I found this online", response)
            self.assertIn("/wiki/London", response)

    def test_major_cities_query_returns_overview_with_examples(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=300,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            payload = (
                '{"extract":"A global city is a city which is a primary node in the global economic network.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Global_city"}}}'
            ).encode("utf-8")

            with patch("src.backends.wrappers.request.urlopen", return_value=_MockResponse(payload)):
                response = backend.generate("What are some major cities in the world?")

            self.assertIn("major examples", response.lower())
            self.assertIn("drammen", response.lower())
            self.assertIn("/wiki/Global_city", response)

    def test_major_capitals_query_returns_capitals_overview(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=300,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            payload = (
                '{"extract":"A capital city is the municipality holding primary status in a country or region.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Capital_city"}}}'
            ).encode("utf-8")

            with patch("src.backends.wrappers.request.urlopen", return_value=_MockResponse(payload)):
                response = backend.generate("What are major capitals in the world?")

            self.assertIn("major capital examples", response.lower())
            self.assertIn("oslo", response.lower())
            self.assertIn("/wiki/Capital_city", response)

    def test_specific_city_query_extracts_city_topic(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=250,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            search_hit_payload = '["drammen", ["Drammen"], [""], [""] ]'.encode("utf-8")
            summary_payload = (
                '{"extract":"Drammen is a city in Buskerud county, Norway.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Drammen"}}}'
            ).encode("utf-8")

            def _mock_urlopen(req, timeout=0):
                url = req.full_url
                if "w/api.php" in url and "search=drammen" in url:
                    return _MockResponse(search_hit_payload)
                if "page/summary/Drammen" in url:
                    return _MockResponse(summary_payload)
                raise RuntimeError("Not Found")

            with patch("src.backends.wrappers.request.urlopen", side_effect=_mock_urlopen):
                response = backend.generate("Tell me information about great city Drammen")

            self.assertIn("I found this online", response)
            self.assertIn("/wiki/Drammen", response)

    def test_city_not_in_curated_examples_can_still_be_found(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=250,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            search_payload = '["kisumu", ["Kisumu County", "Kisumu"], ["", ""], ["", ""] ]'.encode("utf-8")
            summary_payload = (
                '{"extract":"Kisumu is a city in western Kenya.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Kisumu"}}}'
            ).encode("utf-8")

            def _mock_urlopen(req, timeout=0):
                url = req.full_url
                if "w/api.php" in url and "search=kisumu" in url:
                    return _MockResponse(search_payload)
                if "page/summary/Kisumu%20County" in url:
                    raise RuntimeError("Not Found")
                if "page/summary/Kisumu" in url:
                    return _MockResponse(summary_payload)
                raise RuntimeError("Not Found")

            with patch("src.backends.wrappers.request.urlopen", side_effect=_mock_urlopen):
                response = backend.generate("Tell me about Kisumu")

            self.assertIn("I found this online", response)
            self.assertIn("/wiki/Kisumu", response)

    def test_ambiguous_city_query_includes_did_you_mean_hint(self):
        class _MockResponse:
            def __init__(self, payload: bytes):
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with TemporaryDirectory() as tmp_dir:
            cache_path = f"{tmp_dir}/internet-cache.json"
            backend = InternetAugmentedBackend(
                primary=cast(BackendProtocol, Bot().backend),
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=250,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
                source_providers=("wikipedia",),
                max_sources=1,
            )

            search_payload = (
                '["springfield", ["Springfield, Illinois", "Springfield, Missouri", "Springfield, Massachusetts"], ["", "", ""], ["", "", ""] ]'
            ).encode("utf-8")
            summary_payload = (
                '{"extract":"Springfield is the capital city of Illinois.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Springfield,_Illinois"}}}'
            ).encode("utf-8")

            def _mock_urlopen(req, timeout=0):
                url = req.full_url
                if "w/api.php" in url and "search=springfield" in url:
                    return _MockResponse(search_payload)
                if "page/summary/Springfield%2C%20Illinois" in url:
                    return _MockResponse(summary_payload)
                raise RuntimeError("Not Found")

            with patch("src.backends.wrappers.request.urlopen", side_effect=_mock_urlopen):
                response = backend.generate("Tell me about Springfield")

            self.assertIn("Did you mean:", response)
            self.assertIn("Springfield, Missouri", response)

    def test_create_backend_wraps_rule_based_with_internet_backend_when_enabled(self):
        backend = create_backend(
            "rule-based",
            openai_api_key="",
            openai_model="gpt-4o-mini",
            openai_temperature=0.2,
            ollama_host="http://127.0.0.1:11434",
            ollama_model="llama3.1",
            allow_backend_fallback=True,
            enable_learning=False,
            learning_store_path="data/test-learned.json",
            learning_min_similarity=0.70,
            system_prompt_path="src/prompts/system_prompt.txt",
            enable_internet_learning=True,
            internet_cache_path="data/test-internet-cache.json",
            internet_timeout_seconds=8,
            internet_max_summary_chars=700,
            internet_cache_ttl_days=14,
            internet_allowed_domains=("en.wikipedia.org", "wikipedia.org"),
            internet_source_providers=("wikipedia",),
            internet_max_sources=1,
        )
        self.assertIsInstance(backend, InternetAugmentedBackend)


class TestBotAsync(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.bot = Bot()

    async def test_async_batch_processing(self):
        results = await self.bot.process_batch_async(["Hello", "help", "Goodbye"])
        self.assertEqual(3, len(results))
        self.assertEqual("Hello", results[0].user_input)
        self.assertIn("Hello", results[0].response)
        self.assertIn("help", results[1].response.lower())
        self.assertIn("Goodbye", results[2].response)

    async def test_async_stream_response(self):
        chunks = []
        async for chunk in self.bot.stream_response_async("Goodbye"):
            chunks.append(chunk)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("Goodbye", "".join(chunks))

if __name__ == '__main__':
    unittest.main()