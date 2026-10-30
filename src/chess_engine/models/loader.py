from pathlib import Path


class ModelLoader:
    """
    Ponto de integração para modelos futuros.

    O motor inicial não depende de modelos externos.
    """

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)

    def load(self):
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Modelo não encontrado: {self.model_path}"
            )

        raise NotImplementedError(
            "O carregamento de modelos ainda não foi implementado."
        )