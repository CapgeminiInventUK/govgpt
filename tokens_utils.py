import tiktoken


class TokenUtils:
    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def calculate_token_length(self, text):
        return len(self.encoding.encode(text))

    @staticmethod
    def calculate_embedding_token_cost(token_count):
        return (token_count / 1000) * 0.0001
