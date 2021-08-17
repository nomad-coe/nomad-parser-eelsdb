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

from nomad.datamodel import EntryArchive
from nomad.parsing.parser import MatchingParser
from nomad.units import ureg

from nomad.datamodel.metainfo.common_experimental import (
    Measurement, Data, Metadata, Spectrum, Sample, SampleMaterial, Instrument,
    DeviceSettings, Origin, Experiment, Author)


logger = logging.getLogger(__name__)


class EELSDBParser(MatchingParser):
    def __init__(self):
        super().__init__(
            name='parsers/eels', code_name='eels', code_homepage='https://eelsdb.eu/',
            domain='ems',
            mainfile_mime_re=r'application/json',
            mainfile_contents_re=(r'https://eelsdb.eu/spectra')
        )

    def parse_msa_file(self, msa_path, logger=logger):
        metadata_re = re.compile(r'^#\s*([A-Z0-9]+)\s*:(.*)\s*$')
        data_re = re.compile(r'(-?\d+(\.\d+)?),\s*(-?\d+(\.\d+)?)')

        raw_metadata = {}
        raw_energies = []
        raw_counts = []
        with open(msa_path, 'rt') as f:
            for line in f.readlines():
                match = re.match(metadata_re, line)
                if match:
                    raw_metadata[match.group(1)] = match.group(2)
                    continue
                match = re.match(data_re, line)
                if match:
                    raw_energies.append(float(match.group(1)))
                    raw_counts.append(float(match.group(3)))
                    continue

                logger.warning('Unexpected line format in .msa file')

        x_units = raw_metadata.get('XUNITS')
        if not x_units or 'undefined' in x_units.lower():
            x_units = 'eV'
            logger.warning('Unknown energy units')

        if int(raw_metadata.get('NPOINTS', 0)) != len(raw_energies):
            logger.warning('Npoints metadata does not match value count')

        spectrum = Spectrum()
        spectrum.n_values = len(raw_energies)
        spectrum.energy = raw_energies * ureg(x_units)
        spectrum.count = raw_counts
        return raw_metadata, spectrum

    def parse(self, mainfile_path, archive: EntryArchive, logger=logger):
        with open(mainfile_path, 'rt') as f:
            raw_metadata = json.load(f)

        # Create a measurement in the archive
        measurement = archive.m_create(Measurement)
        measurement.section_data = Data()

        # Read (numerical) dataset into the measurement
        # Read the msa file if it exists
        msa_path = next(iter(
            glob.glob(os.path.join(os.path.dirname(mainfile_path), '*.msa'))), None)
        if msa_path:
            _, spectrum = self.parse_msa_file(msa_path)
            measurement.section_data.section_spectrum = spectrum
        else:
            logger.warning('No *.msa file found')

        # Create metadata schematic and import values
        metadata = measurement.m_create(Metadata)

        # Load entries into each heading
        # Sample
        sample = metadata.m_create(Sample)
        sample_material = sample.m_create(SampleMaterial)

        sample_material.formula = raw_metadata['formula']
        sample.sample_name = raw_metadata['title']

        elements = raw_metadata.get('elements', [])
        if isinstance(elements, str):
            elements = json.loads(elements)
        sample_material.elements = elements

        # Experiment
        experiment = metadata.m_create(Experiment)
        experiment.experiment_id = str(raw_metadata['id'])
        archive.section_metadata.external_id = str(raw_metadata['id'])
        experiment.method_name = 'electron energy loss spectroscopy'
        experiment.method_abbreviation = 'EELS'
        experiment.experiment_publish_time = datetime.strptime(
            raw_metadata.get('published'), '%Y-%m-%d %H:%M:%S')
        edges = raw_metadata.get('edges', [])
        if isinstance(edges, str):
            edges = json.loads(edges)
        experiment.edges = edges
        experiment.description = raw_metadata['description']

        # Instrument
        # TODO: Add units to variables here
        instrument = metadata.m_create(Instrument)
        instrument.source_label = raw_metadata['microscope']
        device_settings = instrument.m_create(DeviceSettings)
        device_settings.device_name = raw_metadata['microscope']
        device_settings.max_energy = raw_metadata['max_energy']
        if raw_metadata.get('min_energy') is not None:
            device_settings.min_energy = raw_metadata['min_energy']
        device_settings.guntype = raw_metadata['guntype']
        device_settings.beam_energy = raw_metadata['beamenergy']
        if raw_metadata.get('resolution') is not None:
            device_settings.resolution = raw_metadata['resolution']
        device_settings.step_size = raw_metadata['stepSize']
        if raw_metadata.get('acquisition_mode') is not None:
            device_settings.acquisition_mode = raw_metadata['acquisition_mode']
        if raw_metadata.get('beamcurrent') is not None:
            device_settings.beam_current = raw_metadata['beamcurrent']
        device_settings.detector_type = raw_metadata['detector']
        device_settings.dark_current = raw_metadata['darkcurrent']

        # Origin
        origin = metadata.m_create(Origin)
        origin.permalink = raw_metadata['permalink']
        origin.api_permalink = raw_metadata['api_permalink']
        if raw_metadata.get('repository_name') is not None:
            origin.repository_name = raw_metadata['repository_name']
        if raw_metadata.get('repository_url') is not None:
            origin.repository_url = raw_metadata['repository_url']
        if raw_metadata.get('preview_url') is not None:
            origin.preview_url = raw_metadata['preview_url']
        if raw_metadata.get('entry_repository_url') is not None:
            origin.entry_repository_url = raw_metadata['entry_repository_url']

        # Author
        author = origin.m_create(Author)
        author.author_name = raw_metadata['author']['name']
        author.author_profile_url = raw_metadata['author']['profile_url']
        author.author_profile_api_url = raw_metadata['author']['profile_api_url']
