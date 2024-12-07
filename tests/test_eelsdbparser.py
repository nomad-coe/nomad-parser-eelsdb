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

from nomad.datamodel import EntryArchive, EntryMetadata

from eelsdbparser.eelsdb_parser import EELSDBParser


@pytest.fixture
def parser():
    return EELSDBParser()


@pytest.mark.parametrize('mainfile, n_values', [
    ('test_1/metadata.json', 226),
    ('test_2/metadata.json', 546),
    ('test_3/metadata.json', 1340)
])
def test_examples(parser, mainfile, n_values):
    archive = EntryArchive()
    archive.m_create(EntryMetadata)
    parser.parse(f'tests/data/{mainfile}', archive, logging)

    measurement = archive.measurement[0]
    assert measurement.measurement_id is not None
    assert measurement.method_name is not None
    assert measurement.eels.spectrum.n_values == n_values


def test_all_metadata_example(parser):
    archive = EntryArchive()
    archive.m_create(EntryMetadata)
    parser.parse('tests/data/all_metadata.json', archive, logging)
