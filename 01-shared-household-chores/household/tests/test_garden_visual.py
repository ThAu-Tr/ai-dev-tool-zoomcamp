from django.template import Context, Template
from django.test import SimpleTestCase
from pathlib import Path

from household.garden import GARDEN_STAGES, GardenStage


class GardenVisualTemplateTests(SimpleTestCase):
    def render_garden(self, stage, member_name="Alex"):
        return Template(
            '{% include "household/includes/garden.html" with stage=stage member_name=member_name %}'
        ).render(Context({"stage": stage, "member_name": member_name}))

    def test_every_approved_stage_renders_its_visible_and_accessible_name(self):
        for stage in GARDEN_STAGES:
            with self.subTest(stage=stage.identifier):
                rendered = self.render_garden(stage)

                expected_name = f"Alex's garden — {stage.label}"
                self.assertEqual(rendered.count("<svg"), 1)
                self.assertIn(f'aria-label="{expected_name}"', rendered)
                self.assertIn(f">{expected_name}</figcaption>", rendered)
                self.assertIn('role="img"', rendered)
                self.assertIn('aria-hidden="true"', rendered)

    def test_stage_artwork_is_cumulative_and_distinct(self):
        rendered_by_stage = {
            stage.identifier: self.render_garden(stage) for stage in GARDEN_STAGES
        }

        self.assertNotIn('rx="9"', rendered_by_stage["empty_soil"])
        self.assertIn('rx="9"', rendered_by_stage["seed"])
        self.assertIn('M160 147v-32', rendered_by_stage["sprout"])
        self.assertIn('M160 147V91', rendered_by_stage["small_plant"])
        self.assertIn('cx="130" cy="89"', rendered_by_stage["flowers"])
        self.assertIn('M52 150c0-25', rendered_by_stage["bushes"])
        self.assertIn('M262 143V67', rendered_by_stage["tree"])
        self.assertIn('M74 130c-7-30', rendered_by_stage["richer_garden"])

    def test_unexpected_identifier_falls_back_to_bare_soil_and_keeps_label(self):
        rendered = self.render_garden(GardenStage(0, "unexpected", "Mystery garden"))

        self.assertIn("Alex's garden — Mystery garden", rendered)
        self.assertNotIn('rx="9"', rendered)
        self.assertNotIn('M160 147v-32', rendered)

    def test_multiple_instances_keep_their_own_member_names_and_stages(self):
        rendered = Template(
            '{% include "household/includes/garden.html" with stage=first member_name="Alex" %}'
            '{% include "household/includes/garden.html" with stage=second member_name="Sam" %}'
        ).render(Context({"first": GARDEN_STAGES[0], "second": GARDEN_STAGES[-1]}))

        self.assertEqual(rendered.count("<svg"), 2)
        self.assertIn("Alex's garden — Empty soil", rendered)
        self.assertIn("Sam's garden — Richer garden", rendered)

    def test_artwork_stays_within_a_responsive_bounded_container(self):
        stylesheet = Path("household/static/household/site.css").read_text()

        self.assertIn(".garden-visual { width: min(100%, 32rem);", stylesheet)
        self.assertIn(".garden-visual__art { display: block; width: 100%; height: auto;", stylesheet)
        self.assertIn("@media (min-width: 80rem)", stylesheet)
