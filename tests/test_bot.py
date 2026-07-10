import unittest
from src.bot import Bot  # Adjust the import based on your actual bot class location

class TestBot(unittest.TestCase):

    def setUp(self):
        self.bot = Bot()  # Initialize the bot before each test

    def test_response_to_greeting(self):
        response = self.bot.get_response("Hello")
        self.assertIn("Hello", response)  # Adjust based on expected behavior

    def test_response_to_farewell(self):
        response = self.bot.get_response("Goodbye")
        self.assertIn("Goodbye", response)  # Adjust based on expected behavior

    def test_response_to_unknown_input(self):
        response = self.bot.get_response("What is this?")
        self.assertIn("I'm not sure how to respond", response)  # Adjust based on expected behavior

if __name__ == '__main__':
    unittest.main()