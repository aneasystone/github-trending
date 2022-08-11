# coding:utf-8

import datetime
import codecs
import requests
import os
from pyquery import PyQuery as pq

def scrape_url(url):
    ''' scrape github trending url
    '''
    HEADERS = {
        'User-Agent'		: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
        'Accept'			: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding'	: 'gzip,deflate,sdch',
        'Accept-Language'	: 'zh-CN,zh;q=0.8'
    }

    r = requests.get(url, headers=HEADERS)
    assert r.status_code == 200
    
    d = pq(r.content)
    items = d('div.Box article.Box-row')

    results = {}
    # codecs to solve the problem utf-8 codec like chinese
    for item in items:
        i = pq(item)
        title = i(".lh-condensed a").text()
        description = i("p.col-9").text()
        url = i(".lh-condensed a").attr("href")
        url = "https://github.com" + url
        results[title] = { 'title': title, 'url': url, 'description': description }
    return results

def scrape_lang(language):
    ''' scrape github trending with lang parameters
    '''
    url = 'https://github.com/trending/{language}'.format(language=language)
    r1 = scrape_url(url)
    url = 'https://github.com/trending/{language}&spoken_language_code=zh'.format(language=language)
    r2 = scrape_url(url)
    return { **r1, **r2 }

def write_markdown(lang, results):
    ''' write the results to markdown file
    '''
    with open('README.md') as f:
        content = f.read()
        content = convert_file_contenet(content, lang, results)
        f.write(content)

def convert_file_contenet(content, lang, results):
    distinct_results = []
    for title, result in results.items():
        if '[' + title + ']' not in content:
            distinct_results.append(result)
    
    if not distinct_results:
        print('There is no distinct results')
        return content

    lang_title = convert_lang_title(lang)
    if lang_title not in content:
        content += lang_title + '\r\n'
    
    return content.replace(lang_title, lang_title + convert_result_content(distinct_results))

def convert_result_content(results):
    for result in results:
        return u"* [{title}]({url}) - {description}\n".format(
            title=result['title'], url=result['v'], description=result['description'])

def convert_lang_title(lang):
    if lang == '':
        return '## All language'
    return '## ' + lang.capitalize()

def job():
    languages = ['', 'java', 'python', 'javascript', 'go', 'c', 'c++', 'c#', 'html', 'css', 'unknown']
    for lang in languages:
        results = scrape_lang(lang)
        write_markdown(lang, results)

if __name__ == '__main__':
    job()