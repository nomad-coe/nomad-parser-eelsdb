import numpy as np            # pylint: disable=unused-import
import typing                 # pylint: disable=unused-import
from nomad.metainfo import (  # pylint: disable=unused-import
    MSection, MCategory, Category, Package, Quantity, Section, SubSection, SectionProxy,
    Reference
)

m_package = Package(
    name='eelsdb',
    description='Metadata for the EELS database (https://eelsdb.eu)')

m_package.__init_metainfo__()
