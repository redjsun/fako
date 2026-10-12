"""Cria (ou promove) um usuário administrador para a curadoria de conteúdo.

Uso: python -m app.seeds.create_admin <usuario> <senha>
"""

import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User, UserProgress
from app.repositories.user_repository import UserRepository


def main(username: str, password: str) -> None:
    with SessionLocal.begin() as db:
        users = UserRepository(db)
        user = users.get_by_username(username)
        if user is None:
            user = users.add(User(username=username, password_hash=hash_password(password)))
            db.add(UserProgress(user_id=user.id))
        user.is_admin = True
    print(f"Administrador '{username}' pronto.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: python -m app.seeds.create_admin <usuario> <senha>")
    main(sys.argv[1], sys.argv[2])
