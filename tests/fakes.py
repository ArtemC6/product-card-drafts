class FakeLLM:
    """Отдаёт заранее заготовленные ответы и запоминает, что ей отправили."""

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)
