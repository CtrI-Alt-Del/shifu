from shifu.shared.core.domain.structures.structure import structure


@structure
class MentorAccessGrant:
    account_id: str
    access_revision: str
    operation_key: str
