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
import numpy as np
from datetime import datetime
import logging
import pandas as pd
import nomad.units

from .metainfo import *
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
            file_data = json.load(f)

        # Create a measurement in the archive
        measurement = archive.m_create(Measurement)

        """
        Read (numerical) dataset into the measurement
        """
        # Check that the msa file exists

        dirpath = os.path.dirname(filepath)
        for i in os.listdir(dirpath):
            if i.endswith('.msa'):
                dataset_filepath = os.path.join(dirpath, i)

        if dataset_filepath is not None:
            data = measurement.m_create(Data)
            # Read header of the dataset(msa file)
            with open(dataset_filepath, 'rt') as f:
                line = f.readline()
                skip_row_counter = 0
                header_dataset = []
                while line.startswith('#'):
                    header_dataset.append(line.strip().lstrip('#').split())
                    line = f.readline()
                    skip_row_counter += 1

            # Extract units from the header of the dataset file
            for item in header_dataset:
                if item[0].lower() == 'xunits':
                    if item[-1] != ':':
                        x_units = item[-1]
                    else:
                        x_units = 'eV'

            # Read the dataset from the msa file
            df = pd.read_csv(dataset_filepath,
                             header=None, skiprows=skip_row_counter,
                             skipfooter=1, engine='python', sep=", | |,|\t")

            # Export the dataset to the archive
            ureg = nomad.units.ureg

            spectrum = data.m_create(Spectrum)
            spectrum.n_values = len(df)
            try:
                x_units
            except NameError:
                x_units = 'eV'
                logger.info('WARNING!!! Manually set energy units to eV!')
            if 'undefined' in x_units:
                x_units = 'eV'
                logger.info('WARNING!!! Manually set energy units to eV!')
            spectrum.energy = df[0].to_numpy() * ureg(x_units)
            spectrum.count = df[1].to_numpy()

        """
        Create metadata schematic and import values
        """
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

        # Author Generated
        author_generated = metadata.m_create(AuthorGenerated)
        author_generated.permalink = file_data['permalink']
        author_generated.author_name = file_data['author']['name']
        author_generated.author_profile_url = file_data['author']['profile_url']
        author_generated.author_profile_api_url = file_data['author']['profile_api_url']
        author_generated.descriptionn = file_data['description']
