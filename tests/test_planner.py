import unittest

from scanner.planner import generate_circle_waypoints


class PlannerTest(unittest.TestCase):
    def test_generate_circle_waypoints_count_and_shape(self) -> None:
        points = generate_circle_waypoints([0.3, 0.0, 0.45], radius=0.1, z_height=0.45, num_points=8)
        self.assertEqual(len(points), 8)
        for p in points:
            self.assertEqual(set(p.keys()), {"idx", "xyz", "rpy"})
            self.assertEqual(len(p["xyz"]), 3)
            self.assertEqual(len(p["rpy"]), 3)

    def test_generate_circle_waypoints_min_points_validation(self) -> None:
        with self.assertRaises(ValueError):
            generate_circle_waypoints([0.3, 0.0, 0.45], radius=0.1, z_height=0.45, num_points=2)


if __name__ == "__main__":
    unittest.main()
