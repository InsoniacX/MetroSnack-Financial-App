class AppState:
    def __init__(self):
        self.user = None
        self.session_expired = False

    def is_logged_in(self):
        return self.user is not None

    def login(self, user):
        self.user = user
        self.session_expired = False

    def logout(self, session_expired=False):
        self.user = None
        self.session_expired = session_expired

    def consume_session_expired(self):
        expired = self.session_expired
        self.session_expired = False
        return expired

app_state = AppState()
