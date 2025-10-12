from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # To load from a .env file, we specify the file path
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    # Define your configuration variables here
    PROJECT_NAME: str = "Turkish Diaspora Location App API"
    APP_VERSION: str = "0.0.1" # A default version

# Create a single instance of the settings to be used throughout the app
settings = Settings()