from sqlalchemy.orm import Session


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str):
        raise NotImplementedError("User lookup is not implemented yet.")

    def create_user(self, email: str, display_name: str, password: str):
        raise NotImplementedError("User creation is not implemented yet.")
