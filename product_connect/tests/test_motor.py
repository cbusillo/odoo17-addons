from datetime import date
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged
from parameterized import parameterized


@tagged("post_install", "-at_install")
class TestMotor(common.TransactionCase):

    def setUp(self) -> None:
        super(TestMotor, self).setUp()
        self.Motor = self.env["motor"]
        self.Manufacturer = self.env["product.manufacturer"]
        self.Stroke = self.env["motor.stroke"]
        self.Configuration = self.env["motor.configuration"]
        self.Color = self.env["product.color"]

        # Create test data
        self.manufacturer = self.Manufacturer.create({"name": "Test Manufacturer", "is_motor_manufacturer": True})
        self.stroke = self.Stroke.search([]).first()
        self.configuration = self.Configuration.create({"name": "4 Cylinder"})
        self.color = self.Color.create({"name": "Black"})

    @parameterized.expand(
        [
            ("valid_hp", 100, True),
            ("zero_hp", 0, True),
            ("max_hp", 600, True),
            ("negative_hp", -1, False),
            ("over_max_hp", 601, False),
        ]
    )
    def test_horsepower_constraint(self, name, hp_value, should_pass) -> None:
        if should_pass:
            motor = self.Motor.create([{"manufacturer": self.manufacturer.id, "horsepower": hp_value}])
            self.assertEqual(motor.horsepower, hp_value)
        else:
            with self.assertRaises(ValidationError):
                self.Motor.create([{"manufacturer": self.manufacturer.id, "horsepower": hp_value}])

    @parameterized.expand(
        [
            ("year_with_letters", "2023abc", "2023"),
            ("year_only_numbers", "2023", "2023"),
            ("empty_year", "", ""),
        ]
    )
    def test_sanitize_year(self, name, input_year, expected_year) -> None:
        vals = {"year": input_year}
        sanitized = self.Motor._sanitize_vals(vals)
        self.assertEqual(
            sanitized["year"], expected_year, f"{name} with {input_year} should be sanitized to {expected_year}"
        )

    @parameterized.expand(
        [
            (
                "mixed_case_with_numbers",
                {"year": "2023abc", "model": "Test Model 123", "serial_number": "abc-123-XYZ"},
                {"year": "2023", "model": "TEST MODEL 123", "serial_number": "ABC-123-XYZ"},
            ),
            (
                "lowercase_with_spaces",
                {"year": " 2024 ", "model": "  lower case  model  ", "serial_number": "  abc 123  "},
                {"year": "2024", "model": "LOWER CASE  MODEL", "serial_number": "ABC 123"},
            ),
            (
                "empty_values",
                {"year": "", "model": "", "serial_number": ""},
                {"year": "", "model": "", "serial_number": ""},
            ),
        ]
    )
    def test_sanitize_vals(self, name, input_vals, expected_vals) -> None:
        # Create a motor with the input values
        motor = self.Motor.create(
            [
                {
                    "manufacturer": self.manufacturer.id,
                    "year": input_vals["year"],
                    "model": input_vals["model"],
                    "serial_number": input_vals["serial_number"],
                }
            ]
        )

        # Check if the motor's attributes match the expected sanitized values
        self.assertEqual(motor.year, expected_vals["year"], f"Year not sanitized correctly for {name}")
        self.assertEqual(motor.model, expected_vals["model"], f"Model not sanitized correctly for {name}")
        self.assertEqual(
            motor.serial_number, expected_vals["serial_number"], f"Serial number not sanitized correctly for {name}"
        )

    @parameterized.expand(
        [
            (
                "with_hp",
                "M-000001",
                "2023",
                "Test Manufacturer",
                100,
                "TEST123",
                "ABC123",
                "M-000001 2023 Test Manufacturer 100 HP TEST123 - ABC123",
            ),
            (
                "without_hp",
                "M-000002",
                "2023",
                "Test Manufacturer",
                0,
                "TEST123",
                "ABC123",
                "M-000002 2023 Test Manufacturer TEST123 - ABC123",
            ),
            (
                "without_serial",
                "M-000003",
                "2023",
                "Test Manufacturer",
                100,
                "TEST123",
                "",
                "M-000003 2023 Test Manufacturer 100 HP TEST123",
            ),
        ]
    )
    def test_compute_display_name(
        self, name, motor_number, year, manufacturer_name, hp, model, serial, expected_name
    ) -> None:
        manufacturer = self.Manufacturer.create({"name": manufacturer_name, "is_motor_manufacturer": True})
        motor = self.Motor.create(
            [
                {
                    "motor_number": motor_number,
                    "manufacturer": manufacturer.id,
                    "horsepower": hp,
                    "model": model,
                    "year": year,
                    "serial_number": serial,
                }
            ]
        )
        self.assertEqual(motor.display_name, expected_name, f"Display name not computed correctly for {name}")

    @parameterized.expand(
        [
            ("four_cylinder", "4 Cylinder", 4),
            ("six_cylinder", "6 Cylinder", 6),
            ("eight_cylinder", "8 Cylinder", 8),
            ("no_number", "V Engine", 0),
        ]
    )
    def test_get_cylinder_count(self, name, config_name, expected_count) -> None:
        configuration = self.Configuration.create({"name": config_name})
        motor = self.Motor.create([{"manufacturer": self.manufacturer.id, "configuration": configuration.id}])
        self.assertEqual(
            motor._get_cylinder_count(), expected_count, f"Cylinder count not computed correctly for {name}"
        )

    def test_get_years(self) -> None:
        # Mock the fields.Date.today() to return a fixed date
        with patch.object(fields.Date, "today", return_value=date(2023, 1, 1)):
            years = self.Motor._get_years()

            # Test the length
            expected_length = 2023 - 1960 + 2  # +2 because it includes 2023 and 2024
            self.assertEqual(len(years), expected_length, "Incorrect number of years returned")

            # Test the range
            self.assertEqual(years[0], ("2024", "2024"), "First year should be next year")
            self.assertEqual(years[-1], ("1960", "1960"), "Last year should be 1960")

            # Test the format
            for year_tuple in years:
                self.assertTrue(all(isinstance(y, str) for y in year_tuple), "Year should be string")
                self.assertEqual(year_tuple[0], year_tuple[1], "Year tuple should have matching values")

            # Test the order
            self.assertTrue(
                all(int(years[i][0]) > int(years[i + 1][0]) for i in range(len(years) - 1)),
                "Years should be in descending order",
            )
