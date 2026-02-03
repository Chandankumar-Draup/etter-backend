"""Test the role adjacency model."""

from unittest import TestCase
from unittest.mock import patch

from ml_models.role_adjacency.role_adjacency import get_similar_roles
from ml_models.role_adjacency.title_to_role_api import TitleToRoleAPIException
from ml_models.role_adjacency.types import RoleAdjacencyInput, PredictedRole


class TestGetSimilarRoles(TestCase):
    def setUp(self):
        """Set up test data."""
        self.input_data: RoleAdjacencyInput = {
            "job_roles": "Software Engineer",
            "company": "Tech Corp",
            "top_k": 3,
        }

        self.mock_predicted_roles: list[PredictedRole] = [
            {"job_role": "Senior Software Engineer", "score": 0.95},
            {"job_role": "Full Stack Developer", "score": 0.88},
            {"job_role": "Backend Engineer", "score": 0.82},
        ]

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    def test_get_similar_roles_v1(self, mock_title_to_role):
        """Test get_similar_roles with version v1 (title-to-role API)."""
        mock_title_to_role.return_value = self.mock_predicted_roles

        result = get_similar_roles(self.input_data, version="v1")

        # Assert the API was called with correct data
        mock_title_to_role.assert_called_once_with(self.input_data)

        # Assert the result structure

        self.assertIsInstance(result, list)
        self.assertEqual(result, self.mock_predicted_roles)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["job_role"], "Senior Software Engineer")
        self.assertAlmostEqual(result[0]["score"], 0.95, places=2)

    @patch("ml_models.role_adjacency.role_adjacency.get_similar_roles_using_llm")
    def test_get_similar_roles_v2(self, mock_llm):
        """Test get_similar_roles with version v2 (LLM)."""
        mock_llm.return_value = self.mock_predicted_roles

        result = get_similar_roles(self.input_data, version="v2")

        # Assert the LLM API was called with correct data
        mock_llm.assert_called_once_with(self.input_data)

        # Assert the result structure
        self.assertIsInstance(result, list)
        self.assertEqual(result, self.mock_predicted_roles)
        self.assertEqual(len(result), 3)

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_embedding_model"
    )
    def test_get_similar_roles_v3(self, mock_embedding):
        """Test get_similar_roles with version v3 (embedding model)."""
        mock_embedding.return_value = self.mock_predicted_roles

        result = get_similar_roles(self.input_data, version="v3")

        # Assert the embedding API was called with correct data
        mock_embedding.assert_called_once_with(self.input_data)

        # Assert the result structure
        self.assertIsInstance(result, list)
        self.assertEqual(result, self.mock_predicted_roles)

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    def test_get_similar_roles_default_version(self, mock_title_to_role):
        """Test get_similar_roles with default version (should be v1)."""
        mock_title_to_role.return_value = self.mock_predicted_roles

        result = get_similar_roles(self.input_data)

        # Assert the title-to-role API was called (default is v1)
        mock_title_to_role.assert_called_once_with(self.input_data)

        # Assert the result structure
        self.assertIsInstance(result, list)
        self.assertEqual(result, self.mock_predicted_roles)

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    @patch("ml_models.role_adjacency.role_adjacency.get_similar_roles_using_llm")
    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_embedding_model"
    )
    def test_get_similar_roles_unsupported_version(
        self, mock_embedding, mock_llm, mock_title_to_role
    ):
        """Test get_similar_roles with unsupported version."""

        # Assert none of the APIs were called
        mock_title_to_role.assert_not_called()
        mock_llm.assert_not_called()
        mock_embedding.assert_not_called()

        # Raise ValueError
        self.assertRaises(ValueError, get_similar_roles, self.input_data, version="v99")

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    def test_get_similar_roles_empty_response(self, mock_title_to_role):
        """Test get_similar_roles when API returns empty list."""
        mock_title_to_role.return_value = []

        result = get_similar_roles(self.input_data, version="v1")

        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    def test_get_similar_roles_exception_handling(self, mock_title_to_role):
        """Test get_similar_roles exception handling."""
        mock_title_to_role.side_effect = TitleToRoleAPIException("API connection error")
        self.assertRaises(
            TitleToRoleAPIException, get_similar_roles, self.input_data, version="v1"
        )

    @patch("ml_models.role_adjacency.role_adjacency.get_similar_roles_using_llm")
    def test_get_similar_roles_v2_exception(self, mock_llm):
        """Test get_similar_roles v2 exception handling."""
        mock_llm.side_effect = Exception("Invalid input")
        self.assertRaises(Exception, get_similar_roles, self.input_data, version="v2")

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    def test_get_similar_roles_with_different_input(self, mock_title_to_role):
        """Test get_similar_roles with different input data."""
        different_input: RoleAdjacencyInput = {
            "role": "Data Scientist",
            "company": "AI Labs",
            "job_family": "Data Science",
        }

        mock_predicted_roles: list[PredictedRole] = [
            {"job_role": "Senior Data Scientist", "score": 0.92},
            {"job_role": "Machine Learning Engineer", "score": 0.85},
        ]
        mock_title_to_role.return_value = mock_predicted_roles

        result = get_similar_roles(different_input, version="v1")

        # Assert the result matches the different input
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["job_role"], "Senior Data Scientist")

    @patch(
        "ml_models.role_adjacency.role_adjacency.get_similar_roles_using_title_to_role_api"
    )
    def test_get_similar_roles_preserves_input_fields(self, mock_title_to_role):
        """Test that get_similar_roles preserves all input fields in the result."""
        mock_title_to_role.return_value = self.mock_predicted_roles

        result = get_similar_roles(self.input_data, version="v1")

        # Assert all input fields are preserved in the result
        self.assertEqual(result, self.mock_predicted_roles)
