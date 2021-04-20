#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pytest
import logging
import os.path

from nomad import utils
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.ems import EMSMetadata

from eelsdbconverter import EELSApiJsonConverter


@pytest.fixture(scope='session', autouse=True)
def nomad_logging():
    utils.set_console_log_level(logging.ERROR)


@pytest.fixture
def parser():
    return EELSApiJsonConverter()


@pytest.mark.parametrize('path, n_values', [
    ('data/test_1/metadata.json', 226),
    ('data/test_2/metadata.json', 546),
    ('data/all.json', None)
])
def test_example(parser, path, n_values):
    archive = EntryArchive()
    entry_metadata = archive.m_create(EntryMetadata)
    ems = entry_metadata.m_create(EMSMetadata)

    parser.parse(
        os.path.join(os.path.dirname(__file__), path),
        archive, utils.get_logger(__name__))

    measurement = archive.section_measurement[0]
    assert measurement.section_metadata.section_sample.sample_id is not None
    assert measurement.section_metadata.section_experiment.method_name is not None
    if n_values is None:
        assert measurement.section_data is None
    else:
        assert measurement.section_data.section_spectrum.n_values == n_values

    ems.apply_domain_metadata(archive)

    assert archive.section_metadata.formula is not None
    assert len(archive.section_metadata.atoms) > 0

    import json
    print(json.dumps(archive.section_metadata.m_to_dict(), indent=2))
