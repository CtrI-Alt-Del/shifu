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
