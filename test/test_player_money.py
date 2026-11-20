import unittest

from power_grid.player_money import PlayerMoney
from power_grid.simple_types import PlayerColor


class TestPlayerMoney(unittest.TestCase):
    # Constructor tests

    def test_default_starting_money(self) -> None:
        money = PlayerMoney(PlayerColor.BLUE)
        self.assertEqual(money.current_money, 50)

    def test_custom_starting_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 125)
        self.assertEqual(money.current_money, 125)

    def test_negative_starting_money(self) -> None:
        with self.assertRaises(ValueError):
            PlayerMoney(PlayerColor.GREEN, -1)

    # has_enough_money tests

    def test_has_enough_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        self.assertTrue(money.has_enough_money(50))

    def test_does_not_have_enough_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        self.assertFalse(money.has_enough_money(80))

    def test_has_exact_amount_of_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        self.assertTrue(money.has_enough_money(75))

    def test_negative_amount(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        with self.assertRaises(ValueError):
            money.has_enough_money(-1)

    # spend_money tests

    def test_spend_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        money.spend_money(30)
        self.assertEqual(money.current_money, 45)

    def test_spend_all_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        money.spend_money(75)
        self.assertEqual(money.current_money, 0)

    def test_spend_negative_amount(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        with self.assertRaises(ValueError):
            money.spend_money(-1)
        self.assertEqual(money.current_money, 75)

    def test_spend_more_money_than_available(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 75)
        with self.assertRaises(ValueError):
            money.spend_money(100)
        self.assertEqual(money.current_money, 75)

    # receive_money tests

    def test_receive_money(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 50)
        money.receive_money(6)
        self.assertEqual(money.current_money, 123)

    def test_receive_money_for_all_town_counts(self) -> None:
        income = [
            10, 22, 33, 44, 54, 64, 73,
            82, 90, 98, 105, 112, 118, 124,
            129, 134, 138, 142, 145, 148, 150
        ]

        for number_of_towns in range(21):
            money = PlayerMoney(PlayerColor.RED, 50)
            money.receive_money(number_of_towns)
            expected_money = 50 + income[number_of_towns]
            self.assertEqual(
                money.current_money,
                expected_money,
                f"Wrong income for {number_of_towns} towns"
            )

    def test_receive_money_for_negative_town_count(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 50)
        with self.assertRaises(ValueError):
            money.receive_money(-1)
        self.assertEqual(money.current_money, 50)

    def test_receive_money_for_more_than_20_towns(self) -> None:
        money = PlayerMoney(PlayerColor.RED, 50)
        with self.assertRaises(ValueError):
            money.receive_money(21)
        self.assertEqual(money.current_money, 50)


if __name__ == "__main__":
    unittest.main()
