from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OLLAMA_URL: str = "http://ollama:11434"
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    EMBED_MODEL: str = "nomic-embed-text"
    CHAT_MODEL: str = "llama3.2"

    # Path mapping: host path -> container path
    HOST_HOME: str = "/home/user"
    CONTAINER_HOME: str = "/home/user"

    DATA_DIR: str = "/app/data"

    class Config:
        env_file = ".env"


settings = Settings()


def host_to_container(path: str) -> str:
    if path.startswith(settings.HOST_HOME):
        return settings.CONTAINER_HOME + path[len(settings.HOST_HOME):]
    return path


def container_to_host(path: str) -> str:
    if path.startswith(settings.CONTAINER_HOME):
        return settings.HOST_HOME + path[len(settings.CONTAINER_HOME):]
    return path
