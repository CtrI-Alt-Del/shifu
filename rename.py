import os
import glob
from pathlib import Path

# Files to rename
file_renames = [
    ("apps/server/src/shifu/shared/core/interfaces/curriculum_catalog_reader.py", "apps/server/src/shifu/shared/core/interfaces/curriculum_catalog_provider.py"),
    ("apps/server/src/shifu/curriculum/providers/curriculum_catalog_reader_provider.py", "apps/server/src/shifu/curriculum/providers/curriculum_catalog_provider_impl.py"), # wait, what should CurriculumCatalogReaderProvider be called?
]

# The comment says: "Use somente o nome Provider em vez de Reader" on `curriculum_catalog_reader.py`. 
# So `CurriculumCatalogReader` -> `CurriculumCatalogProvider`.
# Then `CurriculumCatalogReaderProvider` (the implementation) might just be `CurriculumCatalogProviderImpl` or something? Wait. The reviewer says "Use somente o nome Provider em vez de Reader" on the Protocol.
# If the protocol is `CurriculumCatalogProvider`, then what's the implementation? Maybe `SqlalchemyCurriculumCatalogProvider`? Currently it's `CurriculumCatalogReaderProvider`. If I just rename `Reader` to `Provider` everywhere:
# `CurriculumCatalogReader` -> `CurriculumCatalogProvider`
# `curriculum_catalog_reader` -> `curriculum_catalog_provider`
# But wait, if I rename `CurriculumCatalogReaderProvider`, it becomes `CurriculumCatalogProviderProvider` which is silly. Let's see `apps/server/src/shifu/curriculum/providers/curriculum_catalog_reader_provider.py` contents.
