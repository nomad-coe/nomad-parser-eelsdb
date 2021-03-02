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

from .metainfo import *
from nomad.parsing.parser import FairdiParser
from nomad.units import ureg

import pandas as pd

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
                logger.warn('Unknown energy units; assuming eV by default')

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
            logger.warn('No dataset (*.msa) file found in the current directory')

        # Create metadata schematic and import values
        metadata = measurement.m_create(Metadata)

        # Load entries into each heading
        # Sample
        sample = metadata.m_create(Sample)

        sample.formula = file_data['formula']
        sample.sample_id = str(file_data['id'])
        sample.sample_title = file_data['title']

        elements = file_data.get('elements')
        if elements is not None:
            if isinstance(elements, str):
                elements = json.loads(elements)
            sample.elements = elements

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
        origin.permalink = file_data['permalink']
        origin.api_permalink = file_data['api_permalink']
        if file_data.get('repository_name') is not None:
            origin.repository_name = file_data['repository_name']
        if file_data.get('repository_url') is not None:
            origin.repository_url = file_data['repository_url']
        if file_data.get('preview_url') is not None:
            origin.preview_url = file_data['preview_url']
        if file_data.get('entry_repository_url') is not None:
            origin.entry_repository_url = file_data['entry_repository_url']

        # Author
        author = origin.m_create(Author)
        author.author_name = file_data['author']['name']
        author.author_profile_url = file_data['author']['profile_url']
        author.author_profile_api_url = file_data['author']['profile_api_url']
