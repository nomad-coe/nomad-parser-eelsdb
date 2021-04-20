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

import os.path
import os
import json
from datetime import datetime
import logging
import glob
import re
import numpy as np
import pandas as pd

from nomad.parsing.parser import MatchingParser
from nomad.units import ureg
from nomad.datamodel.metainfo.common_experimental import (
    Measurement,
    Metadata,
    Sample, SampleMaterial,
    Experiment,
    Instrument, DeviceSettings,
    Origin, Author,
    Data, Spectrum)
from nomad.datamodel import Author as MetadataAuthor


logger = logging.getLogger(__name__)


class EELSApiJsonConverter(MatchingParser):
    def __init__(self):
        super().__init__(
            name='parsers/eels', code_name='eels', code_homepage='https://eelsdb.eu/',
            domain='ems',
            mainfile_mime_re=r'application/json',
            mainfile_contents_re=(r'https://eelsdb.eu/spectra')
        )

    def parse(self, filepath, archive, logger=logger):
        with open(filepath) as f:
            file_data = json.load(f)

        # Create a measurement in the archive
        measurement = archive.m_create(Measurement)

        # Read (numerical) dataset into the measurement
        # Read the msa file if it exists
        dirpath = os.path.dirname(filepath)
        dataset_filepath = next(iter(glob.glob(os.path.join(dirpath, '*.msa'))), None)
        if dataset_filepath is not None:
            data = measurement.m_create(Data)
            x_units = None
            with open(dataset_filepath, 'rt') as f:
                for line in f:
                    match = re.search(r'#XUNITS(.*)', line)
                    if match is not None:
                        x_units = match.group().split()[-1]
                        break

            if x_units == ':' or 'undefined' in x_units.lower() or x_units is None:
                x_units = 'eV'
                logger.warning('Unknown energy units; assuming eV by default')

            # Read the dataset from the msa file
            df = pd.read_csv(dataset_filepath,
                             header=None, comment='#',
                             skipfooter=1, engine='python', sep=', | |,|\t')

            # Export the dataset to the archive
            spectrum = data.m_create(Spectrum)
            spectrum.n_values = len(df)
            spectrum.energy = df[0].to_numpy() * ureg(x_units)
            spectrum.count = df[1].to_numpy()
        else:
            logger.warning('No dataset (*.msa) file found in the current directory')

        # Create metadata schematic and import values
        metadata = measurement.m_create(Metadata)

        # Load entries into each heading
        # Sample
        sample = metadata.m_create(Sample)
        sample_material = sample.m_create(SampleMaterial)

        sample.sample_id = str(file_data['id'])
        sample.sample_title = file_data['title']
        sample_material.formula = file_data['formula']

        elements = file_data.get('elements')
        if elements is not None:
            if isinstance(elements, str):
                elements = json.loads(elements)
            sample_material.elements = elements

        # Experiment
        experiment = metadata.m_create(Experiment)
        experiment.method_name = 'electron energy loss spectroscopy'
        experiment.method_abbreviation = 'EELS'
        experiment.experiment_publish_time = datetime.strptime(
            file_data.get('published'), '%Y-%m-%d %H:%M:%S')
        edges = file_data.get('edges')
        if edges is not None:
            if isinstance(edges, str):
                edges = json.loads(edges)
            experiment.edges = edges
        experiment.description = file_data['description']

        # Instrument
        # TODO: Add units to variables here
        instrument = metadata.m_create(Instrument)
        instrument.source_label = file_data['microscope']
        device_settings = instrument.m_create(DeviceSettings)
        device_settings.device_name = file_data['microscope']
        device_settings.max_energy = file_data['max_energy']
        if file_data.get('min_energy') is not None:
            device_settings.min_energy = file_data['min_energy']
        device_settings.guntype = file_data['guntype']
        device_settings.beam_energy = file_data['beamenergy']
        if file_data.get('resolution') is not None:
            device_settings.resolution = file_data['resolution']
        device_settings.step_size = file_data['stepSize']
        if file_data.get('acquisition_mode') is not None:
            device_settings.acquisition_mode = file_data['acquisition_mode']
        if file_data.get('beamcurrent') is not None:
            device_settings.beam_current = file_data['beamcurrent']
        device_settings.detector_type = file_data['detector']
        device_settings.dark_current = file_data['darkcurrent']

        # Origin
        origin = metadata.m_create(Origin)
        origin.permalink = file_data.get('permalink')
        origin.api_permalink = file_data.get('api_permalink')
        origin.repository_name = 'Electron Energy Loss Spectroscopy (EELS) database'
        origin.repository_url = 'https://eelsdb.eu'
        origin.entry_repository_url = file_data.get('permalink')

        # Author
        author = origin.m_create(Author)
        author.author_name = file_data['author']['name']
        author.author_profile_url = file_data['author']['profile_url']
        author.author_profile_api_url = file_data['author']['profile_api_url']

        # Search metadata
        archive.section_metadata.external_id = str(file_data.get('id'))
        archive.section_metadata.external_db = 'EELSDB'

        author = file_data.get('author')['name']
        author = re.sub(r'\(.*\)', '', author).strip()
        archive.section_metadata.coauthors = [MetadataAuthor(
            first_name=' '.join(author.split(' ')[0:-1]),
            last_name=author.split(' ')[-1])]
        archive.section_metadata.comment = file_data.get('description')
        archive.section_metadata.references = [
            file_data.get('permalink'),
            file_data.get('api_permalink'),
            file_data.get('download_link')]

        reference = file_data.get('reference')
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
