from abc import ABC, abstractmethod
from typing import List, Tuple


class Parser(ABC):

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.language = self.__class__.__name__.replace('Parser', '')

    @abstractmethod
    def find_dependency_files(self) -> List[str]:
        pass

    @abstractmethod
    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        pass

    def get_dependencies(self) -> List[Tuple[str, str, str]]:
        dependency_files = self.find_dependency_files()
        all_dependencies = []

        for file_path in dependency_files:
            dependencies = self.parse_dependencies(file_path)
            all_dependencies.extend(dependencies)

        return all_dependencies