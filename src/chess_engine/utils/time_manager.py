import time


class SearchTimeout(Exception):
    pass


class TimeManager:
    def __init__(self, time_limit: float):
        if time_limit <= 0:
            raise ValueError("O limite de tempo deve ser positivo.")

        self.time_limit = time_limit
        self.start_time = time.monotonic()
        self.deadline = self.start_time + time_limit

    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def check(self) -> None:
        if time.monotonic() >= self.deadline:
            raise SearchTimeout("Tempo de busca esgotado.")