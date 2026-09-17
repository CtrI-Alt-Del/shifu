from faker import Faker


class IdProviderFaker:
    _faker: Faker = Faker('pt_BR')
    _ulid_alphabet: str = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

    def generate(self) -> str:
        return ''.join(
            [
                self._faker.random_element(elements='01234567'),
                *self._faker.random_choices(
                    elements=self._ulid_alphabet,
                    length=25,
                ),
            ]
        )
