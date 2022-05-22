#!/usr/bin/env python3
# coding: utf-8

import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable

import dateparser
from bs4 import BeautifulSoup, Comment, NavigableString


latest_updates_pattern = re.compile(r'Latest Updates|Das Neueste|Ultimi Aggiornamenti|Dernières Mises à Jour')
site_image_pattern = re.compile(r'images/(\w+)\.')
SITES = {
    'ach': 'Anal Checkups',
    'alg': 'Analyzed Girls',
    'atm': 'Ass Teen Mouth',
    'biv': 'Brutal Invasion',
    'btp': 'Bang Teen Pussy',
    'cht': 'Cumaholic Teens',
    'def': 'Defiled 18',
    'dhd': 'Dreams-HD',
    'dtt': 'Double Teamed Teens',
    'fbs': 'Fab Sluts',
    'ggc': 'Girls Got Cream',
    'hcy': 'Hardcore Youth',
    'lhc': 'Little Hellcat',
    'mtg': 'Make Teen Gape',
    'nys': 'Nylon Sweeties',
    'sed': 'Seductive 18',
    'sgs': 'She Got Six',
    'spm': 'Spermantino',
    'tac': 'Teen Anal Casting',
    'tdr': 'Teen Drillers',
    'tgn': 'Teen Gina',
    'tma': 'Teach My Ass',
    'tnw': 'Teens Natural Way',
    'trt': 'Try Teens',
    'ttb': 'Teens Try Blacks',
    'wtb': 'White Teens Black Cocks',
    'yts': 'Young Throats',
}

def get_site(site_image: str) -> str:
    if m := site_image_pattern.match(site_image):
        return SITES.get(m.group(1), '???')
    return '???'


@dataclass
class Scene:
    site: str
    name: str
    date: str
    image: str
    snapshot: str

    @classmethod
    def parse(cls, timestamp: str, site_image: str, image_url: str, name: str, month_day: str, pathname: str):
        site = get_site(site_image)

        timestamp_dt = datetime.strptime(f'{timestamp}+00:00', '%Y%m%d%H%M%S%z')
        timestamp_time = ':'.join((timestamp[8:10], timestamp[10:12], timestamp[12:14]))
        date_str = f'{month_day} {timestamp[:4]} 12:00:00 UTC'
        parsed_date = dateparser.parse(date_str)
        if parsed_date:
            if parsed_date.date() > timestamp_dt.date():
                parsed_date = parsed_date.replace(timestamp_dt.year - 1)
            date = parsed_date.date().isoformat()
        else:
            print(f'failed to parse: {date_str}')
            date = '????-??-??'
            breakpoint()

        image_url = f'https://web.archive.org/web/{timestamp}im_/{image_url}'
        snapshot_url = f'https://web.archive.org/web/{timestamp}/http://teencoreclub.com/{pathname}'

        return cls(name=name, site=site, date=date, image=image_url, snapshot=snapshot_url)

    @property
    def uid(self) -> str:
        return '|'.join([self.name, self.site, self.date])

    @property
    def csv(self) -> str:
        return ','.join([
            self.name,
            self.site,
            self.date,
            self.image,
            self.snapshot,
        ])

class Processor:
    folders = ['home', 'latest']

    def __init__(self):
        self.root = Path(__file__).parent

    def process(self):
        scenes: Dict[str, Scene] = {}
        for folder in self.folders:
            for scene in self._process_folder(self.root / folder):
                if scene.uid not in scenes:
                    scenes[scene.uid] = scene

        header = ','.join(('Name', 'Site', 'Date', 'Image', 'Snapshot'))
        data = sorted(scenes.values(), key=lambda s: (s.name, s.site))
        data = map(lambda s: s.csv, data)
        data_csv = f'{header}\n' + '\n'.join(data) + '\n'
        (self.root / 'scenes.csv').write_bytes(data_csv.encode('utf-8'))

    def _process_folder(self, folder: Path):
        for snapshot in sorted((x for x in folder.iterdir() if x.is_dir()), key=lambda x: x.name):
            file = next((snapshot / 'teencoreclub.com').glob('*'), None)
            if not file:
                print(f'!!! no file found in {snapshot.relative_to(self.root).as_posix()}')
                continue

            timestamp = snapshot.name

            print(f'processing: {file.relative_to(self.root.parent).as_posix()}')

            func_name = f'_process_{folder.name}'
            try:
                func = getattr(self, func_name)
            except AttributeError:
                raise ValueError(f'function not found: {func_name}')

            yield from func(file, timestamp)

    def _process_home(self, file: Path, timestamp: str) -> Iterable[Scene]:
        soup = BeautifulSoup(file.read_bytes(), features='html.parser')

        text_el = soup.find(['nobr','span'], text=latest_updates_pattern)
        if not text_el:
            breakpoint()
            raise StopIteration

        text_el_table = text_el.find_parent('table')
        if not text_el_table:
            breakpoint()
            raise StopIteration

        latest_updates_table = text_el_table.find_next_sibling('table')
        if not latest_updates_table or isinstance(latest_updates_table, NavigableString):
            breakpoint()
            raise StopIteration

        sites = latest_updates_table.select('img.sitename')
        images = latest_updates_table.select('img.lupdates')
        names = latest_updates_table.select('div.nick')
        dates = latest_updates_table.select('div.date')

        data = (sites, images, names, dates)

        # all have the same length
        if len({ len(i) for i in data }) != 1:
            breakpoint()
            raise StopIteration

        for site_el, image_el, name_el, date_el in zip(*data):
            name = name_el.get_text(strip=True)
            if not name:
                continue

            month_day = date_el.get_text(strip=True)
            if not month_day:
                month_day = str(date_el.find(string=lambda text: isinstance(text, Comment)))
                month_day = html.unescape(month_day)

            if not month_day:
                continue

            scene = Scene.parse(
                timestamp=timestamp,
                pathname=file.name if file.name != 'index.html' else '',
                site_image=site_el.attrs['src'],
                image_url=image_el.attrs['src'],
                name=name,
                month_day=month_day,
            )
            yield scene

    def _process_latest(self, file: Path, timestamp: str) -> Iterable[Scene]:
        soup = BeautifulSoup(file.read_bytes(), features='html.parser')

        text_el = soup.select_one('.enter1')
        if not text_el:
            breakpoint()
            raise StopIteration

        container_table = text_el.find_parents('table', limit=2)[-1]
        if not container_table:
            breakpoint()
            raise StopIteration

        all_updates_table = container_table.select_one('table + table table')
        if not all_updates_table:
            breakpoint()
            raise StopIteration

        sites = all_updates_table.select('img.sitename')
        images = all_updates_table.select('img:not(.sitename)')
        names = all_updates_table.select('div.nick')
        dates = all_updates_table.select('div.date')

        data = (sites, images, names, dates)

        # all have the same length
        if len({ len(i) for i in data }) != 1:
            breakpoint()
            raise StopIteration

        for site_el, image_el, name_el, date_el in zip(*data):
            name = name_el.get_text(strip=True)
            if not name:
                continue

            month_day = date_el.get_text(strip=True)
            if not month_day:
                month_day = str(date_el.find(string=lambda text: isinstance(text, Comment)))
                month_day = html.unescape(month_day)

            if not month_day:
                continue

            scene = Scene.parse(
                timestamp=timestamp,
                pathname=file.name if file.name != 'index.html' else '',
                site_image=site_el.attrs['src'],
                image_url=image_el.attrs['src'],
                name=name,
                month_day=month_day,
            )
            yield scene


def main():
    app = Processor()
    app.process()


if __name__ == '__main__':
    main()
