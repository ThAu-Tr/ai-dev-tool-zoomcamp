from django.test import SimpleTestCase

from household.garden import GARDEN_STAGES, GardenStage, calculate_garden_stage


class GardenStageTests(SimpleTestCase):
    def test_stage_definition_is_ordered_and_complete(self):
        self.assertEqual(
            GARDEN_STAGES,
            (
                GardenStage(0, "empty_soil", "Empty soil"),
                GardenStage(25, "seed", "Seed"),
                GardenStage(75, "sprout", "Sprout"),
                GardenStage(150, "small_plant", "Small plant"),
                GardenStage(300, "flowers", "Flowers"),
                GardenStage(500, "bushes", "Bushes"),
                GardenStage(800, "tree", "Tree"),
                GardenStage(1200, "richer_garden", "Richer garden"),
            ),
        )

    def test_zero_xp_returns_empty_soil(self):
        stage = calculate_garden_stage(0)

        self.assertEqual(stage.identifier, "empty_soil")
        self.assertEqual(stage.label, "Empty soil")

    def test_values_immediately_below_positive_thresholds(self):
        expected_stages = (
            (24, "empty_soil", "Empty soil"),
            (74, "seed", "Seed"),
            (149, "sprout", "Sprout"),
            (299, "small_plant", "Small plant"),
            (499, "flowers", "Flowers"),
            (799, "bushes", "Bushes"),
            (1199, "tree", "Tree"),
        )

        for lifetime_xp, identifier, label in expected_stages:
            with self.subTest(lifetime_xp=lifetime_xp):
                stage = calculate_garden_stage(lifetime_xp)
                self.assertEqual(stage.identifier, identifier)
                self.assertEqual(stage.label, label)

    def test_values_at_positive_thresholds(self):
        for expected_stage in GARDEN_STAGES[1:]:
            with self.subTest(lifetime_xp=expected_stage.threshold):
                self.assertEqual(
                    calculate_garden_stage(expected_stage.threshold), expected_stage
                )

    def test_value_above_final_threshold_remains_richer_garden(self):
        stage = calculate_garden_stage(1201)

        self.assertEqual(stage.identifier, "richer_garden")
        self.assertEqual(stage.label, "Richer garden")

    def test_negative_xp_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_garden_stage(-1)

    def test_non_integer_xp_is_rejected(self):
        invalid_values = (True, False, 25.0, "25", None)

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    calculate_garden_stage(value)
