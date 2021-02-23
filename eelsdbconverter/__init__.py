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
import os
import json
import ase
import numpy as np
from datetime import datetime
import time
import ast
import logging
import re
import glob
import pandas as pd

from nomad.datamodel import Author
# from nomad.datamodel.metainfo.common_experimental import (
    # Experiment, Sample, Method, Data, Material)
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
        
        #Create a measurement in the archive
        measurement = archive.m_create(Measurement)

        """
        Read (numerical) dataset into the measurement
        """
        data = measurement.m_create(Data)

        #Check that the msa file exists
        
        dirpath = filepath[:filepath.rindex('/')]
        if os.path.exists(dirpath):
            for i in os.listdir(dirpath):
                if i.endswith('.msa'):
                    data_file_path = os.path.join(dirpath, i)
        
        #Read header from the msa file
        with open(data_file_path, 'rt') as f:
            line = f.readline()
            skip_row_counter = 0
            header_data_file = []
            while line.startswith('#'):
                previous_line = line
                line = f.readline()
                skip_row_counter += 1
                header_data_file.append(previous_line.strip().lstrip('#').split())
        
        df = pd.read_csv(data_file_path, header=None, skiprows=skip_row_counter, skipfooter=1, engine='python')
        
        numerical_value = data.m_create(NumericalValues)
        numerical_value.data_values = df.to_numpy()

        #Create the hierarchical structure
        metadata = measurement.m_create(Metadata)

        # Create the hierarchical structure inside metadata
        sample = metadata.m_create(Sample)
        experiment = metadata.m_create(Experiment)
        instrument = metadata.m_create(Instrument)
        # data_header = metadata.m_create(DataHeader)
        author_generated = metadata.m_create(AuthorGenerated)

        #Load entries into each above hierarchical structure
        #Sample
        sample.formula = file_data['formula']
        elements = file_data.get('elements')
        if elements is not None:
            if isinstance(elements, str):
                elements = json.loads(elements)
            sample.elements = elements

        #Experiment
        experiment.method_name = 'electron energy loss spectroscopy'
        experiment.method_abbreviation = 'EELS'
        experiment.experiment_publish_time = datetime.strptime(
            file_data.get('published'), '%Y-%m-%d %H:%M:%S')
        
        #Instrument
        instrument.source_label = file_data['microscope']
        device_settings = instrument.m_create(DeviceSettings)
        device_settings.device_name = file_data['microscope']
        device_settings.max_energy = file_data['max_energy']
        device_settings.min_energy = file_data['min_energy']
        device_settings.guntype = file_data['guntype']
        device_settings.beam_energy = file_data['beamenergy']
        device_settings.resolution = file_data['resolution']
        device_settings.step_size = file_data['stepSize']
        device_settings.acquisition_mode = file_data['acquisition_mode']
        device_settings.beam_current = file_data['beamcurrent']
        device_settings.detector_type = file_data['detector']
        device_settings.dark_current = file_data['darkcurrent']

        #Author Generated
        author_generated.sample_id = str(file_data['id'])
        author_generated.sample_title = file_data['title']
        author_generated.permalink = file_data['permalink']
        author_generated.author_name = file_data['author']['name']
        author_generated.author_profile_url = file_data['author']['profile_url']
        author_generated.author_profile_api_url = file_data['author']['profile_api_url']
        author_generated.descriptionn = file_data['description']


        

        #Populating the data header; the information isn't in the metainfo file
        #Data Header
        
        for i in range(len(df.columns)):
            data_header = metadata.m_create(DataHeader)
            if i==0:
                data_header.label = "Energy"
            elif i==1:
                data_header.label = "Counts"
        

        # experiment = archive.m_create(Experiment)
        # experiment.raw_metadata = data

        # experiment.experiment_publish_time = datetime.strptime(
        #     data.get('published'), '%Y-%m-%d %H:%M:%S')

        # sample = experiment.m_create(Sample)
        # material = sample.m_create(Material)
        # material.chemical_formula = data.get('formula')
        # elements = data.get('elements')
        # if elements is not None:
        #     if isinstance(elements, str):
        #         elements = json.loads(elements)
        #     material.atom_labels = elements
        # material.chemical_name = data.get('title')

        # experiment.m_create(
        #     Method,
        #     data_type='spectrum',
        #     method_name='electron energy loss spectroscopy',
        #     method_abbreviation='EELS')

        # section_data = experiment.m_create(Data)

        # archive.section_metadata.external_id = str(data.get('id'))
        # archive.section_metadata.external_db = 'EELSDB'

        # author = data.get('author')['name']
        # author = re.sub(r'\(.*\)', '', author).strip()
        # archive.section_metadata.coauthors = [Author(
        #     first_name=' '.join(author.split(' ')[0:-1]),
        #     last_name=author.split(' ')[-1])]
        # archive.section_metadata.comment = data.get('description')
        # archive.section_metadata.references = [
        #     data.get('permalink'),
        #     data.get('api_permalink'),
        #     data.get('download_link')
        # ]

        # reference = data.get('reference')
        # if reference:
        #     if isinstance(reference, str):
        #         archive.section_metadata.references.append(reference)
        #     elif isinstance(reference, dict):
        #         if 'freetext' in reference:
        #             archive.section_metadata.references.append(
        #                 re.sub(r'\r+\n+', '; ', reference['freetext']))
        #         else:
        #             archive.section_metadata.references.append('; '.join([
        #                 str(value).strip() for value in reference.values()
        #             ]))

        # section_data.repository_name = 'Electron Energy Loss Spectroscopy (EELS) database'
        # section_data.repository_url = 'https://eelsdb.eu'
        # section_data.entry_repository_url = data.get('permalink')
