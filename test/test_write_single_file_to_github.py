import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.scripts.python.write_single_file_to_github import RepositoryService, DirectoryService, Orchestrator


class GithubServiceTest(unittest.TestCase):

    def setUp(self):
        self.test_org = "TEST_ORG"
        self.test_repo_name = "TEST_REPO_NAME"
        self.test_remotefile_names = ["TEST_REMOTEFILE"]
        self.test_local_files = [os.path.dirname(__file__) + "/local_file_fixture.txt"]
        self.test_github_token = "TEST_GITHUB_TOKEN"

    @patch('src.scripts.python.write_single_file_to_github.Auth', autospec=True)
    @patch('src.scripts.python.write_single_file_to_github.Github', autospec=True)
    def test_configures_github_library_correctly(self, mock_github, mock_auth):
        RepositoryService(self.test_org, self.test_repo_name, self.test_github_token)
        mock_auth.Token.assert_called_once_with(self.test_github_token)
        mock_github.assert_called_once_with(auth=mock_auth.Token(self.test_github_token))

    @patch('src.scripts.python.write_single_file_to_github.Auth', autospec=True)
    @patch('src.scripts.python.write_single_file_to_github.Github', autospec=True)
    def test_it_can_get_a_repo(self, mock_github, _):
        RepositoryService(self.test_org, self.test_repo_name, self.test_github_token)
        mock_github.return_value.get_repo.assert_called_once_with("TEST_ORG/TEST_REPO_NAME")


class DirectoryServiceTest(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.dirname(__file__) + "/../resources"
        service = DirectoryService(self.directory)
        self.files = service.get_files_paths_recursively()

    def test_returns_all_file_paths_in_given_directory(self):
        self.assertEqual(len(self.files), 2)
        self.assertIn(self.directory + "/some.file.py", self.files)
        self.assertIn(self.directory + "/test.yaml", self.files)

    def test_excludes_tpl_extension_files(self):
        self.assertEqual(len(self.files), 2)
        self.assertNotIn(self.directory + "/some_directory/file.some.tpl", self.files)

    def test_excludes_subdirectories_in_list(self):
        self.assertEqual(len(self.files), 2)
        self.assertNotIn(self.directory + "/some_directory", self.files)


class OrchestratorTest(unittest.TestCase):
    def test_prepare_files_from_environment(self):
        files = "file1,file2,file3"
        env_var = "LOCAL_REFS"
        os.environ[env_var] = files

        service = Orchestrator()
        files = service.prepare_files_from_environment(env_var)

        self.assertEqual(files, ["file1", "file2", "file3"])

    def test_returns_files_when_is_files_is_true(self):
        os.environ["LOCAL_REFS"] = "file1,file2,file3"
        os.environ["REMOTE_REFS"] = "remote1,remote2,remote3"
        os.environ["IS_FILES"] = "true"

        service = Orchestrator()
        files = service.get_files()

        self.assertEqual(files['local_refs'], ["file1", "file2", "file3"])
        self.assertEqual(files['remote_refs'], ["remote1", "remote2", "remote3"])

    def test_returns_files_from_folders_when_is_files_is_false(self):
        current_dir = os.path.dirname(__file__)
        os.environ["LOCAL_REFS"] = current_dir + "/../resources"
        os.environ["REMOTE_REFS"] = "root/sub"
        os.environ["IS_FILES"] = "false"

        service = Orchestrator()
        files = service.get_files()
        self.assertCountEqual(
            [current_dir + "/../resources/some.file.py", current_dir + "/../resources/test.yaml"],
            files['local_refs']
        )
        self.assertCountEqual(
            ["root/sub/some.file.py", "root/sub/test.yaml"],
            files['remote_refs']
        )

        for index, local_ref in enumerate(files['local_refs']):
            remote_ref = files['remote_refs'][index]
            self.assertEqual(local_ref[len(os.environ["LOCAL_REFS"]):], remote_ref[len(os.environ["REMOTE_REFS"]):])


if __name__ == '__main__':
    unittest.main()
