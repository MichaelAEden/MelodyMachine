"""
Downloads songs from vgmusic.com
Based on: https://scholarworks.sjsu.edu/cgi/viewcontent.cgi?article=1606&context=etd_projects
"""
import os
import logging
from typing import List
from urllib.parse import urljoin

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup


def get_vgmusic_download_urls(path: str) -> List[str]:
    base_url = f'https://vgmusic.com{path}'

    source = requests.get(base_url).text
    soup = BeautifulSoup(source, 'lxml')
    links = soup.find_all('a', href=True)
    links = [
        urljoin(base_url, link['href'])
        for link in links
        if link['href'].endswith('.mid')
    ]

    return links


def download(download_urls: List[str], output_path: str):
    os.makedirs(output_path, exist_ok=True)

    for download_url in tqdm(download_urls):
        filename = download_url.rsplit('/', 1)[-1]
        try:
            resp = requests.get(download_url)
            with open(os.path.join(output_path, filename), 'wb') as f:
                f.write(resp.content)
        except requests.exceptions.Timeout:
            logging.warning(f'Timeout while downloading: {download_url}')


if __name__ == '__main__':
    download_urls = get_vgmusic_download_urls('/music/console/nintendo/nes/')
    download(download_urls[:10], 'res/vgmusic/nes')
