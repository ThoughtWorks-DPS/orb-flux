import difflib
import os
import time

from pathlib import Path

from github import Auth
from github import GitCommit
from github import Github
from github import InputGitTreeElement
from github import UnknownObjectException
from github import GithubException


class RepositoryService:
    def __init__(self, org_name, repo_name, auth_token):
        g = Github(auth=(Auth.Token(auth_token)))
        org_repo = '%s/%s' % (org_name, repo_name)
        print('Setting Github repository connectivity to {}'.format(org_repo))
        self.repo = g.get_repo(org_repo)

    def create_blob(self, file):
        contents = Path(file).read_text()
        return self.repo.create_git_blob(contents, 'utf-8')

    @staticmethod
    def __create_tree_element(path, sha):
        print('Adding {} to tree with sha {}'.format(path, sha))
        return InputGitTreeElement(path, '100644', 'blob', sha=sha)

    def prepare_tree_elements(self, local_files, remote_file_references):
        blobs = []
        for index, filename in enumerate(local_files):
            if self.__is_diff(filename, remote_file_references[index]):
                blobs.append({'blob': self.create_blob(filename), 'remote_ref': remote_file_references[index]})

        tree_elements = []
        if blobs:
            for blob in blobs:
                tree_element = self.__create_tree_element(blob['remote_ref'], blob['blob'].sha)
                tree_elements.append(tree_element)
        else:
            return None
        return tree_elements

    def create_commit(self, tree_elements, branch, message) -> GitCommit:
        base_tree = self.repo.get_git_tree(branch, True)

        git_tree = self.repo.create_git_tree(tree_elements, base_tree)
        print('Creating git commit {} from tree on branch {}'.format(base_tree.sha, branch))
        return self.repo.create_git_commit(
            message, git_tree, [self.repo.get_git_commit(base_tree.sha)]
        )

    def publish(self, tree_elements, message, branch):
        wait_seconds = 15
        for n in range(5):
            try:
                commit = self.create_commit(tree_elements, branch, message)
                git_ref = self.repo.get_git_ref('heads/{}'.format(branch))
                git_ref_sha = git_ref.object.sha
                print('Current head of ref {} is {}'.format(git_ref.ref, git_ref_sha))
                print('Committing to {} with sha {}'.format(git_ref.ref, commit.sha))
                commit_sha = commit.sha
                git_ref.edit(commit.sha)
            except GithubException:
                print('Exception occurred while committing: {}'.format(GithubException))
                print('Waiting {} seconds before trying again...'.format(wait_seconds))
                time.sleep(wait_seconds)
                continue
            else:
                print('Committed successfully!')
                file_location = './commit-sha.txt'
                print(f'Writing commit sha {commit_sha} to {file_location}')
                f = open(file_location, 'w')
                f.write(commit_sha + '\n')
                f.close()
                return
        print('Done retrying')
        raise RuntimeError('Unable to commit after 5 attempts')

    def __is_diff(self, filename, remote_ref):
        print()
        print('Diffing {} against {}...'.format(filename, remote_ref))
        try:
            contents = self.repo.get_contents(remote_ref, 'main')
            filename_text = Path(filename).read_text()
            remote_ref_text = contents.decoded_content.decode('ascii')
            for line in difflib.unified_diff(a=filename_text.splitlines(),
                                             b=remote_ref_text.splitlines(),
                                             lineterm=''):
                print(line + '\n')

            is_diff = filename_text != remote_ref_text
            print('Changes found') if is_diff else print('No changes found')
            return is_diff
        except UnknownObjectException:
            print('This file is new and does not exist in the target repository yet')
            return True


class DirectoryService:
    def __init__(self, dir):
        self.dir = dir

    def get_files_paths_recursively(self):
        folder = Path(self.dir)
        files = []
        for item in folder.rglob('*'):
            if item.suffix != '.tpl' and item.is_file():
                files.append(item.as_posix())
        return files


class Orchestrator:
    def prepare_files_from_environment(self, environment_variable):
        return [x.strip().strip('\"') for x in os.environ[environment_variable].split(',')]

    def get_files(self):
        local_refs = self.prepare_files_from_environment('LOCAL_REFS')
        remote_refs = self.prepare_files_from_environment('REMOTE_REFS')
        if os.environ['IS_FILES'] == 'true':
            return {'local_refs': local_refs, 'remote_refs': remote_refs}
        else:
            remote_files = []
            local_files = []
            for index, local_dir in enumerate(local_refs):
                files_in_directory = DirectoryService(local_dir).get_files_paths_recursively()
                remote_files += [sub.replace(local_dir, remote_refs[index]) for sub in files_in_directory]
                local_files += files_in_directory

            return {'local_refs': local_files, 'remote_refs': remote_files}


if __name__ == '__main__':
    repository = RepositoryService(os.environ['ORG'], os.environ['REPO'], os.environ['GITHUB_TOKEN'])
    orchestrator = Orchestrator()
    files = orchestrator.get_files()
    tree_elements = repository.prepare_tree_elements(files['local_refs'], files['remote_refs'])
    # commit the changes if there are any
    if tree_elements is not None:
        print('Committing changes...', end='')
        repository.publish(
            tree_elements,
            'push from %s build %s' % ((os.environ['CIRCLE_PROJECT_REPONAME']), (os.environ['CIRCLE_BUILD_NUM'])),
            'main'
        )
    else:
        print('No changes. Skipping commit.')
