class Message:
    def __init__(self, text: str | None = None):
        self.text = text

    async def reply_text(self, text: str, reply_markup: None = None):
        print(text)

    async def reply_markdown(self, text: str, reply_markup: None = None):
        print(text)


class Chat:
    id: int


class User:
    id: int


class CallbackQuery:
    def __init__(self):
        self.data = "tool_yes"

    async def answer(self):
        print("Убрал индикатор загрузки")

    async def edit_message_reply_markup(self, reply_markup: None):
        print("Убрал кнопки")


class Update:
    def __init__(self):
        self.message = Message()
        self.effective_message = self.message
        self.effective_chat = Chat()
        self.effective_chat.id = 386169716
        self.effective_user = User()
        self.effective_user.id = 386169716
        self.callback_query = CallbackQuery()


class Bot:
    async def send_chat_action(self, chat_id: int, action: str):
        print(f"Sending chat action: {action} to chat {chat_id}")


class Context:
    def __init__(self):
        self.user_data = {}
        self.bot = Bot()
