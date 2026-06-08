from abc import ABC, abstractmethod
from typing import Any


class ConnectorError(RuntimeError):
    pass


class Connector(ABC):
    @abstractmethod
    def execute(self, action: str, resource: str, input_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

