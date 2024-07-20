class ShopifyGraphQLException(Exception):
    def __init__(self, message: list | str) -> None:
        if isinstance(message, list):
            self.message = "\n".join(error.get("message", "Unknown error") for error in message)
        else:
            self.message = message
        super().__init__(self.message)
