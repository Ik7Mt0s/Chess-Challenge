from dataclasses import dataclass


@dataclass
class SearchMetrics:
    negamax_nodes: int = 0
    quiescence_nodes: int = 0
    alpha_beta_cutoffs: int = 0

    @property
    def total_nodes(self) -> int:
        return self.negamax_nodes + self.quiescence_nodes

    def as_dict(self) -> dict[str, int]:
        return {
            "negamax_nodes": self.negamax_nodes,
            "quiescence_nodes": self.quiescence_nodes,
            "alpha_beta_cutoffs": self.alpha_beta_cutoffs,
            "total_nodes": self.total_nodes,
        }
