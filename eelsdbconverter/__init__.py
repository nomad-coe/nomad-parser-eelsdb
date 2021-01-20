#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD.
# See https://nomad-lab.eu for further info.
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

import sys
import os.path
import json
import ase
import numpy as np
from datetime import datetime
import time
import ast
import logging
import re

from nomad.datamodel import Author
from nomad.datamodel.metainfo.common_experimental import (
    Experiment, Sample, Method, Data, Material)

from nomad.parsing.parser import FairdiParser


logger = logging.getLogger(__name__)


class EELSApiJsonConverter(FairdiParser):
    def __init__(self):
        super().__init__(
            name='parsers/eels', code_name='eels', code_homepage='https://eelsdb.eu/',
            domain='ems',
            mainfile_mime_re=r'application/json',
            mainfile_contents_re=(r'https://eelsdb.eu/spectra')
        )

    def parse(self, filepath, archive, logger=logger):
        with open(filepath) as f:
            data = json.load(f)

        experiment = archive.m_create(Experiment)
        experiment.raw_metadata = data

        experiment.experiment_publish_time = datetime.strptime(
            data.get('published'), '%Y-%m-%d %H:%M:%S')

        sample = experiment.m_create(Sample)
        material = sample.m_create(Material)
        material.chemical_formula = data.get('formula')
        elements = data.get('elements')
        if elements is not None:
            if isinstance(elements, str):
                elements = json.loads(elements)
            material.atom_labels = elements
        material.chemical_name = data.get('title')

        experiment.m_create(
            Method,
            data_type='spectrum',
            method_name='electron energy loss spectroscopy',
            method_abbreviation='EELS')

        section_data = experiment.m_create(Data)

        archive.section_metadata.external_id = str(data.get('id'))
        archive.section_metadata.external_db = 'EELSDB'

        author = data.get('author')['name']
        author = re.sub(r'\(.*\)', '', author).strip()
        archive.section_metadata.coauthors = [Author(
            first_name=' '.join(author.split(' ')[0:-1]),
            last_name=author.split(' ')[-1])]
        archive.section_metadata.comment = data.get('description')
        archive.section_metadata.references = [
            data.get('permalink'),
            data.get('api_permalink'),
            data.get('download_link')
        ]

        reference = data.get('reference')
        if reference:
            if isinstance(reference, str):
                archive.section_metadata.references.append(reference)
            elif isinstance(reference, dict):
                if 'freetext' in reference:
                    archive.section_metadata.references.append(
                        re.sub(r'\r+\n+', '; ', reference['freetext']))
                else:
                    archive.section_metadata.references.append('; '.join([
                        str(value).strip() for value in reference.values()
                    ]))

        section_data.repository_name = 'Electron Energy Loss Spectroscopy (EELS) database'
        section_data.repository_url = 'https://eelsdb.eu'
        section_data.entry_repository_url = data.get('permalink')
