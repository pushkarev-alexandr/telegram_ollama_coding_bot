import asyncio

from handlers import chat, tool_permission_callback
from test_mocks import Context, Update

async def main():
    update = Update()
    context = Context()
    update.message.text = "Какие файлы и папки есть в текущей директории?"
    await chat(update, context)
    await tool_permission_callback(update, context)

if __name__ == "__main__":
    asyncio.run(main())

