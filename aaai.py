# -*- coding: utf-8 -*-
"""
Created on Sat Jul 25 16:55:22 2020

@author: microgts
"""

import urllib
from urllib.request import urlopen
import time
import bs4
from bs4 import BeautifulSoup
import pickle
# from PyPDF2 import PdfFileMerger
from PyPDF3 import PdfFileMerger
import zipfile
import os
import shutil
from tqdm import tqdm
import subprocess
from slugify import slugify
import csv


def save_csv(year):
    """
    write AAAI papers' urls in one csv file
    :param year: int, AAAI year, such 2019
    :return: peper_index: int, the total number of papers
    """
    with open(f'D:/DESKTOP/Papers/AAAI/AAAI_{year}.csv', 'w', newline='') as csvfile:
        fieldnames = ['title', 'link', 'group']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        if year >= 2310:
            init_url = f'https://www.aaai.org/ocs/index.php/AAAI/AAAI{year-2000}/schedConf/presentations'
        if year >= 2000:
            init_url = f'https://www.aaai.org/Library/AAAI/aaai{year - 2000}contents.php'
        else:
            init_url = f'https://www.aaai.org/Library/AAAI/aaai{year - 1900}contents.php'
        # create current dict
        error_log = []
        
        # paper_dict = dict()

        postfix = f'AAAI_{year}'
        if os.path.exists(f'.\\init_url_AAAI_{year}.dat'):
            with open(f'.\\init_url_AAAI_{year}.dat', 'rb') as f:
                content = pickle.load(f)
        else:
            content = urlopen(init_url).read()
            # content = open(f'..\\AAAI_{year}.html', 'rb').read()
            with open(f'.\\init_url_AAAI_{year}.dat', 'wb') as f:
                pickle.dump(content, f)
        soup = BeautifulSoup(content, 'html5lib')
        paper_index = 0
        if year >= 2300:
            print("XXXXXXXXXXXXXXX")
            div_content = soup.find('div', {'id': 'content'})
            pbar = tqdm(div_content.find_all(['h4', 'table']))
            for child in pbar:
                if 'h4' == child.name:  # group name
                    this_group = slugify(child.text)
                else:  # table
                    link = None
                    try:
                        all_as = child.find_all('a')
                        title = slugify(all_as[0].text)
                    except Exception as e:
                        pass
                    try:
                        for a in all_as:
                            if a.text == 'PDF':
                                link = a.get('href').replace('view', 'download')
                                paper_dict = {'title': title,
                                              'link': link,
                                              'group': this_group}
                                paper_index += 1
                                pbar.set_description(f'downloading paper: {title}')
                                # print(f'downloading paper: {title}')
                                # print(link)
                                writer.writerow(paper_dict)
                    except Exception as e:
                        print('Error: ' + title + ' - ' + str(e))
                        if link is None:
                            paper_dict = {'title': title,
                                          'link': 'error',
                                          'group': this_group}
                            error_log.append((title, 'error', str(e)))
                        else:
                            paper_dict = {'title': title,
                                          'link': link,
                                          'group': this_group}
                        paper_index += 1
                        writer.writerow(paper_dict)
        else:
            print("yyyyyyyyyyyyyy")
            paper_list_bar = tqdm(soup.find('div', {'id': 'content'}).find_all(['h3', 'h4', 'p']))
            this_group = ''
            for paper in paper_list_bar:
                if 'h3' == paper.name: # group h3
                    this_group_v3 = slugify(paper.text.strip())
                    this_group = this_group_v3
                elif 'h4' == paper.name:  # group h4
                    this_group_v4 = slugify(paper.text.strip())
                    this_group = this_group_v3 + '--' + this_group_v4
                else: # paper
                    # get title and link
                    title = None
                    link = None
                    all_as = paper.find_all('a')
                    if len(all_as) >= 1:
                        for a in all_as:
                            abs_link = a.get('href')
                            if abs_link is not None:
                                abs_link = urllib.parse.urljoin(init_url, abs_link)
                                title = slugify(a.text.strip())
                                if 'pdf' == abs_link[-3:]:
                                    link = abs_link
                                    break
                                else:
                                    headers = {
                                        'User-Agent':
                                            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
                                    req = urllib.request.Request(url=abs_link, headers=headers)
                                    for i in range(3):
                                        try:
                                            abs_content = urllib.request.urlopen(req, timeout=10).read()
                                            break
                                        except:
                                            pass
                                    if abs_content is not None:
                                        abs_soup = BeautifulSoup(abs_content, 'html5lib')
                                        h1 = abs_soup.find('h1')
                                        try:
                                            link = urllib.parse.urljoin(abs_link, h1.a.get('href')[8:])
                                        except:
                                            break
                                        if link is not None:
                                            break
                    if title is not None:
                        paper_index += 1
                        paper_list_bar.set_description_str(f'Downloading paper {paper_index}: {title}')
                        if title is not None:
                            paper_dict = {'title': title,
                                          'link': link,
                                          'group': this_group}
                        else:
                            paper_dict = {'title': title,
                                          'link': 'error',
                                          'group': this_group}
                            error_log.append((title, 'no link'))
                        writer.writerow(paper_dict)


        #  write error log
        print('write error log')
        with open('download_err_log.txt', 'w') as f:
            for log in tqdm(error_log):
                for e in log:
                    if e is not None:
                        f.write(e)
                    else:
                        f.write('None')
                    f.write('\n')

                f.write('\n')
    return paper_index


def download_from_csv(year, save_dir, time_step_in_seconds=5, total_paper_number=None):
    """
    download all AAAI paper given year
    :param year: int, AAAI year, such 2019
    :param save_dir: str, paper and supplement material's save path
    :param time_step_in_seconds: int, the interval time between two downlaod request in seconds
    :param total_paper_number: int, the total number of papers that is going to download
    :return: True
    """
    # use IDM to download everything
    idm_path = '''"C:\Program Files (x86)\Internet Download Manager\IDMan.exe"'''  # should replace by the local IDM path
    basic_command = [idm_path, '/d', 'xxxx', '/p', os.getcwd(), '/f', 'xxxx', '/n']

    error_log = []
    postfix = f'AAAI_{year}'
    with open(f'D:\DESKTOP\Papers\AAAI\AAAI_{year}.csv', newline='') as csvfile:
        myreader = csv.DictReader(csvfile, delimiter=',')
        pbar = tqdm(myreader)
        i = 0
        for this_paper in pbar:
            i += 1
            # get title
            title = slugify(this_paper['title'])
            if '' == this_paper['group']:
                this_paper_main_path = os.path.join(save_dir, f'{title}_{postfix}.pdf')
            else:
                this_paper_main_path = os.path.join(save_dir, (this_paper['group']), f'{title}_{postfix}.pdf')
                os.makedirs(os.path.join(save_dir, (this_paper['group'])), exist_ok=True)
            if os.path.exists(this_paper_main_path):
                continue
            if total_paper_number is not None:
                pbar.set_description(f'Downloading paper {i}/{total_paper_number}')

            else:
                pbar.set_description(f'Downloading paper {i}')
            if 'error' == this_paper['link']:
                error_log.append((title, 'no link'))
            elif '' != this_paper['link']:
                try:
                    # download paper with IDM
                    basic_command[2] = this_paper['link']
                    basic_command[6] = this_paper_main_path
                    p = subprocess.Popen(' '.join(basic_command))
                  
                    #p.wait()
              
                    time.sleep(5)
                    # while True:
                    #     if os.path.exists(this_paper_main_path):
                    #         break
                    print("Downloaded")
                except Exception as e:
                    # error_flag = True
                    print('Error: ' + title + ' - ' + str(e))
                    error_log.append((title, this_paper['link'], 'paper download error', str(e)))

        # 2. write error log
        print('write error log')
        with open('download_err_log.txt', 'w') as f:
            for log in tqdm(error_log):
                for e in log:
                    if e is not None:
                        f.write(e)
                    else:
                        f.write('None')
                    f.write('\n')

                f.write('\n')


if __name__ == '__main__':
    # year = 2008
    # total_paper_number = None
    # # total_paper_number = save_csv(year)
    # download_from_csv(year, save_dir=f'..\\AAAI_{year}',
    #                   time_step_in_seconds=2,
    #                   total_paper_number=total_paper_number)
    for year in range(2019, 2020):
        print(year)
       #total_paper_number = 676
        total_paper_number = save_csv(year)
        download_from_csv(year, save_dir=f'..\\AAAI_{year}',
                          time_step_in_seconds=1 ,
                          total_paper_number=total_paper_number)
        time.sleep(1)

    pass