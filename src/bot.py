def main():
    print("Welcome to the AI Bot!")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        response = process_input(user_input)
        print("Bot:", response)

def process_input(user_input):
    # Placeholder for processing user input and generating a response
    return "This is a placeholder response."

if __name__ == "__main__":
    main()