"""Test the title to role API."""

from unittest import TestCase
from unittest.mock import patch
from unittest.mock import Mock

from ml_models.role_adjacency.title_to_role_api import get_title_to_role_api


class TestTitleToRoleAPI(TestCase):
    @patch("ml_models.role_adjacency.title_to_role_api.requests.post")
    def test_get_title_to_role_api(self, mock_post):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "results": [
                {
                    "job_title": "presenter",
                    "predicted_roles": [
                        {"job_role": "Show Host", "score": 0.7130289077758789},
                        {"job_role": "Radio Host", "score": 0.5949971675872803},
                        {
                            "job_role": "Presentation Specialist",
                            "score": 0.5646853446960449,
                        },
                        {"job_role": "Events Specialist", "score": 0.554550290107727},
                        {"job_role": "Broadcast Director", "score": 0.5523744225502014},
                    ],
                }
            ]
        }
        mock_post.return_value = mock_response

        result = get_title_to_role_api("presenter", top_k=5)

        # Assert the function returns a dict (response.json())
        self.assertIsInstance(result, dict)
        self.assertEqual(result["results"][0]["job_title"], "presenter")
        self.assertEqual(len(result["results"][0]["predicted_roles"]), 5)
        self.assertEqual(
            result["results"][0]["predicted_roles"][0]["job_role"], "Show Host"
        )
        self.assertAlmostEqual(
            result["results"][0]["predicted_roles"][0]["score"],
            0.7130289077758789,
            places=6,
        )
        self.assertEqual(
            result["results"][0]["predicted_roles"][1]["job_role"], "Radio Host"
        )
        self.assertAlmostEqual(
            result["results"][0]["predicted_roles"][1]["score"],
            0.5949971675872803,
            places=6,
        )
        self.assertEqual(
            result["results"][0]["predicted_roles"][2]["job_role"],
            "Presentation Specialist",
        )
        self.assertAlmostEqual(
            result["results"][0]["predicted_roles"][2]["score"],
            0.5646853446960449,
            places=6,
        )

    @patch("ml_models.role_adjacency.title_to_role_api.requests.post")
    def test_get_title_to_role_api_error(self, mock_post):
        mock_post.side_effect = Exception("Internal Server Error")
        result = get_title_to_role_api("presenter", top_k=5)
        mock_post.assert_called_once_with(
            "http://127.0.0.1:8080/title-to-role",
            headers={"Content-Type": "application/json", "charset": "utf-8"},
            json={
                "input_titles": ["presenter"],
                "top_k": 5,
                "return_score": True,
                "base_threshold": False,
            },
        )
        self.assertIsNone(result)
