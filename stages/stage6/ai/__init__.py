from .minimax import Minimax
from .alphabeta import AlphaBeta
from .expectimax import Expectimax

class AI:
    @staticmethod
    def act(algo, gs, depth=2):
        if algo == "Minimax":
            return Minimax.run(gs, depth)
        if algo == "AlphaBeta":
            return AlphaBeta.run(gs, depth)
        if algo == "Expectimax":
            return Expectimax.run(gs, depth)