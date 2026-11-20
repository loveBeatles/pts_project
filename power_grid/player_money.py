"""Track one player's money and Bureaucracy income."""

from power_grid.simple_types import PlayerColor


class PlayerMoney:
    _INCOME_BY_TOWNS: tuple[int, ...] = (
        10,
        22,
        33,
        44,
        54,
        64,
        73,
        82,
        90,
        98,
        105,
        112,
        118,
        124,
        129,
        134,
        138,
        142,
        145,
        148,
        150,
    )

    _color: PlayerColor
    _current_money: int

    def __init__(self, color: PlayerColor, starting_money: int = 50) -> None:
        """Create the player's money with a default value of 50 Elektro."""
        if starting_money < 0:
            raise ValueError("Starting money cannot be negative.")

        self._color = color
        self._current_money = starting_money

    @property
    def current_money(self) -> int:
        return self._current_money

    def has_enough_money(self, amount: int) -> bool:
        if amount < 0:
            raise ValueError("Amount cannot be negative.")
        return self._current_money >= amount

    def receive_money(self, number_of_towns: int) -> None:
        if not 0 <= number_of_towns < len(self._INCOME_BY_TOWNS):
            raise ValueError("Supplied towns must be between 0 and 20.")
        self._current_money += self._INCOME_BY_TOWNS[number_of_towns]

    def spend_money(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Amount cannot be negative.")
        if amount > self._current_money:
            raise ValueError("Insufficient money.")
        self._current_money -= amount
