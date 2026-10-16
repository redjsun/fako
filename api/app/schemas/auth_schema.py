"""DTOs de cadastro e login."""

from pydantic import BaseModel, Field, field_validator

# O bcrypt só considera os primeiros 72 bytes: uma senha maior valeria o mesmo que o começo dela.
MAXIMO_BYTES_SENHA = 72


def senha_cabe_no_bcrypt(senha: str) -> str:
    if len(senha.encode()) > MAXIMO_BYTES_SENHA:
        raise ValueError(f"A senha pode ter no máximo {MAXIMO_BYTES_SENHA} bytes")
    return senha


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=MAXIMO_BYTES_SENHA)

    _senha = field_validator("password")(senha_cabe_no_bcrypt)


class LoginRequest(BaseModel):
    # Sem mínimo: contas antigas foram criadas com senhas de 6 caracteres.
    username: str = Field(max_length=50)
    password: str = Field(max_length=MAXIMO_BYTES_SENHA)

    _senha = field_validator("password")(senha_cabe_no_bcrypt)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
