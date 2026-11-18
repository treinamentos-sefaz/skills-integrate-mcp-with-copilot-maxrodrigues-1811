import unittest

import src.app as school_app


class ActivityDataTests(unittest.TestCase):
    def test_activities_have_categories_and_schedule_sort_order(self) -> None:
        activities = school_app.get_activities()

        self.assertEqual(
            {activity["category"] for activity in activities.values()},
            {"Academic", "Arts", "Sports"},
        )
        self.assertTrue(
            all(
                isinstance(activity["schedule_sort_order"], int)
                for activity in activities.values()
            )
        )

        chronological_names = sorted(
            activities,
            key=lambda name: activities[name]["schedule_sort_order"],
        )
        self.assertEqual(
            chronological_names[:3],
            ["Gym Class", "Drama Club", "Programming Class"],
        )


if __name__ == "__main__":
    unittest.main()
