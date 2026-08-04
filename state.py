class AppState:
    def __init__(self):
        self.user = None

    def is_logged_in(self):
        return self.user is not None

    def login(self, user):
        self.user = user

    def logout(self):
        self.user = None

app_state = AppState()