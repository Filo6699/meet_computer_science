import json
import os
from typing import Optional


class Memories:
    def __init__(self):
        self._memories: list = []

        if os.path.isfile(".ai-memories.json"):
            with open(".ai-memories.json", "r", encoding="utf-8") as fd:
                self._memories = json.load(fd)

    def save_memory(self, memory: str):
        self._memories.append(memory)
        self.save_to_file()

    def get_all_memories(self) -> str:
        return "\n".join(self._memories)

    def save_to_file(self):
        with open(".ai-memories.json", "w", encoding="utf-8") as fd:
            json.dump(self._memories, fd, ensure_ascii=False, indent=4)
