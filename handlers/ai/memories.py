import json
import os
from typing import Optional


class Memories:
    def __init__(self):
        self._memories: dict = {}

        if os.path.isfile(".ai-memories.json"):
            with open(".ai-memories.json", "r", encoding="utf-8") as fd:
                self._memories = json.load(fd)
    
    def save_memory(self, user: str, memory: str):
        user = user.strip(":").strip(" ")

        if user not in self._memories:
            self._memories[user] = []

        self._memories[user].append(memory)

        if len(self._memories[user]) > 15:
            self._memories[user] = self._memories[user][-15:]

        self.save_to_file()
    
    def get_memory(self, user: str) -> Optional[str]:
        memory = self._memories.get(user, None)
        return f"MEMORY {user}: {memory}"
    
    def get_all_memories(self) -> str:
        output = ""
        for user, memory in self._memories.items():
            line = f"MEMORY {user}: {memory}\n"
            output += line
        if not output:
            return "None"
        return output
    
    def save_to_file(self):
        with open(".ai-memories.json", "w", encoding="utf-8") as fd:
            json.dump(self._memories, fd, ensure_ascii=False, indent=4)
