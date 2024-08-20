from handlers.ai.memories import Memories


memory = Memories()


tools = [
   {
       "name": "remember",
       "description": "Запомнить что-либо и записать это в память. Можно перезаписывать память. Записывай в память очень много информации. Вызывай эту функцию минимум 1 раз за ответ",
       "parameter_definitions": {
           "memory_slot": {
               "description": "Название слота памяти с которым происходит операция.",
               "type": "str",
               "required": True
           },
           "memory": {
               "description": "Данные которые нужно запомнить.",
               "type": "str",
               "required": True
           }
       }
   }
]

functions_map = {
    "remember": memory.save_memory,
}
