import openai

from openai import OpenAI  # New import


class API:
    def __init__(self):
        self.model = "gpt-4o-mini"  # Using GPT-4 Mini model
        self.messages = []
        self.client = None  # Add client property

    def get_response(self, user_input, system_prompt=None):
        if system_prompt and not self.messages:
            # Add system prompt at the start of conversation
            self.messages.append({"role": "system", "content": system_prompt})
            
        self.messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages
            )
            ai_response = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": ai_response})
            return ai_response

        except Exception as e:
            print(f"Error getting response: {e}")
            return "I'm having trouble connecting right now."

    def load_api_key(self):
        try:
            with open("../metadata/openai-key.txt", "r") as file:
                api_key = file.read().strip()
                self.client = OpenAI(api_key=api_key)  # Initialize client with API key
        except FileNotFoundError:
            print("Error: openai-key.txt file not found")
            return None
        except Exception as e:
            print(f"Error loading API key: {e}")
            return None


if __name__ == "__main__":
    persona = API()
    persona.load_api_key()
    print(persona.get_response("Hello, how are you?"))
