"""Cria (ou promove) um usuário administrador para a curadoria de conteúdo.

Uso: python -m app.seeds.create_admin <usuario> [senha]

Sem a senha nos argumentos, ela é pedida no terminal (não fica no histórico do shell nem na
lista de processos).
"""

import sys
from getpass import getpass

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


def pedir_senha() -> str:
    senha = getpass("Senha do administrador: ")
    if senha != getpass("Repita a senha: "):
        sys.exit("As senhas não conferem.")
    return senha


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit("Uso: python -m app.seeds.create_admin <usuario> [senha]")
    senha = sys.argv[2] if len(sys.argv) == 3 else pedir_senha()
    if len(senha) < 8 or len(senha.encode()) > 72:
        sys.exit("A senha precisa ter de 8 caracteres a 72 bytes.")
    main(sys.argv[1], senha)
