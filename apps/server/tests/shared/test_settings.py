import pytest
from pydantic import ValidationError

from shifu.shared.constants.environment import EnvironmentSettings
from shifu.shared.settings import Settings


def test_settings_parse_trusted_proxy_ips_from_a_comma_separated_value() -> None:
    settings = Settings.model_validate(
        {
            'redis_url': 'redis://localhost:6379/0',
            'trusted_proxy_ips': ' 127.0.0.1, , 10.0.0.0/8 ',
        }
    )

    assert settings.trusted_proxy_ips == ['127.0.0.1', '10.0.0.0/8']


def test_settings_preserve_a_preparsed_trusted_proxy_list() -> None:
    settings = Settings(
        redis_url='redis://localhost:6379/0',
        trusted_proxy_ips=['127.0.0.1', '10.0.0.0/8'],
    )

    assert settings.trusted_proxy_ips == ['127.0.0.1', '10.0.0.0/8']


def test_environment_settings_default_local_release_version_for_blank_input() -> None:
    settings = EnvironmentSettings.from_environment(
        {
            'SHIFU_SERVER_APP_MODE': 'local',
            'SHIFU_RELEASE_VERSION': '  ',
            'SHIFU_COMMUNICATION_ENCRYPTION_KEYS': 'test-key',
        }
    )

    assert settings.release_version == 'local-dev'


def test_environment_settings_requires_release_version_outside_local_modes() -> None:
    with pytest.raises(ValidationError, match='Release version is required'):
        EnvironmentSettings.from_environment(
            {
                'SHIFU_SERVER_APP_MODE': 'staging',
                'SHIFU_RELEASE_VERSION': '',
                'SHIFU_COMMUNICATION_ENCRYPTION_KEYS': 'test-key',
            }
        )
