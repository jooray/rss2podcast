import ollama

class OllamaClient:
    def __init__(self, model, url='http://localhost:11434'):
        self.model = model
        self.client = ollama.Client(host=url)

    def generate(self, prompt):
        try:
            response = self.client.generate(model=self.model, prompt=prompt)
            return response['response']
        except Exception as e:
            raise Exception(f"Ollama API request failed: {str(e)}")
