from shifu.shared.core.domain.structures import structure


@structure
class ImageChoiceOptionDetail:
    key: str
    image_path: str
    description: str
