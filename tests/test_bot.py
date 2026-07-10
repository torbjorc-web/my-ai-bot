import unittest
from src.bot import Bot  # Adjust the import based on your actual bot class location


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