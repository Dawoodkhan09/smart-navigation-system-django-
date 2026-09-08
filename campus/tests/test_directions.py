from django.test import SimpleTestCase

from campus.services.directions import bearing, steps_from_path, turn_word


class BearingTests(SimpleTestCase):
    def test_due_north(self):
        self.assertAlmostEqual(bearing((0, 0), (1, 0)), 0, delta=0.01)

    def test_due_east(self):
        self.assertAlmostEqual(bearing((0, 0), (0, 1)), 90, delta=0.01)

    def test_due_south(self):
        self.assertAlmostEqual(bearing((0, 0), (-1, 0)), 180, delta=0.01)

    def test_due_west(self):
        self.assertAlmostEqual(bearing((0, 0), (0, -1)), 270, delta=0.01)

    def test_accepts_dicts(self):
        a = {'latitude': 0, 'longitude': 0}
        b = {'latitude': 1, 'longitude': 0}
        self.assertAlmostEqual(bearing(a, b), 0, delta=0.01)

    def test_result_always_in_range(self):
        self.assertGreaterEqual(bearing((10, 10), (-10, -10)), 0)
        self.assertLess(bearing((10, 10), (-10, -10)), 360)


class TurnWordTests(SimpleTestCase):
    def test_small_change_is_straight(self):
        self.assertEqual(turn_word(0, 10), 'Continue straight')
        self.assertEqual(turn_word(0, 350), 'Continue straight')

    def test_slight_right(self):
        self.assertEqual(turn_word(0, 40), 'Turn slight right')

    def test_slight_left(self):
        self.assertEqual(turn_word(0, 320), 'Turn slight left')

    def test_turn_right(self):
        self.assertEqual(turn_word(0, 90), 'Turn right')

    def test_turn_left(self):
        self.assertEqual(turn_word(0, 270), 'Turn left')

    def test_sharp_right(self):
        self.assertEqual(turn_word(0, 170), 'Turn sharp right')

    def test_sharp_left(self):
        self.assertEqual(turn_word(0, 190), 'Turn sharp left')

    def test_wraps_around_0_360_boundary(self):
        # 355 -> 5 is a 10-degree turn, not a 350-degree one.
        self.assertEqual(turn_word(355, 5), 'Continue straight')

    def test_threshold_boundaries(self):
        # Exactly on a boundary belongs to the *next* tier up.
        self.assertEqual(turn_word(0, 20), 'Turn slight right')
        self.assertEqual(turn_word(0, 55), 'Turn right')
        self.assertEqual(turn_word(0, 125), 'Turn right')
        self.assertEqual(turn_word(0, 126), 'Turn sharp right')


class StepsFromPathTests(SimpleTestCase):
    def test_empty_or_single_point_has_no_steps(self):
        self.assertEqual(steps_from_path([]), [])
        self.assertEqual(steps_from_path([{'latitude': 0, 'longitude': 0, 'name': 'A'}]), [])

    def test_two_point_path_has_a_head_step_and_an_arrive_step(self):
        path = [
            {'latitude': 0, 'longitude': 0, 'name': 'Gate'},
            {'latitude': 1, 'longitude': 0, 'name': 'Library'},
        ]
        steps = steps_from_path(path)

        self.assertEqual(len(steps), 2)
        self.assertTrue(steps[0]['instruction'].startswith('Head '))
        self.assertEqual(steps[0]['from'], 'Gate')
        self.assertEqual(steps[0]['to'], 'Library')
        self.assertGreater(steps[0]['distance_m'], 0)

        self.assertEqual(steps[1]['instruction'], 'Arrive at Library')
        self.assertEqual(steps[1]['distance_m'], 0.0)

    def test_three_point_path_reports_the_turn_at_the_middle_node(self):
        path = [
            {'latitude': 0, 'longitude': 0, 'name': 'A'},
            {'latitude': 1, 'longitude': 0, 'name': 'B'},  # walk north
            {'latitude': 1, 'longitude': 1, 'name': 'C'},  # then east = turn right
        ]
        steps = steps_from_path(path)

        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[1]['instruction'], 'Turn right')
        self.assertEqual(steps[2]['instruction'], 'Arrive at C')
