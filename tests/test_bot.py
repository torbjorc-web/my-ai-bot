import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from src.bot import Bot, FallbackBackend, InternetAugmentedBackend, create_backend


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
            )

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
                primary=Bot().backend,
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("wikipedia.org",),
            )

            payload = (
                '{"extract":"Python is a programming language.",' 
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            with patch("src.bot.request.urlopen", return_value=_MockResponse(payload)) as mocked_urlopen:
                first = backend.generate("What is Python?")
                second = backend.generate("What is Python?")

            self.assertIn("I found this online", first)
            self.assertIn("wikipedia.org", first)
            self.assertEqual(first, second)
            self.assertEqual(1, mocked_urlopen.call_count)

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
                primary=Bot().backend,
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=0,
                allowed_domains=("wikipedia.org",),
            )

            payload = (
                '{"extract":"Python is a programming language.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            with patch("src.bot.request.urlopen", return_value=_MockResponse(payload)) as mocked_urlopen:
                backend.generate("What is Python?")
                backend.generate("What is Python?")

            self.assertEqual(2, mocked_urlopen.call_count)

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
                primary=Bot().backend,
                cache_path=cache_path,
                timeout_seconds=2,
                max_summary_chars=200,
                cache_ttl_days=14,
                allowed_domains=("example.com",),
            )

            payload = (
                '{"extract":"Python is a programming language.",'
                '"content_urls":{"desktop":{"page":"https://en.wikipedia.org/wiki/Python_(programming_language)"}}}'
            ).encode("utf-8")

            with patch("src.bot.request.urlopen", return_value=_MockResponse(payload)):
                response = backend.generate("What is Python?")

            self.assertIn("not sure how to respond", response.lower())

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